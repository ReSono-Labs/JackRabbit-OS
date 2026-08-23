import { FastbootDevice } from "android-fastboot/dist/fastboot.mjs";
import { ContractError } from "../release/contract-validator.mjs";
import { R1_BOOTLOADER_USB, R1_FASTBOOTD_USB } from "./read-r1-snapshot.mjs";

function fail(code, message) {
  throw new ContractError(code, message);
}

async function createBrowserTransport(device) {
  const client = new FastbootDevice();
  client.device = device;
  await client._validateAndConnectDevice();
  return Object.freeze({
    getVariable: name => client.getVariable(name),
    runCommand: command => client.runCommand(command),
    flashBlob: (partition, blob, progress) => client.flashBlob(partition, blob, progress),
    async close() {
      if (client.device?.opened) await client.device.close();
    }
  });
}

async function safelyClose(transport) {
  try { await transport.close(); } catch { /* A reboot may remove USB first. */ }
}

async function assertGate(transport, release, expectedMode) {
  const product = await transport.getVariable("product");
  const slot = await transport.getVariable("current-slot");
  const unlocked = await transport.getVariable("unlocked");
  const userspace = await transport.getVariable("is-userspace");
  const mode = userspace === "yes" ? "fastbootd" : "bootloader";
  if (product !== release.product) fail("JR-FLASH-PRODUCT", `Expected ${release.product}; R1 reported ${product || "nothing"}.`);
  if (slot !== release.slot) fail("JR-FLASH-SLOT", `Expected slot ${release.slot}; R1 reported ${slot || "nothing"}.`);
  if (unlocked !== "yes") fail("JR-FLASH-LOCKED", "R1 no longer reports an unlocked bootloader.");
  if (mode !== expectedMode) fail("JR-FLASH-MODE", `Expected ${expectedMode}; R1 reported ${mode}.`);
}

function sameR1(device, original, expectedMode) {
  const expected = expectedMode === "fastbootd" ? R1_FASTBOOTD_USB : R1_BOOTLOADER_USB;
  if (device.vendorId !== expected.vendorId || device.productId !== expected.productId) return false;
  return !original.serialNumber || !device.serialNumber || device.serialNumber === original.serialNumber;
}

async function reconnectR1({ original, expectedMode, release, createTransport, requestReconnect, onProgress }) {
  if (typeof requestReconnect !== "function") fail("JR-FLASH-RECONNECT", "installer has no user-authorized reconnect handler");
  let retryError = null;
  while (true) {
    onProgress({ label: `Select the R1 again in ${expectedMode}.`, fraction: null, requiresUserAction: true, expectedMode });
    const candidate = await requestReconnect(expectedMode, retryError);
    retryError = null;
    if (!candidate || !sameR1(candidate, original, expectedMode)) {
      retryError = new ContractError("JR-FLASH-RECONNECT", `selected USB device is not the same R1 in ${expectedMode}`);
      continue;
    }
    let transport = null;
    try {
      transport = await createTransport(candidate);
      await assertGate(transport, release, expectedMode);
      return transport;
    } catch (error) {
      if (transport) await safelyClose(transport);
      retryError = error;
    }
  }
}

export async function flashStockR1({ initialDevice, packageFiles, release, createTransport = createBrowserTransport, requestReconnect, onProgress = () => {} }) {
  const file = path => {
    const selected = packageFiles.get(path);
    if (!selected) fail("JR-FLASH-PACKAGE", `Verified package file is unavailable: ${path}`);
    return selected;
  };
  const steps = 22;
  let step = 0;
  let transport = await createTransport(initialDevice);
  const report = (label, fraction = null) => onProgress({ step, total: steps, label, fraction });
  const command = async (label, raw) => {
    report(label);
    await transport.runCommand(raw);
    step += 1;
  };
  const flash = async (label, partition, blob) => {
    report(label, 0);
    await transport.flashBlob(partition, blob, fraction => report(label, fraction));
    step += 1;
  };

  try {
    await assertGate(transport, release, "bootloader");
    await flash("Writing boot slot A", "boot_a", file("images/stock/boot.img"));
    await flash("Writing boot slot B", "boot_b", file("images/stock/boot.img"));

    const stockVbmeta = file("images/stock/vbmeta.img");
    const stockVbmetaSystem = file("images/stock/vbmeta_system.img");
    const stockVbmetaVendor = file("images/stock/vbmeta_vendor.img");
    for (const slot of ["a", "b"]) {
      await flash(`Writing stock VBMeta slot ${slot.toUpperCase()}`, `vbmeta_${slot}`, stockVbmeta);
      await flash(`Writing stock system VBMeta slot ${slot.toUpperCase()}`, `vbmeta_system_${slot}`, stockVbmetaSystem);
      await flash(`Writing stock vendor VBMeta slot ${slot.toUpperCase()}`, `vbmeta_vendor_${slot}`, stockVbmetaVendor);
    }

    report("Rebooting into fastbootd");
    await transport.runCommand("reboot-fastboot");
    step += 1;
    await safelyClose(transport);
    transport = await reconnectR1({ original: initialDevice, expectedMode: "fastbootd", release, createTransport, requestReconnect, onProgress });

    await flash("Writing stock super — the R1 screen may go blank; do not unplug", "super", file("images/stock/super.img"));
    const systemExtHex = await transport.getVariable("partition-size:system_ext_a");
    if (systemExtHex === null) {
      await command("Creating system_ext partition", `create-logical-partition:system_ext_a:${release.systemExtSize}`);
    } else if (Number.parseInt(systemExtHex.replace(/^0x/, ""), 16) !== release.systemExtSize) {
      fail("JR-FLASH-SYSTEM-EXT-SIZE", `Existing system_ext_a has unexpected size ${systemExtHex}.`);
    }

    await flash("Writing JackRabbit system", "system_a", file("images/jackrabbit/system.img"));
    await flash("Writing CipherOS system extensions", "system_ext_a", file("images/cipheros/system_ext.img"));
    await flash("Writing JackRabbit product", "product_a", file("images/jackrabbit/product.img"));
    await flash("Writing CipherOS vendor", "vendor_a", file("images/cipheros/vendor.img"));

    report("Returning to bootloader FASTBOOT");
    await transport.runCommand("reboot-bootloader");
    step += 1;
    await safelyClose(transport);
    transport = await reconnectR1({ original: initialDevice, expectedMode: "bootloader", release, createTransport, requestReconnect, onProgress });

    await flash("Activating CipherOS VBMeta", "vbmeta_a", file("images/cipheros/vbmeta.img"));
    await flash("Activating CipherOS system VBMeta", "vbmeta_system_a", file("images/cipheros/vbmeta_system.img"));
    await flash("Activating CipherOS vendor VBMeta", "vbmeta_vendor_a", file("images/cipheros/vbmeta_vendor.img"));
    await command("Erasing stock user data", "erase:userdata");
    await command("Selecting slot A", "set_active:a");
    report("Rebooting into JackRabbit");
    await transport.runCommand("reboot");
    step += 1;
    return Object.freeze({ releaseId: release.id, operationsCompleted: step });
  } finally {
    await safelyClose(transport);
  }
}
