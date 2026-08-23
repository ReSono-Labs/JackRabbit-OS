import assert from "node:assert/strict";
import test from "node:test";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { indexReleaseFiles, verifyStockR1Package } from "../src/release/select-stock-r1-package.mjs";

function selectedFile(path, bytes) {
  return {
    name: path.split("/").at(-1),
    webkitRelativePath: `release/${path}`,
    size: bytes.byteLength,
    stream() { return new Blob([bytes]).stream(); }
  };
}

const bytes = new TextEncoder().encode("exact-image");
const release = Object.freeze({
  id: "test-release",
  artifacts: Object.freeze([{ path: "images/system.img", size: bytes.byteLength, sha256: bytesToHex(sha256(bytes)) }])
});

test("indexes and hashes the exact selected release inventory", async () => {
  const file = selectedFile("images/system.img", bytes);
  assert.equal(indexReleaseFiles([file], release).get("images/system.img"), file);
  const result = await verifyStockR1Package([file], release);
  assert.equal(result.releaseId, "test-release");
  assert.equal(result.artifactCount, 1);
});

test("missing, duplicate, wrong-size, and changed package files fail before install", async () => {
  assert.throws(() => indexReleaseFiles([], release), /Expected exactly one/);
  const file = selectedFile("images/system.img", bytes);
  assert.throws(() => indexReleaseFiles([file, file], release), /found 2/);
  const wrongSize = selectedFile("images/system.img", new Uint8Array(bytes.byteLength + 1));
  assert.throws(() => indexReleaseFiles([wrongSize], release), /size does not match/);
  const changed = selectedFile("images/system.img", new TextEncoder().encode("wrong-image"));
  await assert.rejects(verifyStockR1Package([changed], release), /digest does not match/);
});
