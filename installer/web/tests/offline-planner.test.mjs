import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createContractValidator, ContractError } from "../src/release/contract-validator.mjs";
import { planRelease } from "../src/install/plan-release.mjs";

const installerRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const contractFiles = ["operations-v1.schema.json", "signature-v1.schema.json", "release-v1.schema.json", "recovery-v1.schema.json", "journal-v1.schema.json"];
const schemas = await Promise.all(contractFiles.map(async file => JSON.parse(await readFile(join(installerRoot, "contracts", file), "utf8"))));
const contracts = createContractValidator(schemas);
const fixture = JSON.parse(await readFile(join(installerRoot, "conformance", "update-plan-valid-v1.json"), "utf8"));

function clone(value) {
  return structuredClone(value);
}

function expectCode(code, operation) {
  assert.throws(operation, error => error instanceof ContractError && error.code === code);
}

test("all canonical schemas compile and the valid release plans immutably", () => {
  contracts.validate("urn:jackrabbit:installer:release:v1", fixture.manifest);
  const plan = planRelease(fixture.manifest, fixture.device);
  assert.equal(plan.operations.length, 7);
  assert.equal(plan.operations[1].artifact.sha256, "a".repeat(64));
  assert(Object.isFrozen(plan));
  assert(Object.isFrozen(plan.operations));
  assert(Object.isFrozen(plan.operations[1].artifact));
});

test("schema rejects unknown fields and unsafe paths", () => {
  const unknown = clone(fixture.manifest);
  unknown.force = true;
  expectCode("JR-RELEASE-SCHEMA", () => contracts.validate("urn:jackrabbit:installer:release:v1", unknown));
  const escape = clone(fixture.manifest);
  escape.artifacts[0].path = ["..", "system.img"].join("/");
  expectCode("JR-RELEASE-SCHEMA", () => contracts.validate("urn:jackrabbit:installer:release:v1", escape));
});

test("planner denies locked, wrong product, contract, and slot", () => {
  for (const [code, change] of [
    ["JR-PLAN-LOCKED", { unlocked: false }],
    ["JR-PLAN-PRODUCT", { product: "other" }],
    ["JR-PLAN-STARTING-CONTRACT", { startingContract: "other" }],
    ["JR-PLAN-SLOT", { currentSlot: "b" }]
  ]) {
    expectCode(code, () => planRelease(fixture.manifest, { ...fixture.device, ...change }));
  }
});

test("signed input cannot escape action, target, mode, artifact, or data policy", () => {
  const cases = [
    ["JR-PLAN-ACTION", operation => { operation.action = "unlock"; }],
    ["JR-PLAN-TARGET", operation => { operation.target = "vendor"; }],
    ["JR-PLAN-MODE", operation => { operation.mode = "fastbootd"; }],
    ["JR-PLAN-ARTIFACT", operation => { operation.artifactId = "missing"; }]
  ];
  for (const [code, mutate] of cases) {
    const manifest = clone(fixture.manifest);
    mutate(manifest.operations[4]);
    expectCode(code, () => planRelease(manifest, fixture.device));
  }
  const erase = clone(fixture.manifest);
  erase.operations.splice(1, 0, { id: "erase-data", action: "erase", mode: "fastbootd", target: "userdata" });
  expectCode("JR-PLAN-DATA-POLICY", () => planRelease(erase, fixture.device));
});

test("duplicate identifiers and repeated target writes stop", () => {
  const duplicateArtifact = clone(fixture.manifest);
  duplicateArtifact.artifacts.push(clone(duplicateArtifact.artifacts[0]));
  expectCode("JR-PLAN-DUPLICATE", () => planRelease(duplicateArtifact, fixture.device));
  const repeatedTarget = clone(fixture.manifest);
  repeatedTarget.operations.splice(3, 0, { ...clone(repeatedTarget.operations[1]), id: "flash-system-again" });
  expectCode("JR-PLAN-DUPLICATE", () => planRelease(repeatedTarget, fixture.device));
});
