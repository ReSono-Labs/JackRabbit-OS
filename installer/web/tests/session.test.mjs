import assert from "node:assert/strict";
import test from "node:test";
import { createSession } from "../src/app/session.mjs";
import { isInstallAllowed } from "../src/capability/install-gate.mjs";

const capable = Object.freeze({ installAllowed: true, exactSupport: { readOnlyFastboot: true } });

test("installation requires browser, device, unlock, and package gates", () => {
  const ready = { name: "PACKAGE_READY", device: { unlocked: true }, package: { releaseId: "current" } };
  assert.equal(isInstallAllowed({ ...ready, capability: capable }), true);
  assert.equal(isInstallAllowed({ ...ready, capability: { installAllowed: false } }), false);
  assert.equal(isInstallAllowed({ ...ready, device: { unlocked: false }, capability: capable }), false);
  assert.equal(isInstallAllowed({ ...ready, package: null, capability: capable }), false);
});

test("session permits the verified connection sequence", () => {
  const states = [];
  const session = createSession(state => states.push(state.name));
  session.capability(capable);
  session.connecting();
  session.connected(Object.freeze({ product: "rabbit-r1" }));
  assert.deepEqual(states, ["READY", "CONNECTING", "CONNECTED"]);
});

test("session rejects skipped transitions", () => {
  const session = createSession(() => {});
  assert.throws(() => session.connected({}), /illegal installer state transition/);
  assert.equal("flash" in session, false);
});

test("session permits a separate unlock operation and returns to verified connection", () => {
  const states = [];
  const session = createSession(state => states.push(state.name));
  session.capability(capable);
  session.connecting();
  session.connected(Object.freeze({ product: "k65v1_64_bsp", unlocked: false }));
  session.unlocking();
  session.unlocked(Object.freeze({ product: "k65v1_64_bsp", unlocked: true }));
  assert.deepEqual(states, ["READY", "CONNECTING", "CONNECTED", "UNLOCKING", "CONNECTED"]);
});

test("locked and already-unlocked paths converge on package verification and install", () => {
  for (const startsUnlocked of [false, true]) {
    const states = [];
    const session = createSession(state => states.push(state.name));
    session.capability(capable);
    session.connecting();
    session.connected(Object.freeze({ product: "k65v1_64_bsp", unlocked: startsUnlocked }));
    if (!startsUnlocked) {
      session.unlocking();
      session.unlocked(Object.freeze({ product: "k65v1_64_bsp", unlocked: true }));
    }
    session.verifying();
    session.packageReady(Object.freeze({ releaseId: "stock-r1", artifactCount: 12 }));
    session.installing(Object.freeze({ step: 0, total: 22 }));
    session.completed(Object.freeze({ operationsCompleted: 22 }));
    assert.deepEqual(states.slice(-4), ["VERIFYING", "PACKAGE_READY", "INSTALLING", "COMPLETE"]);
  }
});

test("installation pauses for a user-authorized USB mode reconnect", () => {
  const states = [];
  const session = createSession(state => states.push([state.name, state.progress?.expectedMode, state.error?.code]));
  session.capability(capable);
  session.connecting();
  session.connected(Object.freeze({ product: "k65v1_64_bsp", unlocked: true }));
  session.verifying();
  session.packageReady(Object.freeze({ releaseId: "current", artifactCount: 12 }));
  session.installing(Object.freeze({ step: 8, total: 22 }));
  session.reconnectRequired(Object.freeze({ step: 9, total: 22, expectedMode: "fastbootd" }));
  session.reconnectFailed(Object.assign(new Error("permission denied"), { code: "JR-USB-PERMISSION" }));
  session.installationProgress(Object.freeze({ step: 9, total: 22, label: "Writing super", fraction: 0 }));
  assert.deepEqual(states.slice(-3), [["INSTALLING", "fastbootd", undefined], ["INSTALLING", "fastbootd", "JR-USB-PERMISSION"], ["INSTALLING", undefined, undefined]]);
});
