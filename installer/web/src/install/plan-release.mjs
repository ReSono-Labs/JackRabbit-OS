import { ContractError } from "../release/contract-validator.mjs";

const flashTargets = Object.freeze({
  bootloader: new Set(["boot", "vbmeta", "vbmeta_system", "vbmeta_vendor"]),
  fastbootd: new Set(["system", "system_ext", "product", "vendor"])
});
const eraseTargets = new Set(["userdata", "metadata"]);
const rebootTargets = Object.freeze({
  bootloader: new Set(["fastbootd", "system"]),
  fastbootd: new Set(["bootloader"])
});

function deny(code, message) {
  throw new ContractError(code, message);
}

function immutable(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const child of Object.values(value)) immutable(child);
  }
  return value;
}

export function planRelease(manifest, device) {
  if (!device || device.unlocked !== true) deny("JR-PLAN-LOCKED", "bootloader is not machine-verified as unlocked");
  if (!manifest.startingContracts.includes(device.startingContract)) {
    deny("JR-PLAN-STARTING-CONTRACT", "device starting contract is not accepted by this release");
  }
  if (!manifest.products.includes(device.product)) deny("JR-PLAN-PRODUCT", "device product is not accepted by this release");
  if (!manifest.slots.includes(device.currentSlot)) deny("JR-PLAN-SLOT", "device slot is not accepted by this release");
  if (!flashTargets[device.mode]) deny("JR-PLAN-MODE", "device mode is not recognized");

  const artifacts = new Map();
  for (const artifact of manifest.artifacts) {
    if (artifacts.has(artifact.id)) deny("JR-PLAN-DUPLICATE", `duplicate artifact id: ${artifact.id}`);
    artifacts.set(artifact.id, artifact);
  }

  const operationIds = new Set();
  const writtenTargets = new Set();
  let mode = device.mode;
  const operations = manifest.operations.map(operation => {
    if (operationIds.has(operation.id)) deny("JR-PLAN-DUPLICATE", `duplicate operation id: ${operation.id}`);
    operationIds.add(operation.id);
    if (operation.mode !== mode) deny("JR-PLAN-MODE", `operation ${operation.id} requires ${operation.mode} while device plan is ${mode}`);

    if (operation.action === "flash") {
      if (!flashTargets[mode]?.has(operation.target)) deny("JR-PLAN-TARGET", `flash target is not allowed in ${mode}: ${operation.target}`);
      if (writtenTargets.has(operation.target)) deny("JR-PLAN-DUPLICATE", `target is written more than once: ${operation.target}`);
      const artifact = artifacts.get(operation.artifactId);
      if (!artifact) deny("JR-PLAN-ARTIFACT", `operation ${operation.id} references an unknown artifact`);
      writtenTargets.add(operation.target);
      return { ...operation, artifact: { ...artifact } };
    }
    if (operation.action === "erase") {
      if (manifest.dataPolicy !== "erase") deny("JR-PLAN-DATA-POLICY", "erase operation is forbidden by preserve data policy");
      if (!eraseTargets.has(operation.target)) deny("JR-PLAN-TARGET", `erase target is not allowed: ${operation.target}`);
      return { ...operation };
    }
    if (operation.action === "reboot") {
      if (!rebootTargets[mode]?.has(operation.target)) deny("JR-PLAN-TARGET", `reboot transition is not allowed: ${mode} to ${operation.target}`);
      mode = operation.target === "fastbootd" ? "fastbootd" : "bootloader";
      return { ...operation };
    }
    deny("JR-PLAN-ACTION", `action is not allowed: ${operation.action}`);
  });

  return immutable({
    releaseId: manifest.releaseId,
    profile: manifest.profile,
    dataPolicy: manifest.dataPolicy,
    startingContract: device.startingContract,
    product: device.product,
    currentSlot: device.currentSlot,
    recoveryRuleId: manifest.recoveryRuleId,
    operations
  });
}
