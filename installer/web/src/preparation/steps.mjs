import contract from "../../../contracts/preparation-prompts-v1.json";

function present(prompt) {
  return Object.freeze({
    id: prompt.id,
    title: prompt.title,
    body: prompt.action,
    expected: prompt.expected,
    warning: prompt.warning,
    href: prompt.href,
    linkLabel: prompt.linkLabel
  });
}

if (contract.schemaVersion !== 1) throw new Error("JR-PROMPT-SCHEMA: unsupported physical prompt contract");

export const preparationSteps = Object.freeze(contract.prompts
  .filter(prompt => prompt.phase === "prepare" && prompt.surfaces.includes("web"))
  .map(present));

const officialEntry = contract.prompts.find(prompt => prompt.id === "open-official-entry" && prompt.surfaces.includes("web"));
if (!officialEntry) throw new Error("JR-PROMPT-SCHEMA: official FASTBOOT entry prompt is absent");

export const rabbitFastbootFallback = present(officialEntry);
