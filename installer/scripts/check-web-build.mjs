import { readdir, readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const installerRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const buildRoot = join(installerRoot, "dist", "web");

function fail(code, message) {
  process.stderr.write(`JR-WEB-BUILD-${code}: ${message}\n`);
  process.exit(1);
}

let files;
try {
  files = await readdir(buildRoot, { recursive: true });
} catch {
  fail("MISSING", "run npm run build before checking deployment output");
}

const regularFiles = files.filter(path => path !== "assets");
if (regularFiles.some(path => path.endsWith(".map"))) fail("SOURCE-MAP", "production output contains a source map");
for (const required of ["index.html", "_headers"]) {
  if (!regularFiles.includes(required)) fail("REQUIRED", `production output is missing ${required}`);
}

const scripts = regularFiles.filter(path => /^assets\/index-[A-Za-z0-9_-]+\.js$/.test(path));
const styles = regularFiles.filter(path => /^assets\/index-[A-Za-z0-9_-]+\.css$/.test(path));
if (scripts.length !== 1 || styles.length !== 1) fail("ASSETS", "expected one hashed script and one hashed stylesheet");

const index = await readFile(join(buildRoot, "index.html"), "utf8");
if (!index.includes(`/${scripts[0]}`) || !index.includes(`/${styles[0]}`)) fail("INDEX", "index does not bind the exact hashed assets");
if (index.includes("http://")) fail("INSECURE", "production index contains an insecure URL");

const headers = await readFile(join(buildRoot, "_headers"), "utf8");
for (const required of ["default-src 'self'", "script-src 'self'", "object-src 'none'", "frame-ancestors 'none'", "usb=(self)", "serial=(self)", "Referrer-Policy: no-referrer", "X-Content-Type-Options: nosniff"]) {
  if (!headers.includes(required)) fail("HEADERS", `deployment headers are missing: ${required}`);
}
if (headers.includes("'unsafe-inline'") || headers.includes("'unsafe-eval'")) fail("CSP", "CSP permits unsafe inline/eval execution");

for (const path of regularFiles) {
  const content = await readFile(join(buildRoot, path), "utf8");
  if (/\/(?:home|Users)\/[^/]+\//.test(content) || /[A-Za-z]:\\Users\\/.test(content)) {
    fail("WORKSTATION", `production output contains a workstation path: ${path}`);
  }
}

process.stdout.write(`JR-WEB-BUILD-OK: ${regularFiles.length} files\n`);
