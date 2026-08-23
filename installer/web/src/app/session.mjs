const allowed = Object.freeze({
  CHECKING: new Set(["BLOCKED", "READY", "ERROR"]),
  BLOCKED: new Set(["CHECKING", "CONNECTING", "ERROR"]),
  READY: new Set(["CONNECTING", "CHECKING"]),
  CONNECTING: new Set(["CONNECTED", "ERROR"]),
  CONNECTED: new Set(["CHECKING", "UNLOCKING", "VERIFYING"]),
  UNLOCKING: new Set(["CONNECTED", "ERROR"]),
  VERIFYING: new Set(["PACKAGE_READY", "ERROR"]),
  PACKAGE_READY: new Set(["VERIFYING", "INSTALLING", "CONNECTING", "ERROR"]),
  INSTALLING: new Set(["COMPLETE", "ERROR"]),
  COMPLETE: new Set(["CHECKING"]),
  ERROR: new Set(["CHECKING", "CONNECTING", "VERIFYING"])
});

export function createSession(render) {
  let state = Object.freeze({ name: "CHECKING", capability: null, device: null, entry: null, package: null, progress: null, result: null, error: null });
  const publish = next => {
    if (next.name !== state.name && !allowed[state.name].has(next.name)) {
      throw new Error(`illegal installer state transition: ${state.name} to ${next.name}`);
    }
    state = Object.freeze(next);
    render(state);
  };
  return Object.freeze({
    current: () => state,
    capability(result) { publish({ name: (result.entryAllowed ?? result.installAllowed) ? "READY" : "BLOCKED", capability: result, device: null, entry: null, package: null, progress: null, result: null, error: null }); },
    entryCompleted(entry) { publish({ ...state, entry, error: null }); },
    connecting() { publish({ ...state, name: "CONNECTING", error: null }); },
    connected(device) { publish({ ...state, name: "CONNECTED", device, error: null }); },
    unlocking() { publish({ ...state, name: "UNLOCKING", error: null }); },
    unlocked(device) { publish({ ...state, name: "CONNECTED", device, error: null }); },
    verifying(progress = null) { publish({ ...state, name: "VERIFYING", package: null, progress, error: null }); },
    verificationProgress(progress) { publish({ ...state, progress }); },
    packageReady(selectedPackage) { publish({ ...state, name: "PACKAGE_READY", package: selectedPackage, progress: null, error: null }); },
    installing(progress) { publish({ ...state, name: "INSTALLING", progress, error: null }); },
    installationProgress(progress) { publish({ ...state, progress, error: null }); },
    reconnectRequired(progress) { publish({ ...state, name: "INSTALLING", progress: { ...progress, requiresUserAction: true }, error: null }); },
    reconnectFailed(error) { publish({ ...state, name: "INSTALLING", error }); },
    completed(result) { publish({ ...state, name: "COMPLETE", result, progress: null, error: null }); },
    failed(error) { publish({ ...state, name: "ERROR", error }); },
    checking() { publish({ name: "CHECKING", capability: null, device: null, entry: null, package: null, progress: null, result: null, error: null }); }
  });
}
