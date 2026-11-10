# Android native mod support plan

Status: `.hnmod` import and validation are implemented on the Android branch. The
app can import from the Android document picker, a direct HTTPS URL or the Horizon
registry; registry downloads are checked against the index hash and signature.
Imported bundles are stored in `horizon-mods/` as source. They are **not compiled
or executed** by Android yet. The existing runtime remains the sandboxed Wasmtime
`.hmod` path on 64-bit builds.

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
3. Send the validated source bundle and exact upstream revision pins to a
   reproducible CI build job. The job must use the Android NDK, Rust
   `aarch64-linux-android` target and the project's pinned toolchain. It must
   apply horizon-mixins to the exact Horizon source revision before building.
4. Verify the resulting artifact's provenance, ABI, package ID, source hash,
   toolchain/revision pins and signature before the Android app accepts it.
5. Install it as a distinct game build, preserving the original game and a
   rollback path. A failed build must leave the current install playable.

The source build is not a simple Cargo cross-compile: the upstream launcher
resolves revisions, applies source mixins, builds a separate game and tracks
which mods were left out. Those semantics must be ported or deliberately
reimplemented before source builds can be called compatible.

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
- Source `.hnmod`: import, upstream-format validation and verified registry download are implemented; Android compilation and execution are not.
- Prebuilt ARM64 code inside `.hnmod`: not part of the current upstream package
  schema and must be rejected until a separately specified artifact format exists.
- Fabric, Forge and NeoForge JARs: not executable by Horizon Android.

## Completion criteria

Native execution support is complete only when the Android build pipeline produces a verified ARM64 game artifact from a real source bundle,
the app enforces trust consent and rollback, and a physical Galaxy A54 completes the end-to-end tests above.
