# Third-party tweak runtime: design notes

Status: **experimental source implementation; basic live execution confirmed on Mac.APK**. Version 1 packages select built-in hooks; version 2 contains independently authored JavaScript. On 2026-11-05, the user confirmed the code example works in alpha4. Logs confirm native startup, a completed alert-button callback and Settings preference callbacks. Interrupt deadlines, resource limits, failure isolation and recovery still need live validation. Publishing source does not imply those outstanding checks passed.

## Goal

The actual custom-code implementation is source, not only a proposed format: `patches/icon_positions/src/winterx/tweaks/TweakHost.java`, `TweakSettings.java` and `HomeApi.java`, the QuickJS factory/bootstrap patches, `tools/springys.py`, `springys_registry.py`, `ruby_packages.py`, `ruby_bridge.py`, and the independent `examples/code-tweak/` and `examples/home-tweak/`. The selected combined test includes the earlier runtime, not the new home API. Separate batch2 adds home capabilities and passed packaged lifecycle/Settings/home-model spies without selection or launch. The portable Android inventory bridge refuses executable-tweak installation until running-engine/reconciliation/deployment can be completed.

Allow a tweak author to package code that adds behavior to Spring, such as a Settings page or a home-screen page animation, without requiring every user to rebuild WinterX. Ruby should install, update and remove the package. Safe Mode must disable the code before it runs, so a broken tweak does not prevent recovery.

## Implemented first slice

- Spring 0.8.1's existing QuickJS is used with a separate context and worker for each tweak. A build-time factory limits each context to 32 MB JS heap and 512 KB JS stack. The development engine accepts at most eight installed executable tweaks. Each evaluation, event and promise-job turn requests a 1,000 ms native deadline. These limits must still be verified against actual JNI.
- Java exposes calls on `__host`; Spring invokes methods on `__spring`. `TweakHost.java` provides the versioned `WinterX` bootstrap and keeps all context operations, including close, on the same worker. Exceptions disable that tweak for the session and write `last-error.txt`; other contexts remain independent.
- Startup happens after unlock. Safe Mode skips code loading. A periodic worker check closes contexts after disable, uninstall, Safe Mode entry or a revision change. A full launcher reopen is required to load newly installed/updated code. No automatic respring is performed by the v2 installer.
- `TweakSettings.java` renders manifest-defined pages using Spring's native `T6`, `W6` and `V6` factories. Root entries, nested pages, buttons and persistent toggle preferences are supported. The installed manifest's checksum is checked before it is used.
- The bridge enables code installation only if the **running**, checksum-verified engine contains the runtime hooks and bounded-context factory. Finding a newer APK on disk is not enough.
- The registry stages immutable, package-hash-addressed revisions. Failed/interrupted transactions restore the old **code and manifest**, not only metadata. Installation/removal preserves `state.json` and the tweak's `data/` files. Browsing/catalogue/CLI metadata contain no raw code bytes.
- Android root/emulators and Windows/Linux host adapters remain unsupported. Do not infer Android support from a Mac.APK build.

## Draft JavaScript API (`WinterX.version === 1`)

- `WinterX.on("settingsTap", function (page, row) { ... })`: receive declared button/toggle taps. Page links navigate natively instead of executing a callback. An uncaught callback exception fails that tweak's context.
- `WinterX.log(...values)`: log under that tweak's identifier.
- `WinterX.alert({title, message, buttons})`: request Spring's iOS-style alert; returns a Promise for the selected zero-based button index (`-1` if unavailable). Maximum eight pending alerts per tweak. The example's basic alert/callback flow is live-confirmed; unavailable-UI and concurrent-alert behavior still need checks.
- `WinterX.state.get()` / `.set(object)`: read/replace the tweak's JSON state. `.read(key)` / `.write(key, value)` are convenience calls. The reserved `settings` object holds native toggle values under `page/row` keys as `"on"`/`"off"`.
- `WinterX.data.read(name)` / `.write(name, text)`: scoped UTF-8 files. Only simple filenames are accepted; paths, traversal and symlinks are refused. Each file and the state file are limited to 256 KB; data allows at most 64 files and 8 MB in total.

There is **no** arbitrary Java/reflection, shell execution, networking, unrestricted home mutation or custom animation API. The newer home API below is narrowly scoped, not a general hooking system. SSH is a separately compiled, explicitly started service, not a shell API for JavaScript tweaks. Built-in tweaks such as Animaper and ColoredBar continue using their compiled adapters.

## Experimental home API

New engines with ABI **`winterx-home-grid-v1`** expose `WinterX.home.snapshot()` and `WinterX.home.move(request)` as Promises. V2 manifests must explicitly declare `"capabilities": ["home.read", "home.grid"]` (or only `home.read` for read-only code). Unknown, duplicate or unsupported capabilities are refused; the installer requires the matching capability in the verified **running** engine. The selected experimental2 does not provide it.

- `snapshot()` requires `home.read`. Returns `abi`, `columns`, per-page `capacity`, `pages` (arrays of `{id, slot}`), `dock` (IDs), `gridEnabled` and a `revision` hash. Home editing and Safe Mode refuse access. Snapshots are bounded to 100 additional pages/500 home icons; they are not a folder-content API.
- `move({id, page, slot, revision})` requires `home.grid` and enabled FreeMe. Page/slot are zero-based integers. It moves an existing non-folder icon **within its current page** to an empty normal grid cell, rejects stale revisions/collisions, and saves only FreeMe's sparse cells. Native page JSON, app membership, dock and folders are preserved.
- Requests run on Spring's UI thread, then return to the package worker. At most eight are pending per package. Failed/not-ready/disabled/updated packages, unavailable UI dispatch, changed revisions, editing or Safe Mode fail closed.

```js
WinterX.home.snapshot().then(function (home) {
  WinterX.log(home.pages.length, home.gridEnabled, home.revision);
});
```

The unlisted [`examples/home-tweak`](../examples/home-tweak/) shows a snapshot and asks for explicit confirmation before moving a first-page icon to a gap. Build/inspect it with `tools/springys_tool.py`; it is not bundled into working catalogues. Current packaged model checks and JavaScript mocks do not establish a live native home callback or hardened runtime isolation. Cross-page/dock/folder mutations and custom animation/home hooks remain unsupported.

## Installation layout

```text
files/winterx-tweaks/<id>/
  manifest.json       # normalized v2 manifest, including Settings pages
  manifest.sha256     # manifest integrity record
  code/main.js        # package's unmodified UTF-8 script
  sha256              # plain text script digest, not JSON
  enabled             # installer-controlled activation marker
  state.json          # preserved user/tweak state
  data/               # preserved scoped files
  last-error.txt      # latest startup/turn failure, if any
```

Checksums detect corruption, not malicious authors. The in-process runtime is not a hardened security boundary: executable package installation means trusting the source and author. Do not use this development engine for untrusted packages.

## Example and checks

`examples/code-tweak` contains actual user-editable `tweak/main.js`, with a Settings button, nested page, toggle, persistent counter, file write and Promise alert handler. It is **not bundled into the built-in release repository**.

```sh
python3 tools/springys_tool.py build examples/code-tweak builds/code-tweak.springys
python3 tools/springys_tool.py inspect builds/code-tweak.springys
python3 -m unittest discover -s tests -q
node tests/tweak_runtime_smoke.js
python3 patches/tests/check_tweak_settings.py <converted-Spring.jar>
python3 patches/tests/check_tweak_lifecycle.py <converted-Spring.jar>
```

The lifecycle test uses a JVM QuickJS spy to verify loading, worker affinity, deadline requests, error isolation, scoped data and revision cleanup. The bootstrap test executes JavaScript in Node. Neither test substitutes for Spring's native QuickJS.

## Before enabling in a release

1. Expand the confirmed basic JNI startup/alert test to concurrent alerts, further Promise jobs, looping-script interruption, heap/stack limits and failure isolation on a running launcher.
2. Exercise both Settings controllers, repeated taps, back navigation, toggle refresh, disabled/failed tweaks and Safe Mode recovery.
3. Verify install/update/remove and full reopen preserve saved icon positions, `ios6_pages.json` and tweak state.
4. Implement/document the requested generic home-screen/animation extension points; do not describe presets as arbitrary third-party hooks.
5. Keep development examples and the three test tweaks out of release catalogues.
