import assert from "node:assert/strict";
import test from "node:test";
import { flashStockR1 } from "../src/fastboot/flash-stock-r1.mjs";
import { R1_FASTBOOT_USB } from "../src/fastboot/read-r1-snapshot.mjs";

function vbmeta() {
  const bytes = new Uint8Array(4096);
  bytes.set(new TextEncoder().encode("AVB0"));
  return new Blob([bytes]);
}

test("executes the exact stock R1 route and re-verifies both mode transitions", async () => {
  const commands = [];
  const flashes = [];
  const flashedBlobs = [];
  let mode = "bootloader";
  const device = { ...R1_FASTBOOT_USB, serialNumber: "r1-test" };
  const release = {
    id: "test-stock-r1",
    product: "k65v1_64_bsp",
    slot: "a",
    systemExtSize: 559304704
  };
  const paths = [
    "images/stock/boot.img", "images/stock/super.img", "images/stock/vbmeta.img", "images/stock/vbmeta_system.img", "images/stock/vbmeta_vendor.img",
    "images/jackrabbit/system.img", "images/jackrabbit/product.img", "images/cipheros/system_ext.img", "images/cipheros/vendor.img",
    "images/cipheros/vbmeta.img", "images/cipheros/vbmeta_system.img", "images/cipheros/vbmeta_vendor.img"
  ];
  const packageFiles = new Map(paths.map(path => [path, path.includes("vbmeta") ? vbmeta() : new Blob([path])]));
  let deniedFastbootdOnce = false;
  const createTransport = async () => ({
    async getVariable(name) {
      return { product: release.product, "current-slot": "a", unlocked: "yes", "is-userspace": mode === "fastbootd" ? "yes" : "no", "partition-size:system_ext_a": null }[name] ?? null;
    },
    async runCommand(command) {
      commands.push(command);
      if (command === "reboot-fastboot") mode = "fastbootd";
      if (command === "reboot-bootloader") mode = "bootloader";
      return {};
    },
    async flashBlob(partition, blob, onProgress) { flashes.push(partition); flashedBlobs.push(blob); onProgress(1); },
    async close() {}
  });
  const createTransportWithPermissionRetry = async selectedDevice => {
    if (mode === "fastbootd" && !deniedFastbootdOnce) {
      deniedFastbootdOnce = true;
      throw Object.assign(new Error("Access denied"), { code: 18 });
    }
    return createTransport(selectedDevice);
  };

  const reconnectModes = [];
  const reconnectErrors = [];
  const result = await flashStockR1({
    initialDevice: device,
    packageFiles,
    release,
    createTransport: createTransportWithPermissionRetry,
    async requestReconnect(expectedMode, retryError) {
      reconnectModes.push(expectedMode);
      reconnectErrors.push(retryError?.message ?? null);
      return expectedMode === "fastbootd"
        ? { vendorId: 0x18d1, productId: 0x4ee0, serialNumber: device.serialNumber }
        : device;
    }
  });
  assert.deepEqual(flashes, [
    "boot_a", "boot_b", "vbmeta_a", "vbmeta_system_a", "vbmeta_vendor_a", "vbmeta_b", "vbmeta_system_b", "vbmeta_vendor_b",
    "super", "system_a", "system_ext_a", "product_a", "vendor_a", "vbmeta_a", "vbmeta_system_a", "vbmeta_vendor_a"
  ]);
  assert.deepEqual(commands, ["reboot-fastboot", "create-logical-partition:system_ext_a:559304704", "reboot-bootloader", "erase:userdata", "set_active:a", "reboot"]);
  assert.deepEqual(reconnectModes, ["fastbootd", "fastbootd", "bootloader"]);
  assert.deepEqual(reconnectErrors, [null, "Access denied", null]);
  const selectedBlobs = new Set(packageFiles.values());
  assert(flashedBlobs.every(blob => selectedBlobs.has(blob)), "browser must flash exact verified package blobs without mutation");
  assert.equal(result.operationsCompleted, 22);
});

test("flash module exposes no browser-side VBMeta mutation", async () => {
  const module = await import("../src/fastboot/flash-stock-r1.mjs");
  assert.deepEqual(Object.keys(module), ["flashStockR1"]);
});
