# syntax=docker/dockerfile:1
#
# JackRabbit APK builder image.
#
# A pinned Linux toolchain for android/scripts/build_debug.sh: JDK 17,
# Android SDK (API 36 + Build Tools 36.0.0), Gradle 9.5.0, and the Chaquopy
# CPython 3.13.2 build host. It mirrors the reference environment that
# GitHub Actions uses in .github/workflows/apk-build.yml, with the exact
# /tmp layout build_debug.sh hardcodes, so the build script runs unchanged.
#
# The debug signing key is NEVER baked into this image. CI (and local builds)
# mount ~/.android/debug.keystore into the container at runtime, read-only.
#
# Bumping a toolchain: change the ARG below, then run the
# apk-builder-image.yml workflow to publish a new tag and update
# APK_BUILDER_IMAGE in apk-build.yml.

ARG BASE_IMAGE=eclipse-temurin:17-jdk-noble
FROM ${BASE_IMAGE}

ARG TARGETARCH=amd64
ARG GRADLE_VERSION=9.5.0
ARG CMDLINE_TOOLS_URL=https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
ARG ANDROID_PLATFORM=android-36
ARG ANDROID_BUILD_TOOLS=36.0.0
ARG PY_VERSION=3.13.2
ARG PY_BUILD_DATE=20250212
ARG IMAGE_VERSION=dev

LABEL org.opencontainers.image.title="JackRabbit APK builder" \
      org.opencontainers.image.description="Pinned Linux toolchain (JDK 17, Android SDK 36, Gradle 9.5.0, CPython 3.13.2) for android/scripts/build_debug.sh" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.source="https://github.com/ReSono-Labs/JackRabbit-OS"

# Base tools: curl/unzip for toolchain downloads, git, and ripgrep (required
# by android/scripts/check_boundaries.sh / check_runtime_package.sh).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl unzip git ripgrep \
 && rm -rf /var/lib/apt/lists/*

# --- Android SDK (cmdline-tools -> /opt/android-sdk/cmdline-tools/latest) ---
RUN mkdir -p /opt/android-sdk/cmdline-tools \
 && curl -fsSL -o /tmp/cmdline-tools.zip "${CMDLINE_TOOLS_URL}" \
 && unzip -q /tmp/cmdline-tools.zip -d /opt/android-sdk/cmdline-tools \
 && mv /opt/android-sdk/cmdline-tools/cmdline-tools /opt/android-sdk/cmdline-tools/latest \
 && rm /tmp/cmdline-tools.zip

RUN yes | /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk --licenses >/dev/null 2>&1 || true
RUN /opt/android-sdk/cmdline-tools/latest/bin/sdkmanager --sdk_root=/opt/android-sdk \
      "platform-tools" "platforms;${ANDROID_PLATFORM}" "build-tools;${ANDROID_BUILD_TOOLS}"

# --- Gradle ---
RUN curl -fsSL -o /tmp/gradle-bin.zip \
      "https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip" \
 && unzip -q /tmp/gradle-bin.zip -d /opt \
 && rm /tmp/gradle-bin.zip

# --- Chaquopy build Python (python-build-standalone, same release as CI) ---
# The tarball extracts a python/ tree; the "+" in the asset name is URL-encoded.
RUN PY_HOST="$(case "${TARGETARCH}" in amd64) echo x86_64;; arm64) echo aarch64;; *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1;; esac)" \
 && PY_TRIPLET="${PY_HOST}-unknown-linux-gnu" \
 && curl -fsSL -o /tmp/cpython.tgz \
      "https://github.com/astral-sh/python-build-standalone/releases/download/${PY_BUILD_DATE}/cpython-${PY_VERSION}%2B${PY_BUILD_DATE}-${PY_TRIPLET}-install_only.tar.gz" \
 && mkdir -p /tmp/compile-python "/opt/resono-python/cpython-${PY_VERSION}-linux-${PY_HOST}-gnu" \
 && tar -xzf /tmp/cpython.tgz -C /tmp/compile-python \
 && cp -a /tmp/compile-python/python/. "/opt/resono-python/cpython-${PY_VERSION}-linux-${PY_HOST}-gnu/" \
 && rm -rf /tmp/cpython.tgz /tmp/compile-python \
 && mkdir -p /tmp/resono-python \
 && ln -s "/opt/resono-python/cpython-${PY_VERSION}-linux-${PY_HOST}-gnu" \
          "/tmp/resono-python/cpython-${PY_VERSION}-linux-x86_64-gnu"

# --- Reference /tmp layout that android/scripts/build_debug.sh hardcodes ---
RUN mkdir -p /tmp/resono-python \
 && ln -s /opt/java/openjdk /tmp/r1-jdk17 \
 && ln -s /opt/android-sdk /tmp/r1-android-sdk \
 && ln -s "/opt/gradle-${GRADLE_VERSION}" /tmp/gradle-9.5.0

ENV ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/opt/java/openjdk \
    LANG=C.UTF-8

# --- Sanity-check the whole toolchain at build time ---
RUN /tmp/r1-jdk17/bin/java -version \
 && /tmp/gradle-9.5.0/bin/gradle --version | head -5 \
 && /tmp/resono-python/cpython-3.13.2-linux-x86_64-gnu/bin/python3.13 --version \
 && ls /opt/android-sdk/platform-tools/adb \
      /opt/android-sdk/platforms/android-36 \
      /opt/android-sdk/build-tools/36.0.0 \
 && rg --version | head -1 \
 && git --version
