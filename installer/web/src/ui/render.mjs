import { preparationSteps, rabbitFastbootFallback } from "../preparation/steps.mjs";
import { isInstallAllowed } from "../capability/install-gate.mjs";

const reasonText = Object.freeze({
  "JR-CAPABILITY-SECURE-CONTEXT": "Open the installer from its HTTPS address.",
  "JR-CAPABILITY-WEBUSB": "This browser does not expose WebUSB.",
  "JR-CAPABILITY-WEBSERIAL": "This browser does not expose Web Serial.",
  "JR-CAPABILITY-EXACT-TUPLE-UNKNOWN": "The exact browser and operating-system build could not be verified.",
  "JR-CAPABILITY-TUPLE-UNACCEPTED": "This exact browser and operating-system tuple has not completed physical acceptance."
});

function escape(value) {
  const replacements = { "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" };
  return String(value).replace(/[&<>'"]/g, character => replacements[character]);
}

function capabilityRows(state) {
  if (!state.capability) return '<p class="quiet">Checking secure context and browser device APIs…</p>';
  const { capabilities, tuple } = state.capability;
  const rows = [["HTTPS", capabilities.secureContext], ["WebUSB", capabilities.webUsb], ["Web Serial", capabilities.webSerial]];
  return `
    <div class="checks">${rows.map(([label, pass]) => `<div><span>${escape(label)}</span><strong class="${pass ? "pass" : "fail"}">${pass ? "Available" : "Unavailable"}</strong></div>`).join("")}</div>
    ${tuple ? `<p class="tuple">${escape(tuple.platform)} ${escape(tuple.platformVersion)} · ${escape(tuple.browser)} ${escape(tuple.browserVersion)} · ${escape(tuple.architecture)} ${escape(tuple.bitness)}-bit</p>` : '<p class="tuple">Exact host tuple unavailable</p>'}`;
}

function hostUsbGuidance(state) {
  const platform = state.capability?.tuple?.platform;
  if (platform === "Linux") {
    return '<div class="notice"><strong>Linux one-time USB setup</strong><p>Before flashing, an administrator must install the packaged <code>51-jackrabbit-r1.rules</code> udev rule. The browser and flashing process still run as your normal user. This grants access only to the R1 bootloader and fastbootd USB identities.</p></div>';
  }
  if (platform === "Windows") {
    return '<div class="notice"><strong>Windows USB driver check</strong><p>If Windows reports access denied, the R1 fastboot interfaces need a WinUSB-compatible driver before the browser can claim them. The installer will stop and keep the reconnect action available.</p></div>';
  }
  if (platform === "macOS") {
    return '<div class="notice"><strong>macOS USB check</strong><p>No Linux udev setup applies. Close native adb/fastboot tools and other installer tabs so Chrome can claim the R1 exclusively.</p></div>';
  }
  return "";
}

function preparationCards() {
  return preparationSteps.map((step, index) => `
    <article class="instruction"><span class="step-number">${index + 1}</span><div><h3>${escape(step.title)}</h3><p>${escape(step.body)}</p><p class="quiet">Expected: ${escape(step.expected)}</p>${step.href ? `<a href="${step.href}" target="_blank" rel="noreferrer">${escape(step.linkLabel)} <span aria-hidden="true">↗</span></a>` : ""}</div></article>`).join("");
}

export function createRenderer(root, actions) {
  return state => {
    const blocked = state.name === "BLOCKED";
    const canEnterFastboot = state.capability?.capabilities.secureContext && state.capability?.capabilities.webSerial;
    const canConnect = state.capability?.capabilities.secureContext && state.capability?.capabilities.webUsb && ["READY", "BLOCKED", "ERROR"].includes(state.name);
    const canUnlock = state.name === "CONNECTED" && state.device?.mode === "bootloader" && state.device?.currentSlot === "a" && !state.device?.unlocked;
    const canSelectPackage = state.device?.unlocked && ["CONNECTED", "VERIFYING", "PACKAGE_READY", "ERROR"].includes(state.name);
    const canInstall = isInstallAllowed(state);
    const canReconnect = state.name === "INSTALLING" && state.progress?.requiresUserAction && state.progress?.expectedMode;
    const verificationPercent = state.progress?.total ? Math.floor((state.progress.completed / state.progress.total) * 100) : 0;
    const installPercent = state.progress?.fraction === null
      ? Math.floor(((state.progress?.step ?? 0) / (state.progress?.total ?? 1)) * 100)
      : Math.floor((((state.progress?.step ?? 0) + (state.progress?.fraction ?? 0)) / (state.progress?.total ?? 1)) * 100);
    root.innerHTML = `
      <div class="page-shell">
        <header class="brand"><span class="mark" aria-hidden="true">J</span><div><strong>JackRabbit</strong><span>R1 installer · ${escape(actions.version)}</span></div><span class="state-pill ${state.name.toLowerCase()}">${escape(state.name)}</span></header>
        <section class="hero"><p class="eyebrow">One guided install</p><h1>Give your r1 a new voice.</h1><p>Prepare the device, enter FASTBOOT, verify the exact JackRabbit release package, and install without typing partition commands.</p></section>
        <div class="layout">
          <section class="panel capability"><div class="panel-heading"><span>01</span><div><h2>Check this computer</h2><p>No USB permission is requested during this check.</p></div></div>${capabilityRows(state)}
            ${hostUsbGuidance(state)}
            ${blocked ? `<div class="notice"><strong>Installation is stopped safely.</strong><ul>${state.capability.reasons.map(reason => `<li>${escape(reasonText[reason] ?? reason)}</li>`).join("")}</ul></div>` : ""}
          </section>
          <section class="panel prepare"><div class="panel-heading"><span>02</span><div><h2>Prepare your R1</h2><p>Complete these physical steps before connecting.</p></div></div>${preparationCards()}</section>
          <section class="panel fastboot"><div class="panel-heading"><span>03</span><div><h2>Enter FASTBOOT</h2><p>Use the same MediaTek preloader transition as Rabbit's official browser tool.</p></div></div>
            <div class="fallback"><div><strong>Enter FASTBOOT here</strong><p>Power the R1 off and disconnect it. Click the button, connect the USB cable, then select MT65xx Preloader.</p><p class="quiet">The installer sends only the exact FASTBOOT entry command. Wait for FASTBOOT on the R1 screen.</p></div><button id="enter-fastboot" class="primary" ${canEnterFastboot ? "" : "disabled"}>Enter Fastboot Mode</button></div>
            ${state.entry ? '<div class="device-result"><strong>FASTBOOT command sent</strong><p>Wait for FASTBOOT on the R1 screen, then select the R1 below.</p></div>' : ""}
            <div class="fallback"><div><strong>${escape(rabbitFastbootFallback.title)}</strong><p>${escape(rabbitFastbootFallback.body)}</p><p class="quiet">${escape(rabbitFastbootFallback.warning)}</p></div><a class="primary" href="${rabbitFastbootFallback.href}" target="_blank" rel="noreferrer">${escape(rabbitFastbootFallback.linkLabel)} <span aria-hidden="true">↗</span></a></div>
          </section>
          <section class="panel connect"><div class="panel-heading"><span>04</span><div><h2>Connect and verify</h2><p>The installer reads identity, unlock, slot, mode, and transfer capacity. It does not write.</p></div></div>
            ${state.device ? `<div class="device-result"><strong>R1 verified read-only</strong><dl><div><dt>Product</dt><dd>${escape(state.device.product)}</dd></div><div><dt>Mode</dt><dd>${escape(state.device.mode)}</dd></div><div><dt>Slot</dt><dd>${escape(state.device.currentSlot)}</dd></div><div><dt>Unlocked</dt><dd>${state.device.unlocked ? "Yes" : "No"}</dd></div></dl></div>` : ""}
            ${state.error ? `<div class="notice error"><strong>${escape(state.error.code ?? "JR-INSTALLER-ERROR")}</strong><p>${escape(state.error.message)}</p></div>` : ""}
            <button id="connect-r1" class="primary" ${canConnect ? "" : "disabled"}>Select R1 in FASTBOOT</button>
            <p class="quiet">${canConnect ? "A browser device chooser opens after this button." : "Use Chrome or Edge from the published HTTPS installer."}</p>
            ${canUnlock ? '<div class="notice error"><strong>Bootloader unlock required</strong><p>Confirm that Rabbithole Developer → Device modification → Unlock is enabled. Unlocking erases all R1 data.</p><button id="unlock-r1" class="primary">Unlock R1</button></div>' : ""}
            ${state.name === "UNLOCKING" ? '<div class="notice"><strong>Unlocking R1…</strong><p>Keep USB connected. After verification, the installer continues to the package step.</p></div>' : ""}
            ${state.device?.unlocked ? '<div class="notice"><strong>Bootloader unlocked</strong><p>The unlock branch has rejoined the main installation flow. Continue below.</p></div>' : ""}
          </section>
          <section class="panel package"><div class="panel-heading"><span>05</span><div><h2>Verify installation package</h2><p>Select the extracted current JackRabbit stock-R1 package. Every required image is size- and SHA-256-verified before a write.</p></div></div>
            <label class="primary file-button ${canSelectPackage ? "" : "disabled"}">Select package folder<input id="select-package" type="file" webkitdirectory multiple ${canSelectPackage ? "" : "disabled"}></label>
            ${state.name === "VERIFYING" ? `<div class="device-result"><strong>Verifying package · ${verificationPercent}%</strong><p>${escape(state.progress?.path ?? "Checking inventory…")}</p><progress max="100" value="${verificationPercent}"></progress></div>` : ""}
            ${state.package ? `<div class="device-result"><strong>Package verified</strong><p>${escape(state.package.releaseId)} · ${state.package.artifactCount} exact image files</p></div>` : ""}
          </section>
          <section class="panel install"><div class="panel-heading"><span>06</span><div><h2>Install and reboot</h2><p>Writes both boot slots, verified-boot metadata, stock super, JackRabbit/CipherOS logical partitions, erases userdata, selects slot A, and reboots.</p></div></div>
            ${state.capability && !state.capability.installAllowed ? '<div class="notice"><strong>Use the guided CLI on this computer</strong><p>This browser is missing HTTPS, WebUSB, or Web Serial support. Use the same verified package with: <code>jackrabbit-installer install RELEASE_DIRECTORY</code>.</p></div>' : ""}
            ${state.name === "INSTALLING" ? `<div class="device-result"><strong>${escape(state.progress?.label ?? "Installing…")}</strong><p>${installPercent}% · operation ${(state.progress?.step ?? 0) + 1} of ${state.progress?.total ?? 22}</p><progress max="100" value="${installPercent}"></progress><p class="quiet">${state.progress?.label?.includes("screen may go blank") ? "The screen may go blank during this write. Keep the cable connected and follow this progress bar." : "Do not disconnect the R1."}</p></div>` : ""}
            ${canReconnect ? `<div class="notice"><strong>USB mode changed</strong><p>${state.progress.expectedMode === "fastbootd" ? "Choose the R1 listed as Android Fastboot (18d1:4ee0). On Linux, a missing udev rule may prevent selection." : "Choose the R1 displaying FASTBOOT (0e8d:201c)."}</p><button id="reconnect-r1" class="primary">Select R1 and continue</button></div>` : ""}
            ${state.name === "INSTALLING" && state.error ? `<div class="notice error"><strong>${escape(state.error.code ?? "JR-RECONNECT-ERROR")}</strong><p>${escape(state.error.message)}</p><p>Correct the USB permission or selection issue, then use the same reconnect button again.</p></div>` : ""}
            ${state.name === "COMPLETE" ? '<div class="notice"><strong>JackRabbit installed and rebooting</strong><p>The complete current HOME, runtime, management UI, and motor service are already in the flashed image. The screen may remain blank during early first boot; keep the R1 powered and wait for JackRabbit.</p></div>' : ""}
            <button id="install-r1" class="primary" ${canInstall ? "" : "disabled"}>Install JackRabbit</button>
            <p class="quiet">A final typed confirmation is required. Installation cannot start until the host, device, and package verification gates all pass.</p>
          </section>
        </div>
        <footer><span>No telemetry. No account. No server-side device control.</span><span>Source version ${escape(actions.version)}</span></footer>
      </div>`;
    root.querySelector("#enter-fastboot")?.addEventListener("click", actions.enterFastboot);
    root.querySelector("#connect-r1")?.addEventListener("click", actions.connect);
    root.querySelector("#unlock-r1")?.addEventListener("click", actions.unlock);
    root.querySelector("#reconnect-r1")?.addEventListener("click", actions.reconnect);
    root.querySelector("#select-package")?.addEventListener("change", event => actions.selectPackage(event.target.files));
    root.querySelector("#install-r1")?.addEventListener("click", actions.install);
  };
}
