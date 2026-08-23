export function isInstallAllowed(state) {
  return state.capability?.installAllowed === true
    && state.name === "PACKAGE_READY"
    && state.device?.unlocked === true
    && Boolean(state.package);
}
