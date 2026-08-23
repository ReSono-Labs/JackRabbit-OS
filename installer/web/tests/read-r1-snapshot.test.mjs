import assert from "node:assert/strict";
import test from "node:test";
import { ContractError } from "../src/release/contract-validator.mjs";
import { R1_FASTBOOTD_USB, R1_FASTBOOT_USB, readR1Snapshot, requestR1FastbootDevice, unlockR1Bootloader } from "../src/fastboot/read-r1-snapshot.mjs";

const values = {
  product: "rabbit-r1",
  serialno: "private-test-serial",
  unlocked: "yes",
  "current-slot": "a",
  "is-userspace": "no",
  "max-download-size": "0x10000000"
};

function fakeDevice(overrides = {}, deviceValues = { ...values }) {
  let response = "";
  const commands = [];
  return {
    vendorId: R1_FASTBOOT_USB.vendorId,
    productId: R1_FASTBOOT_USB.productId,
    opened: false,
    configuration: null,
    commands,
    async open() { this.opened = true; },
    async close() { this.opened = false; },
    async selectConfiguration() {
      this.configuration = { interfaces: [{ interfaceNumber: 0, alternates: [{ interfaceClass: 0xff, interfaceSubclass: 0x42, interfaceProtocol: 0x03, endpoints: [{ type: "bulk", direction: "in", endpointNumber: 1 }, { type: "bulk", direction: "out", endpointNumber: 2 }] }] }] };
    },
    async claimInterface() {},
    async transferOut(_endpoint, bytes) {
      const command = new TextDecoder().decode(bytes);
      commands.push(command);
      if (command === "flashing unlock" || command === "flashing unlock_critical") {
        if (command === "flashing unlock_critical") deviceValues.unlocked = "yes";
        response = "OKAY";
      } else {
        response = `OKAY${deviceValues[command.slice(7)] ?? ""}`;
      }
      return { status: "ok" };
    },
    async transferIn() {
      const bytes = new TextEncoder().encode(response);
      return { status: "ok", data: new DataView(bytes.buffer) };
    },
    ...overrides
  };
}

async function expectCode(code, promise) {
  await assert.rejects(promise, error => error instanceof ContractError && error.code === code);
}

test("requests only the exact R1 fastboot USB identity", async () => {
  let options;
  const selected = {};
  assert.equal(await requestR1FastbootDevice({ async requestDevice(value) { options = value; return selected; } }), selected);
  assert.deepEqual(options, { filters: [{ vendorId: 0x0e8d, productId: 0x201c }] });
  await requestR1FastbootDevice({ async requestDevice(value) { options = value; return selected; } }, "fastbootd");
  assert.deepEqual(options, { filters: [{ vendorId: 0x18d1, productId: 0x4ee0 }] });
});

test("accepts the exact fastbootd USB identity only in userspace mode", async () => {
  const device = fakeDevice({ vendorId: R1_FASTBOOTD_USB.vendorId, productId: R1_FASTBOOTD_USB.productId }, { ...values, "is-userspace": "yes" });
  assert.equal((await readR1Snapshot(device)).mode, "fastbootd");
  const mismatch = fakeDevice({ vendorId: R1_FASTBOOTD_USB.vendorId, productId: R1_FASTBOOTD_USB.productId }, { ...values, "is-userspace": "no" });
  await expectCode("JR-FASTBOOT-MODE-IDENTITY", readR1Snapshot(mismatch));
});

test("reads only the closed getvar set and returns redacted immutable identity", async () => {
  const device = fakeDevice();
  const snapshot = await readR1Snapshot(device);
  assert.deepEqual(device.commands, ["getvar:product", "getvar:serialno", "getvar:unlocked", "getvar:current-slot", "getvar:is-userspace", "getvar:max-download-size"]);
  assert.equal(snapshot.product, "rabbit-r1");
  assert.equal(snapshot.unlocked, true);
  assert.equal(snapshot.mode, "bootloader");
  assert.equal(snapshot.maximumDownloadBytes, 0x10000000);
  assert.match(snapshot.deviceBinding, /^[a-f0-9]{64}$/);
  assert.equal(JSON.stringify(snapshot).includes(values.serialno), false);
  assert(Object.isFrozen(snapshot));
  assert.equal(device.opened, false);
});

test("rejects the wrong USB identity before opening", async () => {
  let opened = false;
  const device = fakeDevice({ vendorId: 1, async open() { opened = true; } });
  await expectCode("JR-FASTBOOT-DEVICE", readR1Snapshot(device));
  assert.equal(opened, false);
});

test("rejects a non-fastboot interface and closes", async () => {
  const device = fakeDevice({
    async selectConfiguration() { this.configuration = { interfaces: [] }; }
  });
  await expectCode("JR-FASTBOOT-INTERFACE", readR1Snapshot(device));
  assert.equal(device.opened, false);
});

test("module exposes no raw command function", async () => {
  const module = await import("../src/fastboot/read-r1-snapshot.mjs");
  assert.deepEqual(Object.keys(module).sort(), ["R1_BOOTLOADER_USB", "R1_FASTBOOTD_USB", "R1_FASTBOOT_USB", "readR1Snapshot", "requestR1FastbootDevice", "unlockR1Bootloader"]);
});

test("unlock sends only Rabbit's exact two commands after closed R1 preflight", async () => {
  const device = fakeDevice({}, { ...values, product: "k65v1_64_bsp", unlocked: "no" });
  const snapshot = await unlockR1Bootloader(device);
  assert.equal(snapshot.unlocked, true);
  assert.deepEqual(device.commands, [
    "getvar:product",
    "getvar:serialno",
    "getvar:unlocked",
    "getvar:current-slot",
    "getvar:is-userspace",
    "getvar:max-download-size",
    "flashing unlock",
    "flashing unlock_critical",
    "getvar:unlocked"
  ]);
  assert.equal(device.opened, false);
});

test("unlock rejects the wrong product before a mutating command", async () => {
  const device = fakeDevice({}, { ...values, product: "not-r1", unlocked: "no" });
  await expectCode("JR-UNLOCK-PRODUCT", unlockR1Bootloader(device));
  assert.equal(device.commands.some(command => command.startsWith("flashing ")), false);
});
