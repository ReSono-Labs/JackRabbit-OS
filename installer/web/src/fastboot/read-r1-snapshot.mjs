import { ContractError } from "../release/contract-validator.mjs";

export const R1_BOOTLOADER_USB = Object.freeze({ vendorId: 0x0e8d, productId: 0x201c });
export const R1_FASTBOOTD_USB = Object.freeze({ vendorId: 0x18d1, productId: 0x4ee0 });
export const R1_FASTBOOT_USB = R1_BOOTLOADER_USB;
const fastbootInterface = Object.freeze({ classCode: 0xff, subclassCode: 0x42, protocolCode: 0x03 });
const requiredVariables = Object.freeze(["product", "serialno", "unlocked", "current-slot", "is-userspace", "max-download-size"]);

function fail(code, message) {
  throw new ContractError(code, message);
}

function findInterface(configuration) {
  for (const usbInterface of configuration?.interfaces ?? []) {
    for (const alternate of usbInterface.alternates ?? []) {
      if (
        alternate.interfaceClass === fastbootInterface.classCode &&
        alternate.interfaceSubclass === fastbootInterface.subclassCode &&
        alternate.interfaceProtocol === fastbootInterface.protocolCode
      ) {
        const input = alternate.endpoints.find(endpoint => endpoint.type === "bulk" && endpoint.direction === "in");
        const output = alternate.endpoints.find(endpoint => endpoint.type === "bulk" && endpoint.direction === "out");
        if (input && output) return { interfaceNumber: usbInterface.interfaceNumber, input: input.endpointNumber, output: output.endpointNumber };
      }
    }
  }
  return null;
}

class R1FastbootSession {
  #device;
  #interfaceNumber;
  #input;
  #output;

  constructor(device) {
    this.#device = device;
  }

  async open() {
    await this.#device.open();
    if (!this.#device.configuration) await this.#device.selectConfiguration(1);
    const selected = findInterface(this.#device.configuration);
    if (!selected) fail("JR-FASTBOOT-INTERFACE", "selected USB device has no exact Android fastboot interface");
    try {
      await this.#device.claimInterface(selected.interfaceNumber);
    } catch {
      fail("JR-FASTBOOT-CLAIM", "Unable to claim the R1 USB interface. Close other installer tabs and native adb/fastboot tools, reconnect the cable, then select the R1 again.");
    }
    this.#interfaceNumber = selected.interfaceNumber;
    this.#input = selected.input;
    this.#output = selected.output;
  }

  async close() {
    if (!this.#device.opened) return;
    if (this.#interfaceNumber !== undefined && this.#device.releaseInterface) {
      try { await this.#device.releaseInterface(this.#interfaceNumber); } catch { /* Disconnects release it implicitly. */ }
    }
    await this.#device.close();
  }

  async #exchange(commandText, rejectionCode, rejectionMessage) {
    const command = new TextEncoder().encode(commandText);
    await this.#device.transferOut(this.#output, command);
    let text = "";
    while (true) {
      const result = await this.#device.transferIn(this.#input, 64);
      if (result.status !== "ok" || !result.data) fail("JR-FASTBOOT-TRANSFER", "fastboot read failed");
      const response = new TextDecoder("utf-8", { fatal: true }).decode(result.data.buffer);
      const status = response.slice(0, 4);
      const payload = response.slice(4).trim();
      if (status === "INFO") {
        text += payload;
        continue;
      }
      if (status === "OKAY") return `${text}${payload}`.trim();
      if (status === "FAIL") fail(rejectionCode, rejectionMessage);
      fail("JR-FASTBOOT-RESPONSE", "bootloader returned an unknown response status");
    }
  }

  async #getVariable(name) {
    if (!requiredVariables.includes(name)) fail("JR-FASTBOOT-VARIABLE", `getvar is not allowed: ${name}`);
    return this.#exchange(`getvar:${name}`, "JR-FASTBOOT-REJECTED", `bootloader rejected required getvar: ${name}`);
  }

  async snapshot(cryptoApi) {
    const values = {};
    for (const variable of requiredVariables) values[variable] = await this.#getVariable(variable);
    if (!values.product || !values.serialno) fail("JR-FASTBOOT-IDENTITY", "required device identity is missing");
    if (!new Set(["yes", "no"]).has(values.unlocked)) fail("JR-FASTBOOT-VALUE", "unlocked has an unsupported value");
    if (!new Set(["a", "b"]).has(values["current-slot"])) fail("JR-FASTBOOT-VALUE", "current-slot has an unsupported value");
    if (!new Set(["yes", "no"]).has(values["is-userspace"])) fail("JR-FASTBOOT-VALUE", "is-userspace has an unsupported value");
    if (!/^(?:0x)?[a-fA-F0-9]+$/.test(values["max-download-size"])) fail("JR-FASTBOOT-VALUE", "max-download-size is invalid");

    const identity = new TextEncoder().encode(`${this.#device.vendorId}:${this.#device.productId}:${values.serialno}`);
    const binding = [...new Uint8Array(await cryptoApi.subtle.digest("SHA-256", identity))]
      .map(byte => byte.toString(16).padStart(2, "0"))
      .join("");
    const mode = values["is-userspace"] === "yes" ? "fastbootd" : "bootloader";
    const expectedUsb = mode === "fastbootd" ? R1_FASTBOOTD_USB : R1_BOOTLOADER_USB;
    if (this.#device.vendorId !== expectedUsb.vendorId || this.#device.productId !== expectedUsb.productId) {
      fail("JR-FASTBOOT-MODE-IDENTITY", `R1 USB identity does not match reported ${mode} mode`);
    }
    return Object.freeze({
      product: values.product,
      unlocked: values.unlocked === "yes",
      currentSlot: values["current-slot"],
      mode,
      maximumDownloadBytes: Number.parseInt(values["max-download-size"].replace(/^0x/, ""), 16),
      deviceBinding: binding
    });
  }

  async unlock(cryptoApi) {
    const before = await this.snapshot(cryptoApi);
    if (before.product !== "k65v1_64_bsp") fail("JR-UNLOCK-PRODUCT", "selected device is not the reviewed R1 product");
    if (before.mode !== "bootloader") fail("JR-UNLOCK-MODE", "R1 must be in bootloader FASTBOOT to unlock");
    if (before.currentSlot !== "a") fail("JR-UNLOCK-SLOT", "R1 must be on slot a to unlock");
    if (before.unlocked) return before;

    await this.#exchange("flashing unlock", "JR-UNLOCK-REJECTED", "Rabbit rejected bootloader unlock. Enable developer mode and Device modification → Unlock in Rabbithole.");
    await this.#exchange("flashing unlock_critical", "JR-UNLOCK-CRITICAL-REJECTED", "Rabbit rejected critical-partition unlock. Installation stopped before flashing.");
    const unlocked = await this.#getVariable("unlocked");
    if (unlocked !== "yes") fail("JR-UNLOCK-VERIFY", "unlock commands completed but the R1 still reports locked");
    return Object.freeze({ ...before, unlocked: true });
  }
}

export async function requestR1FastbootDevice(usb = navigator.usb, expectedMode = "bootloader") {
  if (!usb?.requestDevice) fail("JR-CAPABILITY-WEBUSB", "WebUSB is unavailable");
  const filter = expectedMode === "fastbootd" ? R1_FASTBOOTD_USB : R1_BOOTLOADER_USB;
  return usb.requestDevice({ filters: [filter] });
}

export async function readR1Snapshot(device, cryptoApi = globalThis.crypto) {
  const supported = [R1_BOOTLOADER_USB, R1_FASTBOOTD_USB].some(identity => device.vendorId === identity.vendorId && device.productId === identity.productId);
  if (!supported) {
    fail("JR-FASTBOOT-DEVICE", "selected USB device is not the exact reviewed R1 fastboot identity");
  }
  const session = new R1FastbootSession(device);
  try {
    await session.open();
    return await session.snapshot(cryptoApi);
  } finally {
    await session.close();
  }
}

export async function unlockR1Bootloader(device, cryptoApi = globalThis.crypto) {
  if (device.vendorId !== R1_BOOTLOADER_USB.vendorId || device.productId !== R1_BOOTLOADER_USB.productId) {
    fail("JR-FASTBOOT-DEVICE", "selected USB device is not the exact reviewed R1 fastboot identity");
  }
  const session = new R1FastbootSession(device);
  try {
    await session.open();
    return await session.unlock(cryptoApi);
  } finally {
    await session.close();
  }
}
