# Rooted Android / emulator workflow

The rooted WinterX loader preserves the **original installed Spring 0.8.1 APK, signing identity and app UID**. At a fresh Spring start it prepends locally built generic core/hook DEX before Spring classes load. Ruby then installs independent code packages. The loader itself installs no tweaks.

Live development target: **Android 10 / API 29 / ARM64 emulator, root ADB, SELinux Enforcing, macOS host**. The code targets API 26+, but physical devices, other Android versions/ABIs and Windows/Linux hosts are not yet verified. Rootless support is deferred.

## Prerequisites

- Original supported Spring 0.8.1 installed normally; complete Spring's own sign-in/setup and enable Developer Mode.
- Actual root access to that explicit test target (`--access shell` for already-root ADB, or `--access su` for a working root manager).
- Android platform-tools, Python with `frida==17.25.2` and Pillow, and Node/npm for building the loader.
- A locally built [core-only runtime and Ruby/WinterX apps](native-packages.md).
- A matching Frida 17.25.2 server, started explicitly on the target's **127.0.0.1:27042**. Obtain it from the official Frida release for the target architecture. The tools do not root a device or install/start this daemon automatically.

Tested ARM64 server SHA-256: `7bb6219131819c11e5fe53b3e32fae0b8d1ff4c2a9c35c1a549d2703ea0f3b9b`; official compressed asset SHA-256: `08d7b7f02256621c9089cecd6495a5eb43861bf560a7ed86ad376e75d16a1fb6`.

## Stage and launch

Choose your device serial explicitly. These example commands use an already-root emulator:

```sh
export SERIAL=emulator-5554
adb -s "$SERIAL" forward tcp:27048 tcp:27042
npm --prefix tools/android_agent ci
node tools/android_agent/build.mjs out/root-loader.js

python3 tools/android_runtime.py --serial "$SERIAL" --access shell --state out/root-session inspect
```

Fully close Spring before staging. Use the same private host state directory for subsequent launches/recovery:

```sh
python3 tools/android_runtime.py --serial "$SERIAL" --access shell --state out/root-session \
  stage out/core/android-runtime
python3 tools/android_runtime.py --serial "$SERIAL" --access shell --state out/root-session \
  launch out/root-loader.js --bridge --builtin-repo builtin-repo
```

Staging verifies the original APK hash/version/UID, makes a fresh bounded private-data backup and copies only the pinned generic runtime files. Launch refuses an existing Spring process and verifies the app-side DEX hashes, ABI, UID and session acknowledgement. Keep this host command connected for Ruby requests. Later reopens use the same `launch` command after Spring has been fully closed. Late Frida reattachment was unreliable on the tested Android 10 target; retain the initial session instead.

The local repository option makes packages available in Ruby; it does not install them. A fresh core has an empty installed list.

## Install the apps and tweaks

With Developer Mode on, send the locally built `.sapp` apps to Spring's inbox:

```sh
adb -s "$SERIAL" push out/Ruby.sapp /sdcard/Android/data/com.guille.spring/files/sapps-inbox/
adb -s "$SERIAL" push out/WinterX.sapp /sdcard/Android/data/com.guille.spring/files/sapps-inbox/
```

Spring's own importer handles the apps. Ruby 2.0.1 includes the Android refresh-budget correction; use it with a core that trusts build 21. Open Ruby, refresh Sources, choose packages and tap Install. Wait for the completion result before closing Spring. Fully reopen through WinterX to load new code, then open **Settings → WINTERX TWEAKS**.

## Recovery and preservation

The rooted bridge accepts scan, repository, install and remove requests from Ruby. Each write checks the owned runtime and exact expected bytes. Its host journal is bound to the target, app UID, canonical private folder and native-file policy. It stages only package code/manifests/notices/artwork and Ruby registry outputs. It never synchronizes saved layouts, login material, animation/dock preferences, SSH keys, or package state/data from a host mirror.

Keep the private host state directory. On interruption, reconnect through a fresh verified launch with the same state so pending file transactions can recover. External edits that differ from both expected and replacement bytes block recovery instead of being overwritten. Reopen after recovery to load the resulting code revision.

A package fault is recorded in its `last-error.txt`; the provider is quarantined for that session. Ruby's Safe Mode works independently of installed tweaks. After leaving Safe Mode, reopen through WinterX. The installed Spring APK is never replaced or uninstalled by this workflow, and backups are never restored automatically.

For the older read-only/inventory transports, see [portable bridge details](android-bridge.md). Those tools do not by themselves load the rooted runtime.
