import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { lstat, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const installerRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const { stockR1Release } = await import(pathToFileURL(join(installerRoot, "web/src/release/stock-r1-release.mjs")));
const releaseRoot = resolve(process.argv[2] ?? "");

function fail(code, message) {
  process.stderr.write(`JR-RELEASE-DIRECTORY-${code}: ${message}\n`);
  process.exit(1);
}

if (!process.argv[2]) fail("ARGUMENT", "one release directory is required");

async function sha256(path) {
  return new Promise((resolveDigest, reject) => {
    const digest = createHash("sha256");
    const stream = createReadStream(path);
    stream.on("error", reject);
    stream.on("data", chunk => digest.update(chunk));
    stream.on("end", () => resolveDigest(digest.digest("hex")));
  });
}

const expectedPaths = new Set(stockR1Release.artifacts.map(artifact => artifact.path));
const actualPaths = [];
for (const group of ["stock", "jackrabbit", "cipheros"]) {
  let entries;
  try {
    entries = await readdir(join(releaseRoot, "images", group), { withFileTypes: true });
  } catch (error) {
    fail("LAYOUT", `cannot read images/${group}: ${error.message}`);
  }
  for (const entry of entries) {
    if (!entry.isFile()) fail("TYPE", `images/${group}/${entry.name} is not a regular file`);
    actualPaths.push(`images/${group}/${entry.name}`);
  }
}

if (actualPaths.length !== expectedPaths.size || actualPaths.some(path => !expectedPaths.has(path))) {
  fail("INVENTORY", `expected exactly the ${expectedPaths.size} files in ${stockR1Release.id}`);
}

for (const artifact of stockR1Release.artifacts) {
  const path = join(releaseRoot, artifact.path);
  let info;
  try {
    info = await lstat(path);
  } catch (error) {
    fail("MISSING", `${artifact.path}: ${error.message}`);
  }
  if (!info.isFile() || info.isSymbolicLink()) fail("TYPE", `${artifact.path} is not a regular file`);
  if (info.size !== artifact.size) fail("SIZE", `${artifact.path} has ${info.size} bytes; expected ${artifact.size}`);
  if (await sha256(path) !== artifact.sha256) fail("HASH", `${artifact.path} does not match the canonical SHA-256`);
}

process.stdout.write(`JR-RELEASE-DIRECTORY-OK: ${stockR1Release.id} at ${releaseRoot}\n`);
