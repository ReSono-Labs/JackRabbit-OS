import assert from "node:assert/strict";
import test from "node:test";
import { probeBrowser } from "../src/capability/probe-browser.mjs";

const tuple = {
  platform: "Linux",
  platformVersion: "6.1.0",
  architecture: "x86",
  bitness: "64",
  browser: "Google Chrome",
  browserVersion: "150.0.7871.186"
};

function navigatorFor(candidate = tuple) {
  return {
    usb: { requestDevice() {} },
    serial: { requestPort() {} },
    userAgentData: {
      platform: candidate.platform,
      async getHighEntropyValues() {
        return {
          architecture: candidate.architecture,
          bitness: candidate.bitness,
          platformVersion: candidate.platformVersion,
          fullVersionList: [{ brand: candidate.browser, version: candidate.browserVersion }, { brand: "Not_A Brand", version: "99" }]
        };
      }
    }
  };
}

test("available browser APIs permit an acceptance run with an empty support matrix", async () => {
  const result = await probeBrowser({
    windowLike: { isSecureContext: true },
    navigatorLike: navigatorFor(),
    support: { integratedPreloaderEntry: [], readOnlyFastboot: [], install: [] }
  });
  assert.deepEqual(result.capabilities, { secureContext: true, webUsb: true, webSerial: true });
  assert.equal(result.entryAllowed, true);
  assert.equal(result.installAllowed, true);
  assert.deepEqual(result.reasons, []);
  assert.deepEqual(result.acceptanceWarnings, ["JR-CAPABILITY-TUPLE-UNACCEPTED"]);
});

test("only one exact recorded tuple enables its accepted capabilities", async () => {
  const result = await probeBrowser({
    windowLike: { isSecureContext: true },
    navigatorLike: navigatorFor(),
    support: { integratedPreloaderEntry: [tuple], readOnlyFastboot: [tuple], install: [tuple] }
  });
  assert.equal(result.installAllowed, true);
  assert.deepEqual(result.reasons, []);
  assert.deepEqual(result.acceptanceWarnings, []);
});

test("missing secure context, APIs, or exact client hints deny", async () => {
  const result = await probeBrowser({
    windowLike: { isSecureContext: false },
    navigatorLike: {},
    support: { integratedPreloaderEntry: [], readOnlyFastboot: [], install: [] }
  });
  assert.equal(result.installAllowed, false);
  assert.equal(result.entryAllowed, false);
  assert.deepEqual(result.reasons, [
    "JR-CAPABILITY-SECURE-CONTEXT",
    "JR-CAPABILITY-WEBUSB",
    "JR-CAPABILITY-WEBSERIAL"
  ]);
  assert.deepEqual(result.acceptanceWarnings, ["JR-CAPABILITY-EXACT-TUPLE-UNKNOWN"]);
});
