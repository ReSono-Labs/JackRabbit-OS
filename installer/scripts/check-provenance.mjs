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
  "mdn-browser-compat-data",
  "webusb-specification",
  "web-serial-specification"
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
  fastboot.license !== "MIT" ||
  fastboot.disposition !== "pinned-candidate-not-adopted"
) {
  fail("FASTBOOT-PIN", "fastboot.js candidate identity or disposition changed");
}

process.stdout.write(`JR-PROVENANCE-OK: ${ledger.sources.length} sources\n`);
