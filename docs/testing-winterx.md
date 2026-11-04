# Testing and recovery on Mac.APK

WinterX targets the exact Spring 0.8.1 APK documented in the [installation guide](../README.md). Rooted Android, emulators and Windows/Linux hosts are not supported yet. Back up Spring data before live testing, especially `files/ios6_pages.json` and `files/ruby/icon-positions-v1.json`.

## Automated checks

With the documented dependencies and local input files present:

```sh
python3 -m unittest discover -s tests -q
node tests/ruby_ui_smoke.js
node tests/tweak_runtime_smoke.js
node tests/iexplored_ui_smoke.js
node tests/winterx_status_smoke.js
```

The 2026-11-05 development workspace passed 116 Python tests. These cover package validation, staged revisions/rollback, running-engine/status gates, artwork, bridge behaviour, FreeMe/DockIn package/data protection, verified dock patch anchors, stopped-session preparation and portable locking/transfers/recovery/inventory/repositories/SSH-client safeguards. Windows APIs, ADB and SSH use simulated/mocked tests on the current macOS host, not live platform verification. A POSIX host-shell test also exercises remote script quoting with disposable files. UI/bootstrap checks use JavaScript mocks, not Spring's native runtime. Some regression fixtures need locally built apps, the SDK, generated themes or historical APKs; missing gitignored inputs in a fresh checkout are not live runtime failures.

The source-only public checkout passed **108 fixture-independent tests**, run with `python3 tools/check_source_tests.py`. This explicitly omits the two SDK/APK/generated-theme modules, not silently failing checks. Full discovery without those inputs still reports eight missing-input errors; those fixtures are intentionally not distributed. All four JavaScript smoke runners also passed there. Tweak/file requests now load the Spring SDK lazily; only `.sapp` operations require it.

To check a newly built APK, first convert it with Mac.APK's DEX converter **without launching Spring**, then run against the resulting JAR:

```sh
python3 patches/tests/check_coloredbar.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_tweak_settings.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_tweak_lifecycle.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_engine_hooks.py path/to/converted-engine.jar
python3 patches/tests/run_hook_check.py path/to/converted-engine.jar
python3 patches/tests/check_layout_settings.py path/to/converted-engine.jar --packaged
python3 patches/icon_positions/check_patched.py path/to/converted-engine.jar
```

`--packaged` loads the helpers actually present in that engine, not recompiled replacement helpers. ColoredBar checks use Mac.APK's actual Bitmap/Canvas and draw a real Settings header. Lifecycle checks use a QuickJS JNI spy: they verify worker affinity, limit requests, cleanup and isolation logic, **not native deadline enforcement**. Standalone `check.py`, trusted-file and inbox checks compile current sources with isolated fixtures; they are not packaged-engine evidence. None starts or installs a launcher.

## Confirmed vs outstanding

- User-confirmed in alpha4: basic ColoredBar behaviour and independently packaged code. Logs confirm native QuickJS startup, an alert Promise callback and native Settings toggle callbacks.
- Alpha6 isolated packaged checks: Settings lazy loaders/header drawing, preferences, permanent Ruby exclusion and independent red navigation/bottom bars; Settings routing, controller/renderer verification and lifecycle logic. App Store asset selection and dock-app discovery have isolated coverage.
- The selected local test is now **alpha8-local**, checksum `e1fc328e5cb794f8d8ebbac713e9cfaba6d7db08af14c5c13345c80137b6c6db`. Preparation used fresh stopped-session backup `20261105-030135-006501-before-local-alpha8`; existing protected hashes matched afterward. The old plan, active record, APKs and backups were preserved. Spring, the companion and draft tweaks were not launched/installed during preparation. The separate default engine remains unchanged.
- Alpha8-local passed all eleven isolated check runners against its packaged/converted engine, including native Settings/artwork, runtime-worker lifecycle with a QuickJS spy, appearance, trusted files, inbox monitoring and bootstrap/renderer class verification. Layout checks cover FreeMe sparse cells/rollback/cancellation/app-list changes and DockIn native caches, size interpolation, `H6` app-launch rectangles, both renderer exception paths and settling guards. These are **not live UI or JNI-limit verification**. Complete native pointer/folder workflows, rendered motion and visible Settings refresh remain live-unverified; neither tweak is a working catalogue entry.
- Still needs a live trial: Ruby 1.8's red bars/Discord button, Settings/App Store/Phone fixes, exclusion refresh, transitions, concurrent alerts, infinite-loop interruption, heap/stack limits, multi-tweak failure isolation, install/update/uninstall cleanup and Safe Mode recovery. Do not call the runtime a hardened sandbox.

## Safe live testing

Never run stock and patched Spring simultaneously. Do not replace an engine APK in use or perform in-place respring testing: it has caused Java heap exhaustion and `eventfd` errors on Mac.APK. Build to a new output, keep the old APK and backup, fully quit Spring, configure the new build and deliberately reopen it using the installation guide. New/updated v2 code needs a full launcher reopen; its installer does not restart Spring.

Before and after any queued `.sapp` or engine change, clearly tell the person what changed. A watcher in compatible patched engines can import `.sapp` updates live, but that does not reload an engine APK. Reopen the updated app itself; when in doubt, fully quit and reopen the launcher. Native Animaper/ColoredBar preference changes do not need respring on compatible engines.

The alpha8 local launcher rejects stale plans and requires a fresh startup receipt, checksum and matching sole process before writing `active.json`. `tools/prepare_local_test.py` prepares/backups only; `Start WinterX Local Test.command` is the user-controlled launch. A saved receipt/PID is not proof that the engine is still active. `--source-layout` in the layout check runner is a development overlay, not a packaged-build verification.

Check each tweak's actual page in **Spring Settings**, not only its status in Ruby. Test toggles/back navigation, failed/disabled code, uninstall with preserved preferences, and a fresh launch. Recheck protected layout digests after a live trial; do not delete layouts to make a test pass. FreeMe and DockIn remain unfinished; the old free-icon test is not FreeMe.

## Recovery

If Spring cannot start, fully close it, then run `python3 tools/prepare_safe_mode.py` with the documented environment. Reopen original Spring, start the bridge and jailbreak into Safe Mode. Preserve `.ruby-state/backups/` and old APKs. Safe Mode should skip executable code and optional tweak effects; Ruby's own red appearance remains independent. Recovery needs further live verification.

Do not delete Ruby, WinterX, saved icon positions or page files to reset the jailbreak. Removing a tweak preserves its preferences/state/data. Never restore a backup over a running launcher.
