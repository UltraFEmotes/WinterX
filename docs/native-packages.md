# Independent native-code tweaks

> Writing your own tweak? Start with **[Making WinterX tweaks](making-tweaks.md)**. This page covers building the core and the official packages.

The core-only WinterX runtime for **Spring 0.8.1** contains generic hooks, package loaders, recovery controls and Ruby's own red bars. Tweak implementations live in independently installed `.springys` archives. **A fresh core installs no tweaks.**

Ruby supports two code formats:

| Format | Code | Runtime |
| --- | --- | --- |
| `winterx.springys/2` | JavaScript, `tweak/main.js` | Separate QuickJS worker per package; [JavaScript API](tweak-runtime-design.md) |
| `winterx.springys/3` | Java source, JVM JAR and Android DEX | `winterx.native/1`; separate classloader per package |

V1 marker packages remain legacy compatibility/history for older engines. They cannot activate a tweak in the core-only runtime.

## Build the core locally

The current build toolchain uses macOS, Mac.APK's converter/framework, Homebrew OpenJDK, `apktool`, and Android build-tools 36.0.0. Obtain Spring 0.8.1 and its SDK separately. The supported original APK SHA-256 is `f07f980fe681a6de9c4ce8735ae1c0bb0f852f447fbdb925d2dec37cf9778e5c`.

```sh
python3 extensions/build.py runtime /path/to/Spring-0.8.1.apk out/core
```

Choose a new output directory. The builder produces:

- `WinterX-core-0.8.1.apk`: local Mac.APK overlay engine.
- `android-runtime/`: generic core/hook DEX and pinned manifest for the rooted loader.
- `winterx-native-api.jar` and `spring-api.jar`: local compilation APIs.
- `native-api.json`: public hook names, typed signatures, fallback values and dispatch policies.
- `core-audit.json`: actual defined classes, checksum and zero-bundled/zero-preinstalled-tweak audit.

The original APK, converted Spring API, SDK and locally modified APK stay local. Use [rooted Android](rooted-android.md) or the Mac.APK workflow below.

## Mac.APK core workflow

With Spring fully closed:

```sh
python3 tools/mac_core.py prepare out/core
python3 tools/mac_core.py launch --bridge
```

Preparation makes a fresh backup, verifies all persisted files, and writes a separate core plan. It preserves existing test plans, package preferences and layouts. Launch checks the sole process, APK hash and a fresh boot receipt. Each full reopen is user-initiated with the launch command. The `--bridge` option serves Ruby's code-package requests while that core is running.

These commands replace the old bundled-test preparation workflow for a new modular installation. The historical local-test commands still identify their older fixtures. Mac.APK preparation/launch safeguards are covered by non-acting tests; the core and external packages are also checked in the real Mac.APK JVM/framework. See [development status](development-status.md) for live-test scope.

## Build Ruby and WinterX

```sh
python3 tools/build_sapp.py Ruby out/Ruby.sapp
python3 tools/build_sapp.py RubyJailbreak out/WinterX.sapp
```

This wrapper runs Spring SDK checks and preserves the exact `main.js` bytes matched by WinterX's trusted-script pins. The SDK's ordinary packer strips comments, so use this wrapper for trusted WinterX apps. Install through Spring's Developer Mode/inbox importer. App updates keep their stable IDs and use increasing build numbers.

## Build a tweak

```sh
python3 extensions/build.py package extensions/packages/animaper out/animaper-0.2.0.springys \
  --sdk out/core/winterx-native-api.jar --spring-api out/core/spring-api.jar
python3 tools/springys_tool.py inspect out/animaper-0.2.0.springys
```

The other official source directories are `coloredbar`, `freeme`, `dockin`, `snowyhome`, `messageplus` and `ssh`. SSH additionally needs its pinned third-party library:

```sh
python3 patches/ssh/build.py out/ssh-library.jar --deps out/ssh-dependencies
python3 extensions/build.py package extensions/packages/ssh out/ssh-0.2.0.springys \
  --sdk out/core/winterx-native-api.jar --spring-api out/core/spring-api.jar \
  --library out/ssh-library.jar
```

The native package builder includes dependency classes and their notices in the SSH package, never in the core APK. It compiles the package's own current source rather than copying an old tweak implementation from that library.

## Package contents

```text
manifest.json
code/classes.dex
code/classes.jar
source/.../*.java
licenses/<dependency>/LICENSE       optional dependency notices
assets/...                          optional referenced artwork
```

V3 requires `type: "tweak"`, `runtime: "java"`, `api: "winterx.native/1"`, an implementation `entry`, `capabilities: ["native.hooks"]`, `exports`, an HTTPS `source` URL, a `license`, and the usual ID/name/version/author/description metadata. The builder writes the `files` SHA-256 map for every code/source/notice payload. Optional `settings_entry` adds the package to the shared **WINTERX TWEAKS** group. Optional `features` identifies capabilities supplied by that package.

`requires` lists native package IDs that must be installed first. Cycles, missing dependencies and removing a required provider are refused. The runtime starts dependencies first and deactivates dependents if a provider fails or is disabled. Dependencies communicate through public hooks; their classloaders are separate.

Limits: 12 MiB compressed, 32 MiB expanded, 128 archive entries, 16 MiB per payload, 128 KiB manifest, 256 KiB per editable source file, 128 distinct exports, 32 features and at most 16 installed native packages. Paths, duplicate/case-colliding entries, DEX checksums/tables/entry classes, JVM entry classes, platform-class shadowing and payload hashes are checked before staging. ZIP directories, links, encryption and undeclared entries are refused. V2 retains its separate JavaScript limits.

## Public author API

Implement `winterx.extension.NativeTweak`:

- `start(TweakContext)`: initialize this package; do not assume UI rendering has begun.
- `call(String point, Object[] arguments)`: implement only the declared exports. Use the generated API's types; `null` normally preserves the stock/next-provider fallback.
- `stop()`: release services and resources after disablement, replacement or failure.

`TweakContext` exposes the package ID, active-state check, Spring files root, package-owned data paths and generic hook dispatch. Native code executes with Spring's permissions; classloader separation and failure handling are **not a security sandbox**. JavaScript packages use their narrower worker API.

For a native Settings page, `settings.page` receives its page key and returns Spring's `E1.T6` model. Rows named `winterx-tw-r/<package-id>/<page>/<row>` route `settings.tap` to that package with the page and row strings. [Hello Native](../examples/native-hello/) is a complete editable example using the same API and Ruby installer as official packages.

Generic engine hooks cover native Settings, rendering, Home/dock layout adapters, assets and media policies. Typed return mismatches and thrown package failures quarantine that provider and preserve fallback behavior. Canvas leases and drag transactions retain their exact starting code owner so removal cannot strand in-flight cleanup.

## Install, update and remove

1. In Ruby, refresh the source or import a `.springys` through **Packages → Local Packages**.
2. Select the actual package and tap **Install**. Keep the bridge and Spring open until Ruby confirms completion.
3. Fully close and reopen Spring through the appropriate WinterX launch command to load the code.
4. Open **Spring Settings → WINTERX TWEAKS**. Animaper belongs in this same section.
5. Remove through Ruby. Saved layouts, selected animation, dock capacity and package `state.json`/`data/` survive removal.

Updates are identified by package ID and archive hash, not semantic-version ordering. Immutable code revisions support recovery; an install/update does not inject code into the running classloader. Safe Mode disables package execution. After leaving it, fully reopen Spring through WinterX to load installed packages again. SSH additionally requires an explicit Settings Start every session.
