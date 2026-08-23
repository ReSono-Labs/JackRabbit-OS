import { ContractError } from "./contract-validator.mjs";

const signatureSchema = "urn:jackrabbit:installer:signature:v1";
const releaseSchema = "urn:jackrabbit:installer:release:v1";

function decodeBase64Url(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(value.replaceAll("-", "+").replaceAll("_", "/") + padding);
  return Uint8Array.from(binary, character => character.charCodeAt(0));
}

function toHex(bytes) {
  return [...bytes].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

export async function verifyManifest({ manifestBytes, envelope, publicKeys, contracts, cryptoApi = globalThis.crypto }) {
  contracts.validate(signatureSchema, envelope);
  if (!(manifestBytes instanceof Uint8Array)) {
    throw new ContractError("JR-RELEASE-DIGEST", "manifestBytes must be a Uint8Array");
  }
  const publicKey = publicKeys[envelope.keyId];
  if (typeof publicKey !== "string") {
    throw new ContractError("JR-RELEASE-SIGNATURE", "signature key is not trusted");
  }

  const digest = new Uint8Array(await cryptoApi.subtle.digest("SHA-256", manifestBytes));
  if (toHex(digest) !== envelope.manifestSha256) {
    throw new ContractError("JR-RELEASE-DIGEST", "manifest digest does not match the signed envelope");
  }

  const key = await cryptoApi.subtle.importKey(
    "raw",
    decodeBase64Url(publicKey),
    { name: "Ed25519" },
    false,
    ["verify"]
  );
  const verified = await cryptoApi.subtle.verify(
    { name: "Ed25519" },
    key,
    decodeBase64Url(envelope.signature),
    manifestBytes
  );
  if (!verified) {
    throw new ContractError("JR-RELEASE-SIGNATURE", "manifest signature is invalid");
  }

  let manifest;
  try {
    manifest = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(manifestBytes));
  } catch {
    throw new ContractError("JR-RELEASE-SCHEMA", "verified manifest is not strict UTF-8 JSON");
  }
  contracts.validate(releaseSchema, manifest);
  return manifest;
}
