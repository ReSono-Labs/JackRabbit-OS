import { verifyArtifact } from "./verify-artifact.mjs";
import { ContractError } from "./contract-validator.mjs";

function relativePath(file) {
  return String(file.webkitRelativePath || file.name).replaceAll("\\", "/");
}

export function indexReleaseFiles(fileList, release) {
  const selected = [...fileList];
  const files = new Map();
  for (const descriptor of release.artifacts) {
    const matches = selected.filter(file => {
      const path = relativePath(file);
      return path === descriptor.path || path.endsWith(`/${descriptor.path}`);
    });
    if (matches.length !== 1) {
      throw new ContractError("JR-PACKAGE-INVENTORY", `Expected exactly one ${descriptor.path}; found ${matches.length}.`);
    }
    if (matches[0].size !== descriptor.size) {
      throw new ContractError("JR-ARTIFACT-SIZE", `File size does not match: ${descriptor.path}`);
    }
    files.set(descriptor.path, matches[0]);
  }
  return files;
}

export async function verifyStockR1Package(fileList, release, onProgress = () => {}) {
  const files = indexReleaseFiles(fileList, release);
  let completed = 0;
  for (const descriptor of release.artifacts) {
    onProgress({ completed, total: release.artifacts.length, path: descriptor.path });
    await verifyArtifact(files.get(descriptor.path).stream(), { ...descriptor, id: descriptor.path });
    completed += 1;
  }
  onProgress({ completed, total: release.artifacts.length, path: null });
  return Object.freeze({ releaseId: release.id, files, artifactCount: completed });
}

