function browserIdentity(fullVersionList = []) {
  const acceptedBrands = new Set(["Google Chrome", "Microsoft Edge", "Chromium"]);
  const candidates = fullVersionList.filter(item => acceptedBrands.has(item.brand));
  return candidates.length === 1 ? candidates[0] : null;
}

function sameTuple(left, right) {
  return ["platform", "platformVersion", "architecture", "bitness", "browser", "browserVersion"]
    .every(field => left[field] === right[field]);
}

export async function probeBrowser({ windowLike = window, navigatorLike = navigator, support }) {
  const capabilities = Object.freeze({
    secureContext: windowLike.isSecureContext === true,
    webUsb: typeof navigatorLike.usb?.requestDevice === "function",
    webSerial: typeof navigatorLike.serial?.requestPort === "function"
  });

  let tuple = null;
  if (navigatorLike.userAgentData?.getHighEntropyValues) {
    const values = await navigatorLike.userAgentData.getHighEntropyValues([
      "architecture",
      "bitness",
      "fullVersionList",
      "platformVersion"
    ]);
    const browser = browserIdentity(values.fullVersionList);
    if (browser) {
      tuple = Object.freeze({
        platform: navigatorLike.userAgentData.platform,
        platformVersion: values.platformVersion,
        architecture: values.architecture,
        bitness: values.bitness,
        browser: browser.brand,
        browserVersion: browser.version
      });
    }
  }

  const exactSupport = tuple
    ? Object.freeze({
        integratedPreloaderEntry: support.integratedPreloaderEntry.some(candidate => sameTuple(candidate, tuple)),
        readOnlyFastboot: support.readOnlyFastboot.some(candidate => sameTuple(candidate, tuple)),
        install: support.install.some(candidate => sameTuple(candidate, tuple))
      })
    : Object.freeze({ integratedPreloaderEntry: false, readOnlyFastboot: false, install: false });

  const reasons = [];
  if (!capabilities.secureContext) reasons.push("JR-CAPABILITY-SECURE-CONTEXT");
  if (!capabilities.webUsb) reasons.push("JR-CAPABILITY-WEBUSB");
  if (!capabilities.webSerial) reasons.push("JR-CAPABILITY-WEBSERIAL");

  const acceptanceWarnings = [];
  if (!tuple) acceptanceWarnings.push("JR-CAPABILITY-EXACT-TUPLE-UNKNOWN");
  else if (!exactSupport.install) acceptanceWarnings.push("JR-CAPABILITY-TUPLE-UNACCEPTED");

  const installAllowed = capabilities.secureContext && capabilities.webUsb && capabilities.webSerial;
  return Object.freeze({ capabilities, tuple, exactSupport, entryAllowed: installAllowed, installAllowed, reasons: Object.freeze(reasons), acceptanceWarnings: Object.freeze(acceptanceWarnings) });
}
