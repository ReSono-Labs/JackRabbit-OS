import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  root: resolve(import.meta.dirname, "web"),
  build: {
    outDir: resolve(import.meta.dirname, "dist", "web"),
    emptyOutDir: true,
    sourcemap: false,
    target: "es2022"
  },
  server: { host: "127.0.0.1", port: 4173, strictPort: true },
  preview: { host: "127.0.0.1", port: 4173, strictPort: true }
});
