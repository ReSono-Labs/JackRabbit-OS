import assert from "node:assert/strict";
import test from "node:test";
import { ContractError } from "../src/release/contract-validator.mjs";
import { R1_PRELOADER_USB, requestR1Preloader, sendFastbootEntry } from "../src/preloader/enter-r1-fastboot.mjs";

async function expectCode(code, promise) {
  await assert.rejects(promise, error => error instanceof ContractError && error.code === code);
}

test("requests only the exact reviewed R1 preloader identity", async () => {
  let options;
  const port = {};
  assert.equal(await requestR1Preloader({ async requestPort(value) { options = value; return port; } }), port);
  assert.deepEqual(options, { filters: [{ usbVendorId: 0x0e8d, usbProductId: 0x2000 }] });
  assert.deepEqual(R1_PRELOADER_USB, { usbVendorId: 0x0e8d, usbProductId: 0x2000 });
});

test("writes exactly eight FASTBOOT bytes at 115200 and closes", async () => {
  let openOptions;
  let written;
  let released = false;
  let closed = false;
  const port = {
    writable: { getWriter() { return { async write(value) { written = value; }, releaseLock() { released = true; } }; } },
    async open(value) { openOptions = value; },
    async close() { closed = true; }
  };
  const result = await sendFastbootEntry(port);
  assert.deepEqual(openOptions, { baudRate: 115200 });
  assert.equal(new TextDecoder().decode(written), "FASTBOOT");
  assert.equal(written.byteLength, 8);
  assert.deepEqual(result, { payloadBytes: 8, transferComplete: true, deviceModeUnverified: true });
  assert.equal(released, true);
  assert.equal(closed, true);
});

test("transfer failure releases and closes without claiming device-mode success", async () => {
  let released = false;
  let closed = false;
  const port = {
    writable: { getWriter() { return { async write() { throw new Error("disconnect"); }, releaseLock() { released = true; } }; } },
    async open() {},
    async close() { closed = true; }
  };
  await expectCode("JR-PRELOADER-TRANSFER", sendFastbootEntry(port));
  assert.equal(released, true);
  assert.equal(closed, true);
});

test("module exposes no arbitrary payload or serial settings", async () => {
  const module = await import("../src/preloader/enter-r1-fastboot.mjs");
  assert.deepEqual(Object.keys(module).sort(), ["R1_PRELOADER_USB", "requestR1Preloader", "sendFastbootEntry"]);
});
