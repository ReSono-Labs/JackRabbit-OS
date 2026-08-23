import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createContractValidator, ContractError } from "../src/release/contract-validator.mjs";
import { verifyManifest } from "../src/release/verify-manifest.mjs";

const installerRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const schemaFiles = ["operations-v1.schema.json", "signature-v1.schema.json", "release-v1.schema.json"];
const schemas = await Promise.all(schemaFiles.map(async file => JSON.parse(await readFile(join(installerRoot, "contracts", file), "utf8"))));
const contracts = createContractValidator(schemas);
const fixture = JSON.parse(await readFile(join(installerRoot, "conformance", "update-plan-valid-v1.json"), "utf8"));
const manifestBytes = new TextEncoder().encode(JSON.stringify(fixture.manifest));

function base64Url(bytes) {
  return Buffer.from(bytes).toString("base64url");
}

async function signedFixture() {
  const keys = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  const publicKey = base64Url(await crypto.subtle.exportKey("raw", keys.publicKey));
  const signature = base64Url(await crypto.subtle.sign({ name: "Ed25519" }, keys.privateKey, manifestBytes));
  const digest = Buffer.from(await crypto.subtle.digest("SHA-256", manifestBytes)).toString("hex");
  return {
    envelope: { schemaVersion: 1, algorithm: "Ed25519", keyId: "test-key-v1", manifestSha256: digest, signature },
    publicKeys: { "test-key-v1": publicKey }
  };
}

async function expectCode(code, promise) {
  await assert.rejects(promise, error => error instanceof ContractError && error.code === code);
}

test("verifies exact bytes before parsing a release manifest", async () => {
  const signed = await signedFixture();
  const manifest = await verifyManifest({ manifestBytes, contracts, ...signed });
  assert.equal(manifest.releaseId, fixture.manifest.releaseId);
});

test("changed manifest bytes fail the envelope digest", async () => {
  const signed = await signedFixture();
  const changed = Uint8Array.from(manifestBytes);
  changed[changed.length - 1] ^= 1;
  await expectCode("JR-RELEASE-DIGEST", verifyManifest({ manifestBytes: changed, contracts, ...signed }));
});

test("unknown and incorrect public keys fail closed", async () => {
  const signed = await signedFixture();
  await expectCode(
    "JR-RELEASE-SIGNATURE",
    verifyManifest({ manifestBytes, envelope: signed.envelope, publicKeys: {}, contracts })
  );
  const other = await signedFixture();
  await expectCode(
    "JR-RELEASE-SIGNATURE",
    verifyManifest({ manifestBytes, envelope: signed.envelope, publicKeys: other.publicKeys, contracts })
  );
});

test("signature envelope rejects unknown fields", async () => {
  const signed = await signedFixture();
  signed.envelope.force = true;
  await expectCode("JR-RELEASE-SCHEMA", verifyManifest({ manifestBytes, contracts, ...signed }));
});
