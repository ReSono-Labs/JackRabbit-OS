import assert from "node:assert/strict";
import test from "node:test";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { ContractError } from "../src/release/contract-validator.mjs";
import { verifyArtifact, verifyBundleInventory } from "../src/release/verify-artifact.mjs";

const bytes = new TextEncoder().encode("JackRabbit verified artifact fixture");
const descriptor = Object.freeze({ id: "fixture-image", path: "images/fixture.img", size: bytes.length, sha256: bytesToHex(sha256(bytes)) });

async function* chunks(value, width = 5) {
  for (let offset = 0; offset < value.length; offset += width) {
    yield value.slice(offset, offset + width);
  }
}

async function expectCode(code, promise) {
  await assert.rejects(promise, error => error instanceof ContractError && error.code === code);
}

test("incrementally verifies exact artifact size and digest", async () => {
  const verified = await verifyArtifact(chunks(bytes), descriptor);
  assert.deepEqual(verified, { id: descriptor.id, size: descriptor.size, sha256: descriptor.sha256 });
  assert(Object.isFrozen(verified));
});

test("rejects short, long, changed, and non-byte streams", async () => {
  await expectCode("JR-ARTIFACT-SIZE", verifyArtifact(chunks(bytes.slice(1)), descriptor));
  await expectCode("JR-ARTIFACT-SIZE", verifyArtifact(chunks(Uint8Array.from([...bytes, 0])), descriptor));
  const changed = Uint8Array.from(bytes);
  changed[0] ^= 1;
  await expectCode("JR-ARTIFACT-HASH", verifyArtifact(chunks(changed), descriptor));
  await expectCode("JR-ARTIFACT-TYPE", verifyArtifact((async function* () { yield "not bytes"; })(), descriptor));
});

test("bundle inventory is exact and rejects missing, extra, duplicate, and wrong size", () => {
  const manifest = { artifacts: [descriptor] };
  assert.equal(verifyBundleInventory(manifest, [{ path: descriptor.path, size: descriptor.size }]), true);
  for (const [code, entries] of [
    ["JR-BUNDLE-MISSING", []],
    ["JR-BUNDLE-UNEXPECTED", [{ path: "images/other.img", size: descriptor.size }]],
    ["JR-BUNDLE-DUPLICATE", [{ path: descriptor.path, size: descriptor.size }, { path: descriptor.path, size: descriptor.size }]],
    ["JR-ARTIFACT-SIZE", [{ path: descriptor.path, size: descriptor.size + 1 }]]
  ]) {
    assert.throws(() => verifyBundleInventory(manifest, entries), error => error instanceof ContractError && error.code === code);
  }
});
