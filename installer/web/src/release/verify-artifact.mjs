import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { ContractError } from "./contract-validator.mjs";

export async function verifyArtifact(chunks, descriptor) {
  const hash = sha256.create();
  let received = 0;

  for await (const chunk of chunks) {
    if (!(chunk instanceof Uint8Array)) {
      throw new ContractError("JR-ARTIFACT-TYPE", "artifact stream yielded a non-byte chunk");
    }
    received += chunk.byteLength;
    if (received > descriptor.size) {
      throw new ContractError("JR-ARTIFACT-SIZE", `artifact exceeds declared size: ${descriptor.id}`);
    }
    hash.update(chunk);
  }

  if (received !== descriptor.size) {
    throw new ContractError("JR-ARTIFACT-SIZE", `artifact size does not match: ${descriptor.id}`);
  }
  if (bytesToHex(hash.digest()) !== descriptor.sha256) {
    throw new ContractError("JR-ARTIFACT-HASH", `artifact digest does not match: ${descriptor.id}`);
  }
  return Object.freeze({ id: descriptor.id, size: received, sha256: descriptor.sha256 });
}

export function verifyBundleInventory(manifest, entries) {
  const expected = new Map(manifest.artifacts.map(artifact => [artifact.path, artifact]));
  const observed = new Set();

  for (const entry of entries) {
    if (observed.has(entry.path)) {
      throw new ContractError("JR-BUNDLE-DUPLICATE", `bundle path appears more than once: ${entry.path}`);
    }
    observed.add(entry.path);
    const artifact = expected.get(entry.path);
    if (!artifact) {
      throw new ContractError("JR-BUNDLE-UNEXPECTED", `bundle contains an undeclared path: ${entry.path}`);
    }
    if (entry.size !== artifact.size) {
      throw new ContractError("JR-ARTIFACT-SIZE", `bundle entry size does not match: ${entry.path}`);
    }
  }

  for (const path of expected.keys()) {
    if (!observed.has(path)) {
      throw new ContractError("JR-BUNDLE-MISSING", `bundle is missing a declared artifact: ${path}`);
    }
  }
  return true;
}
