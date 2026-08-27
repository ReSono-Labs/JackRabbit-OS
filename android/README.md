# JackRabbit Android application

This is the native Rabbit R1 HOME application. It owns device presentation, hardware input, native WebRTC audio, Android lifecycle, and the Keystore bridge. Runtime provider, agent, tool, and storage behavior remains in `../runtime` and is hosted in the isolated `:runtime` process.

Build and test:

```bash
# Recommended: pinned Linux toolchain in Docker (no local JDK/SDK/Gradle needed).
./scripts/build_apk_docker.sh

# Or build natively on a Linux host with the reference toolchain (see BUILDING.md).
./scripts/build_debug.sh
```
