import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createContractValidator, ContractError } from "../src/release/contract-validator.mjs";

const installerRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const readJson = async path => JSON.parse(await readFile(join(installerRoot, path), "utf8"));
const schemas = await Promise.all([
  readJson("contracts/operations-v1.schema.json"),
  readJson("contracts/prompts-v1.schema.json")
]);
const contract = await readJson("contracts/preparation-prompts-v1.json");
const validator = createContractValidator(schemas);

test("shared preparation prompts satisfy the canonical schema", () => {
  assert.equal(validator.validate("urn:jackrabbit:installer:prompts:v1", contract), contract);
  assert.deepEqual(contract.prompts.map(prompt => prompt.id), [
    "prepare-account",
    "back-up",
    "prepare-hardware",
    "open-official-entry",
    "enter-fastboot-cli"
  ]);
});

test("prompt contract rejects unreviewed links and unknown fields", () => {
  const changedLink = structuredClone(contract);
  changedLink.prompts.at(-1).href = "https://example.invalid/flashing";
  assert.throws(
    () => validator.validate("urn:jackrabbit:installer:prompts:v1", changedLink),
    error => error instanceof ContractError && error.code === "JR-RELEASE-SCHEMA"
  );

  const changedShape = structuredClone(contract);
  changedShape.prompts[0].override = true;
  assert.throws(
    () => validator.validate("urn:jackrabbit:installer:prompts:v1", changedShape),
    error => error instanceof ContractError && error.code === "JR-RELEASE-SCHEMA"
  );
});
