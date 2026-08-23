import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const defaultRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const installerRoot = resolve(process.argv[2] ?? defaultRoot);
const sourcePath = join(installerRoot, "provenance", "sources.json");

function fail(code, message) {
  process.stderr.write(`JR-PROVENANCE-${code}: ${message}\n`);
  process.exit(1);
}

let ledger;
try {
  ledger = JSON.parse(await readFile(sourcePath, "utf8"));
} catch (error) {
  fail("JSON", `cannot parse provenance/sources.json: ${error.message}`);
}

if (ledger.schemaVersion !== 1 || !Array.isArray(ledger.sources)) {
  fail("SCHEMA", "expected schemaVersion 1 and a sources array");
}

const requiredIds = new Set([
  "rabbit-flash-page",
  "rabbit-device-detection",
  "rabbit-fastboot-operations",
  "rabbit-main",
  "fastboot-js",
  "zip-js",
  "rabbit-developer-mode",
  "rabbit-r1-firmware-cipheros-route",
  "android-platform-tools-linux",
  "android-platform-tools-macos",
  "android-platform-tools-windows",
  "rabbit-mediatek-windows-driver",
  "google-usb-driver-windows",
  "mdn-browser-compat-data",
  "webusb-specification",
  "web-serial-specification",
  "serde",
  "serde-json",
  "fastboot-protocol-rust",
  "nusb",
  "futures-rust",
  "serialport-rust",
  "actions-checkout",
  "actions-setup-node",
  "dtolnay-rust-toolchain",
  "actions-upload-artifact"
]);
const sourcesById = new Map();

for (const source of ledger.sources) {
  if (!source || typeof source !== "object" || typeof source.id !== "string") {
    fail("SCHEMA", "every source must have a string id");
  }
  if (sourcesById.has(source.id)) {
    fail("DUPLICATE", `duplicate source id: ${source.id}`);
  }
  if (typeof source.url !== "string" || !source.url.startsWith("https://")) {
    fail("URL", `source ${source.id} must use an HTTPS URL`);
  }
  if (source.sha256 !== undefined && !/^[a-f0-9]{64}$/.test(source.sha256)) {
    fail("HASH", `source ${source.id} has an invalid SHA-256`);
  }
  sourcesById.set(source.id, source);
}

for (const requiredId of requiredIds) {
  if (!sourcesById.has(requiredId)) {
    fail("REQUIRED", `missing source: ${requiredId}`);
  }
}

for (const [id, revision] of [
  ["actions-checkout", "de0fac2e4500dabe0009e67214ff5f5447ce83dd"],
  ["actions-setup-node", "48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e"],
  ["dtolnay-rust-toolchain", "6c977a6ca4077a0ceb28ffbe03f59d46e9ac8772"],
  ["actions-upload-artifact", "ea165f8d65b6e75b540449e92b4886f43607fa02"]
]) {
  const source = sourcesById.get(id);
  if (source.revision !== revision || source.license !== "MIT" || source.disposition !== "adopted-exact") {
    fail("DEPENDENCY-PIN", `${id} dependency identity or disposition changed`);
  }
}

for (const id of [
  "rabbit-flash-page",
  "rabbit-device-detection",
  "rabbit-fastboot-operations",
  "rabbit-main"
]) {
  const source = sourcesById.get(id);
  if (
    source.license !== "NOASSERTION" ||
    source.disposition !== "review-only-no-copy" ||
    source.revision !== null
  ) {
    fail("RABBIT-DISPOSITION", `${id} must remain unversioned review-only material`);
  }
}

const fastboot = sourcesById.get("fastboot-js");
if (
  fastboot.revision !== "5b613332aa9d66cca5bebb49f147cd084a76c464" ||
  fastboot.artifact !== "dist/fastboot.min.mjs" ||
  fastboot.sha256 !== "bd8283520de10c4cb39139f2f98297a420b39e456c3241db2c7322a82bd2a6db" ||
  fastboot.version !== "1.1.3" ||
  fastboot.integrity !== "sha512-WKgJR25RFS6zuIeHlg7hwNiX6MaGYRmDVR1w0ZZv7iXCfJueUVddb7+eCrG0GNzTyJDbTdetVN1R9Pls9r0DKA==" ||
  fastboot.license !== "MIT" ||
  fastboot.disposition !== "adopted-exact-web-writer"
) {
  fail("FASTBOOT-PIN", "fastboot.js dependency identity or disposition changed");
}

const zipJs = sourcesById.get("zip-js");
if (
  zipJs.revision !== "2.2.27" ||
  zipJs.integrity !== "sha512-lQLsq41xUIGJnUizICgjLL+1hrnlLcqyWnQcaNi8FdsxfJl8y0bqdolDit8o65Huai+/GwXbCODMVu05kNU8mA==" ||
  zipJs.license !== "BSD-3-Clause" ||
  zipJs.disposition !== "adopted-transitive-exact"
) {
  fail("DEPENDENCY-PIN", "zip.js dependency identity or disposition changed");
}

const cipherRoute = sourcesById.get("rabbit-r1-firmware-cipheros-route");
if (
  cipherRoute.revision !== "14b1ee3a1ee62dbed1a79ac49764c5dd22b0547b" ||
  cipherRoute.sourcePath !== "scripts/flash-cipheros.sh" ||
  cipherRoute.license !== "Apache-2.0" ||
  cipherRoute.disposition !== "adapted-closed-r1-route"
) {
  fail("CIPHEROS-ROUTE", "CipherOS route donor identity or disposition changed");
}

for (const [id, sha256] of [
  ["android-platform-tools-linux", "d230f13842f60f782a8645f9c813f8f845bf36089ea7289f28c48f17979313f1"],
  ["android-platform-tools-macos", "ee39ad5967e95c2a07f04dbcbde96b1a0c916ba376096db5d2f498b7727a5d1d"],
  ["android-platform-tools-windows", "45f4d63113e895ebde0c90f194099a4676b6ac653bd28d54314a9e022bbc1a99"]
]) {
  const source = sourcesById.get(id);
  if (source.revision !== "37.0.1" || source.sha256 !== sha256 || source.disposition !== "packaged-exact-host-runtime") {
    fail("PLATFORM-TOOLS", `${id} identity or disposition changed`);
  }
}

const rabbitWindowsDriver = sourcesById.get("rabbit-mediatek-windows-driver");
if (
  rabbitWindowsDriver.sha256 !== "c83f7ba3e657abd3577640448009178d98c07a849f49bcdf5f59577158ea7dab" ||
  rabbitWindowsDriver.license !== "NOASSERTION" ||
  rabbitWindowsDriver.disposition !== "packaged-unmodified-official-rabbit-driver"
) {
  fail("HOST-DRIVER", "Rabbit Windows driver identity or disposition changed");
}

const googleWindowsDriver = sourcesById.get("google-usb-driver-windows");
if (
  googleWindowsDriver.revision !== "13" ||
  googleWindowsDriver.sha256 !== "360b01d3dfb6c41621a3a64ae570dfac2c9a40cca1b5a1f136ae90d02f5e9e0b" ||
  googleWindowsDriver.disposition !== "packaged-exact-fastbootd-driver"
) {
  fail("HOST-DRIVER", "Google Windows USB driver identity or disposition changed");
}

for (const [id, revision, integrity] of [
  ["serde", "1.0.229", "4148590afebada386688f18773da617792bf2ef03ffc1e4cbd2b1d45b023e0ba"],
  ["serde-json", "1.0.151", "c841b55ecdae098c80dcae9cf767f6f8a0c2cdb3416bbef72181df4d0fe73f14"]
]) {
  const source = sourcesById.get(id);
  if (
    source.revision !== revision ||
    source.integrity !== integrity ||
    source.license !== "MIT OR Apache-2.0" ||
    source.disposition !== "adopted-exact"
  ) {
    fail("DEPENDENCY-PIN", `${id} dependency identity or disposition changed`);
  }
}

for (const [id, revision, version, integrity, license, disposition] of [
  ["fastboot-protocol-rust", "c84eee005cfadef7baa80a6cdbebb966de5f03e0", "0.4.0", "d68604b2b5b85058d350ce6ecc153ac0a30306118099dfef2a2012544d4fee2e", "MIT OR Apache-2.0", "adopted-read-only-cli-adapter"],
  ["nusb", "bdc148c123c102785cd1d506b77bfeeb794ffeb1", "0.2.7", "18ef13beb3b3a8fc16fd7aea912ebd3d45dde00a9a5b968d0742297468065845", "Apache-2.0 OR MIT", "adopted-exact"],
  ["futures-rust", "705e6b5c0f06535b1aac1cb1989a172b3d45be8c", "0.3.34", "9a31d2a3fbaaeb2af2368bbdd904aa8e812d3c04a1ee10d3171f52d556e5d0a3", "MIT OR Apache-2.0", "adopted-exact"]
]) {
  const source = sourcesById.get(id);
  if (
    source.revision !== revision ||
    source.version !== version ||
    source.integrity !== integrity ||
    source.license !== license ||
    source.disposition !== disposition
  ) {
    fail("DEPENDENCY-PIN", `${id} dependency identity or disposition changed`);
  }
}

const serialport = sourcesById.get("serialport-rust");
if (
  serialport.revision !== "4.9.0" ||
  serialport.integrity !== "a4d91116f97173694f1642263b2ff837f80d933aa837e2314969f6728f661df3" ||
  serialport.license !== "MPL-2.0" ||
  serialport.disposition !== "adopted-exact-preloader-transport"
) {
  fail("DEPENDENCY-PIN", "serialport dependency identity or disposition changed");
}

process.stdout.write(`JR-PROVENANCE-OK: ${ledger.sources.length} sources\n`);
