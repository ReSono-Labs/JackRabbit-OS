import support from "../../../contracts/support-v1.json";
import packageMetadata from "../../../package.json";
import { isInstallAllowed } from "../capability/install-gate.mjs";
import { probeBrowser } from "../capability/probe-browser.mjs";
import { requestR1FastbootDevice, readR1Snapshot, unlockR1Bootloader } from "../fastboot/read-r1-snapshot.mjs";
import { requestR1Preloader, sendFastbootEntry } from "../preloader/enter-r1-fastboot.mjs";
import { flashStockR1 } from "../fastboot/flash-stock-r1.mjs";
import { stockR1Release } from "../release/stock-r1-release.mjs";
import { verifyStockR1Package } from "../release/select-stock-r1-package.mjs";
import { createRenderer } from "../ui/render.mjs";
import { createSession } from "./session.mjs";
import "../ui/styles.css";

const version = packageMetadata.version;
const root = document.querySelector("#app");
let session;
let selectedFastbootDevice = null;
let selectedPackageFiles = null;
let pendingReconnect = null;
const render = createRenderer(root, {
  version,
  async enterFastboot() {
    try {
      const port = await requestR1Preloader();
      session.entryCompleted(await sendFastbootEntry(port));
    } catch (error) {
      session.failed(error);
    }
  },
  async connect() {
    try {
      session.connecting();
      const device = await requestR1FastbootDevice();
      const snapshot = await readR1Snapshot(device);
      selectedFastbootDevice = device;
      session.connected(snapshot);
    } catch (error) {
      session.failed(error);
    }
  },
  async unlock() {
    const confirmation = globalThis.prompt("Unlocking erases all R1 data. Type ERASE AND UNLOCK R1 to continue.");
    if (confirmation !== "ERASE AND UNLOCK R1") return;
    try {
      if (!selectedFastbootDevice) throw new Error("Select and verify the R1 before unlocking.");
      session.unlocking();
      session.unlocked(await unlockR1Bootloader(selectedFastbootDevice));
    } catch (error) {
      session.failed(error);
    }
  },
  async reconnect() {
    if (!pendingReconnect) return;
    try {
      const selected = await requestR1FastbootDevice(navigator.usb, pendingReconnect.expectedMode);
      const resolve = pendingReconnect.resolve;
      pendingReconnect = null;
      resolve(selected);
    } catch (error) {
      session.reconnectFailed(error);
    }
  },
  async selectPackage(fileList) {
    try {
      session.verifying();
      const selected = await verifyStockR1Package(fileList, stockR1Release, progress => session.verificationProgress(progress));
      selectedPackageFiles = selected.files;
      session.packageReady({ releaseId: selected.releaseId, artifactCount: selected.artifactCount });
    } catch (error) {
      selectedPackageFiles = null;
      session.failed(error);
    }
  },
  async install() {
    if (!isInstallAllowed(session.current())) {
      session.failed(Object.assign(new Error("Installation requires HTTPS, WebUSB, Web Serial, an unlocked verified R1, and a verified release package."), { code: "JR-INSTALL-GATE" }));
      return;
    }
    const confirmation = globalThis.prompt("This erases the R1 and writes the complete JackRabbit/CipherOS base. Type ERASE STOCK R1 AND INSTALL JACKRABBIT to begin.");
    if (confirmation !== "ERASE STOCK R1 AND INSTALL JACKRABBIT") return;
    try {
      if (!selectedFastbootDevice || !selectedPackageFiles) throw new Error("Verify the R1 and installer package before installation.");
      session.installing({ step: 0, total: 22, label: "Starting installation", fraction: 0 });
      const result = await flashStockR1({
        initialDevice: selectedFastbootDevice,
        packageFiles: selectedPackageFiles,
        release: stockR1Release,
        requestReconnect(expectedMode, retryError = null) {
          return new Promise(resolve => {
            pendingReconnect = { expectedMode, resolve };
            session.reconnectRequired({
              step: session.current().progress?.step ?? 0,
              total: 22,
              label: expectedMode === "fastbootd"
                ? "R1 changed to fastbootd. Select it again to continue."
                : "R1 returned to bootloader FASTBOOT. Select it again to finish.",
              fraction: null,
              expectedMode
            });
            if (retryError) session.reconnectFailed(retryError);
          });
        },
        onProgress: progress => session.installationProgress(progress)
      });
      session.completed(result);
    } catch (error) {
      session.failed(error);
    }
  }
});
session = createSession(render);
render(session.current());

try {
  session.capability(await probeBrowser({ support }));
} catch (error) {
  session.failed(error);
}
