import { access, readFile, readdir, stat } from "node:fs/promises";
import { constants } from "node:fs";
import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const readJson = async path => JSON.parse(await readFile(join(root, path), "utf8"));
const stockR1Release = await readJson("contracts/current-release-v0.2.json");
const contract = await readJson("contracts/host-dependencies-v1.json");
const provenance = await readJson("provenance/sources.json");
const sources = new Map(provenance.sources.map(source => [source.id, source]));
const digestCache = new Map();

function fail(code, message) {
  process.stderr.write(`JR-HOST-PACKAGE-${code}: ${message}\n`);
  process.exit(1);
}

async function sha256(path) {
  const info = await stat(path);
  const key = `${info.dev}:${info.ino}:${info.size}`;
  if (!digestCache.has(key)) {
    digestCache.set(key, new Promise((resolveDigest, reject) => {
      const digest = createHash("sha256");
      const stream = createReadStream(path);
      stream.on("error", reject);
      stream.on("data", chunk => digest.update(chunk));
      stream.on("end", () => resolveDigest(digest.digest("hex")));
    }));
  }
  return digestCache.get(key);
}

for (const [platform, sourceId] of [
  ["linux-x64", "android-platform-tools-linux"],
  ["macos-x64", "android-platform-tools-macos"],
  ["macos-arm64", "android-platform-tools-macos"],
  ["windows-x64", "android-platform-tools-windows"]
]) {
  const dependency = contract.platformTools[platform];
  const source = sources.get(sourceId);
  if (!dependency || dependency.url !== source?.url || dependency.sha256 !== source?.sha256) {
    fail("PIN", `${platform} Platform Tools contract and provenance differ`);
  }
}

for (const [name, sourceId] of [
  ["rabbitMediaTekPreloader", "rabbit-mediatek-windows-driver"],
  ["googleUsbDriver", "google-usb-driver-windows"]
]) {
  const dependency = contract.windowsDrivers[name];
  const source = sources.get(sourceId);
  if (!dependency || dependency.url !== source?.url || dependency.sha256 !== source?.sha256) {
    fail("PIN", `${name} contract and provenance differ`);
  }
}

const linuxRule = await readFile(join(root, "linux-macos/drivers/51-jackrabbit-r1.rules"), "utf8");
for (const identity of ["2000", "201c", "4ee0"]) {
  if (!linuxRule.includes(`idProduct}==\"${identity}\"`)) fail("LINUX-RULE", `missing R1 USB product ${identity}`);
}
if (!linuxRule.includes('SUBSYSTEM=="tty"') || !linuxRule.includes('ATTRS{idProduct}=="2000"')) {
  fail("LINUX-RULE", "missing preloader serial-node access");
}

const unixLauncher = await readFile(join(root, "linux-macos/install.sh"), "utf8");
for (const required of ["Press Enter to configure R1 USB access", "ENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?", 'release_root="$package_root/../../release"', 'JACKRABBIT_FASTBOOT="$package_root/tools/fastboot"', 'exec "$installer_binary" install "$release_root"']) {
  if (!unixLauncher.includes(required)) fail("UNIX-LAUNCHER", `missing ${required}`);
}

const windowsLauncher = await readFile(join(root, "windows/install.ps1"), "utf8");
const windowsDrivers = await readFile(join(root, "windows/install-drivers.ps1"), "utf8");
for (const required of ["Press Enter to install or repair", "ENTRY INCORRECT. WOULD YOU LIKE TO CANCEL?", "jackrabbit-installer.exe", '"..\\..\\release"', "JACKRABBIT_FASTBOOT", "install $Release"]) {
  if (!windowsLauncher.includes(required)) fail("WINDOWS-LAUNCHER", `missing ${required}`);
}
for (const required of ["MediaTek_Preloader_USB_VCOM_drivers.exe", "android_winusb.inf", "pnputil.exe", "-Verb RunAs"]) {
  if (!windowsDrivers.includes(required)) fail("WINDOWS-DRIVER", `missing ${required}`);
}

const stageScript = await readFile(join(root, "scripts/stage-host-package.sh"), "utf8");
const assemblyScript = await readFile(join(root, "scripts/assemble-host-packages.sh"), "utf8");
for (const platform of ["linux-x64", "macos-x64", "macos-arm64", "windows-x64"]) {
  if (!stageScript.includes(platform)) fail("TARGET", `package builder is missing ${platform}`);
}
for (const source of ["linux-macos/install.sh", "linux-macos/install.command", "windows/install.cmd", "windows/install.ps1", "windows/install-drivers.ps1"]) {
  if (!stageScript.includes(source.split("/").at(-1))) fail("TARGET", `package builder does not include ${source}`);
}
for (const documentation of ["INSTALL.md", "TROUBLESHOOTING.md"]) {
  if (!stageScript.includes(documentation)) fail("DOCUMENTATION", `package builder does not include ${documentation}`);
}
for (const required of ["linux-x64 macos-x64 macos-arm64 windows-x64", "verify-release-directory.mjs", "cmp -s"]) {
  if (!assemblyScript.includes(required)) fail("ASSEMBLY", `four-package assembly is missing ${required}`);
}

const cliFastboot = await readFile(join(root, "cli/src/fastboot.rs"), "utf8");
const cliInstall = await readFile(join(root, "cli/src/install.rs"), "utf8");
const troubleshooting = await readFile(join(root, "TROUBLESHOOTING.md"), "utf8");
for (const required of ["fastboot_failed(output.status.success(), &text)", 'line.contains("FAILED")']) {
  if (!cliFastboot.includes(required)) fail("CLI-FASTBOOT", `shared engine is missing ${required}`);
}
const cliRelease = await readFile(join(root, "cli/src/release.rs"), "utf8");
for (const artifact of stockR1Release.artifacts) {
  if (!cliRelease.includes(artifact.path) || !cliRelease.includes(artifact.sha256)) {
    fail("RELEASE-CONTRACT", `shared CLI inventory differs at ${artifact.path}`);
  }
}
for (const required of ["missing_system_ext(&error.to_string())", "system_ext_size(&output_text)", "enter_or_find_fastboot", "incorrect_then_retry_or_cancel"]) {
  if (!cliInstall.includes(required)) fail("CLI-INSTALL", `shared engine is missing ${required}`);
}
const cliSourceFiles = await Promise.all((await readdir(join(root, "cli/src"))).filter(name => name.endsWith(".rs")).map(name => readFile(join(root, "cli/src", name), "utf8")));
const cliErrorCodes = new Set(cliSourceFiles.flatMap(source => source.match(/JR-CLI-[A-Z0-9-]+/g) ?? []));
for (const code of cliErrorCodes) {
  if (!troubleshooting.includes(`\`${code}\``)) fail("DOCUMENTATION", `TROUBLESHOOTING.md is missing ${code}`);
}

const bundleRoot = join(root, "dist/bundles/jackrabbit-current-v0.2");
const releaseRoot = join(bundleRoot, "release");
const packageRoot = join(bundleRoot, "hosts");
let stagedPackages = [];
try {
  stagedPackages = (await readdir(packageRoot, { withFileTypes: true }))
    .filter(entry => entry.isDirectory())
    .map(entry => entry.name);
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}

const packageFiles = {
  "linux-x64": ["README.md", "INSTALL.md", "TROUBLESHOOTING.md", "install.sh", "bin/jackrabbit-installer", "tools/fastboot", "drivers/51-jackrabbit-r1.rules"],
  "macos-x64": ["README.md", "INSTALL.md", "TROUBLESHOOTING.md", "install.sh", "install.command", "bin/jackrabbit-installer", "tools/fastboot"],
  "macos-arm64": ["README.md", "INSTALL.md", "TROUBLESHOOTING.md", "install.sh", "install.command", "bin/jackrabbit-installer", "tools/fastboot"],
  "windows-x64": ["README.md", "INSTALL.md", "TROUBLESHOOTING.md", "install.cmd", "install.ps1", "install-drivers.ps1", "bin/jackrabbit-installer.exe", "tools/fastboot.exe"]
};

try {
  await access(releaseRoot, constants.R_OK);
  for (const artifact of stockR1Release.artifacts) {
    const imagePath = join(releaseRoot, artifact.path);
    const info = await stat(imagePath);
    if (info.size !== artifact.size) fail("SHARED-IMAGE-SIZE", `${artifact.path} has the wrong size`);
    if (await sha256(imagePath) !== artifact.sha256) fail("SHARED-IMAGE-HASH", `${artifact.path} has the wrong SHA-256`);
  }
} catch (error) {
  if (error.code !== "ENOENT") throw error;
}

for (const packageName of stagedPackages) {
  if (!Object.hasOwn(packageFiles, packageName)) fail("STAGED-NAME", `unexpected host directory ${packageName}`);
  const platform = packageName;
  const staged = join(packageRoot, packageName);
  for (const required of packageFiles[platform]) {
    const info = await stat(join(staged, required));
    if (!info.isFile()) fail("STAGED-FILE", `${packageName} is missing ${required}`);
  }

  const sourceCopies = platform === "windows-x64"
    ? [["windows/README.md", "README.md"], ["windows/install.cmd", "install.cmd"], ["windows/install.ps1", "install.ps1"], ["windows/install-drivers.ps1", "install-drivers.ps1"]]
    : [["linux-macos/README.md", "README.md"], ["linux-macos/install.sh", "install.sh"], ...(platform.startsWith("macos") ? [["linux-macos/install.command", "install.command"]] : []), ...(platform === "linux-x64" ? [["linux-macos/drivers/51-jackrabbit-r1.rules", "drivers/51-jackrabbit-r1.rules"]] : [])];
  sourceCopies.push(["contracts/host-dependencies-v1.json", "HOST-DEPENDENCIES.json"]);
  sourceCopies.push(["INSTALL.md", "INSTALL.md"], ["TROUBLESHOOTING.md", "TROUBLESHOOTING.md"]);
  for (const [source, packaged] of sourceCopies) {
    if (await readFile(join(root, source), "utf8") !== await readFile(join(staged, packaged), "utf8")) {
      fail("STAGED-SOURCE", `${packageName}/${packaged} differs from ${source}`);
    }
  }

  try {
    await access(join(staged, "release"));
    fail("DUPLICATE-IMAGES", `${packageName} contains a private release directory instead of using the shared release`);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }

  if (platform === "linux-x64") {
    const builtCli = join(root, "cli/target/release/jackrabbit-installer-cli");
    try {
      await access(builtCli, constants.R_OK);
      const [built, packaged] = await Promise.all([readFile(builtCli), readFile(join(staged, "bin/jackrabbit-installer"))]);
      if (!built.equals(packaged)) fail("STAGED-CLI", `${packageName} CLI differs from the current release build`);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
  }
}

process.stdout.write("JR-HOST-PACKAGE-OK\n");
