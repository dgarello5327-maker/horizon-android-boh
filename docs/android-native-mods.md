# Android native mod support plan

Status: Android can import and validate .hnmod source bundles and can now
compile one into a separate ARM64 Android APK through a manual GitHub Actions
workflow. The build downloads the bundle over HTTPS, checks its manifest and
revision pins, applies the pinned horizon-mixins tool to the exact pinned
Horizon source, reapplies this fork's Android-port changes, and builds the
horizon-android package for aarch64-linux-android.

The workflow requires an explicit yes-I-trust-this-native-code selection.
The resulting APK is published as a GitHub Actions artifact under the separate
development package ID dev.horizon.android.dev, so it does not replace the
normal Android app. Each workflow run uses a temporary signing key; to install
a later build over an earlier development APK, uninstall the old development
APK first. The main app and its data are left alone.

This is a CI build path, not yet an in-app build/install flow. The build accepts
a public HTTPS .hnmod URL, and the bundle's Horizon revision must be an
ancestor of the selected Android fork revision. Builds for unrelated or newer
Horizon pins are rejected rather than silently applying patches to the wrong
source. The produced APK still needs physical Galaxy A54 testing.

## What a native package contains

The upstream Horizon format defines `.hnmod` as a ZIP archive containing
`horizon-native.json` and `mixins/<id>/`. The bundle contains
`horizon-mixin.toml`, Rust source (`.rs`), TOML and permitted data/readme/license
files. The manifest pins the exact Horizon and horizon-mixins commits and may
declare a native hook API version. It is not a package of ready-to-load Android
shared libraries. The upstream reader rejects arbitrary native entries.

Native mods are **not sandboxed**. They are source transformations applied by
horizon-mixins before compiling a separate Horizon game build. Treat every
package as executable code with the app user's privileges.

## Two Android delivery paths

### 1. Build source bundles for Android

1. Parse and validate the ZIP and `horizon-native.json` using the same rules and
   limits as upstream. Reject duplicate paths, traversal, symlinks, unknown
   manifest fields, unsupported schema versions and invalid pins.
2. Show the package identity, version, requested compatibility and a prominent
   untrusted-code warning. Require explicit per-package consent; never build or
   enable a package automatically.
3. Run the manual Build Android ARM64 client with a native mod workflow from
   the Android fork's Actions tab. Supply a public HTTPS .hnmod URL and select
   yes only when the source is trusted. The job uses the pinned NDK and Rust
   toolchain, applies horizon-mixins at the exact revision and compiles the
   Android client.
4. Download the horizon-android-hnmod-arm64 artifact from the completed run.
   It is a separate development app; it does not update or overwrite the normal
   Android installation. The app does not yet verify build provenance or install
   the artifact itself.

The CI builder currently handles one source bundle per build. It reconstructs
this Android fork on the exact pinned Horizon commit and refuses a pin that is
not an ancestor of the selected fork revision. The full desktop launcher's
multi-mod dependency resolution, isolation/retry behaviour and post-build
steps are not yet ported; bundles relying on those advanced features may fail
rather than being treated as compatible.

### 2. Prebuilt ARM64 artifacts

The current upstream `.hnmod` schema does not define an embedded ARM64
executable or shared-library entry. Do **not** accept a binary merely because
the archive contains one, and do not rename an arbitrary binary to `.hnmod`.
If a separately versioned Android artifact format is introduced, it must bind
the binary to the source package hash, Horizon revision, mixins revision,
Android ABI, NDK/API level and signing identity. Verify all of these before
loading. A prebuilt artifact must still pass the same explicit trust consent.

## Galaxy A54 validation and performance

The target Android ABI is `arm64-v8a`. Device model alone is not proof that a
native build works. Validate on a physical Galaxy A54, not only an emulator:

- clean install, upgrade, rollback and app-data preservation;
- package validation, malformed ZIP rejection and consent persistence;
- successful build, incompatible pin, missing hook, compiler failure and
  interrupted CI download;
- memory peak, storage peak, cold/warm build time and crash recovery;
- Vulkan and GLES paths, frame pacing and thermal throttling during a
  repeatable gameplay workload.

Do not change renderer defaults or claim performance gains without before/after
measurements on the physical device.

## Current implementation boundary

- Sandboxed `.hmod`: supported by the existing Wasmtime runtime on 64-bit builds.
- Source `.hnmod`: import and verified registry download are implemented; a manual CI workflow compiles one bundle into a separate ARM64 development APK. In-app compilation, installation and provenance verification are not implemented.
- Prebuilt ARM64 code inside `.hnmod`: not part of the current upstream package
  schema and must be rejected until a separately specified artifact format exists.
- Fabric, Forge and NeoForge JARs: not executable by Horizon Android.

## Completion criteria

Native support is complete only when the app verifies build provenance, provides in-app consent and installation/rollback, handles multi-mod dependency and post-build semantics, and a physical Galaxy A54 completes the end-to-end tests above.
