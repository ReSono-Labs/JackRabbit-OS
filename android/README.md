# JackRabbit Android application

This is the native Rabbit R1 HOME application. It owns device presentation, hardware input, native WebRTC audio, Android lifecycle, and the Keystore bridge. Runtime provider, agent, tool, and storage behavior remains in `../runtime` and is hosted in the isolated `:runtime` process.

Build and test:

```bash
./scripts/build_debug.sh
```
