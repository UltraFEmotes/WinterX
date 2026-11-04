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

The 2026-11-05 development workspace passed 82 Python tests. These cover package validation, staged revisions/rollback, running-engine gates, artwork, bridge behaviour and portable locking/private-folder transports. Windows APIs and ADB use simulated/mocked tests on the current macOS host, not live platform verification. UI/bootstrap checks use JavaScript mocks, not Spring's native runtime. Some regression fixtures need locally built apps or historical build artifacts; missing gitignored fixtures in a fresh checkout are not live runtime failures.

To check a newly built APK, first convert it with Mac.APK's DEX converter **without launching Spring**, then run against the resulting JAR:

```sh
python3 patches/tests/check_coloredbar.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_tweak_settings.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_tweak_lifecycle.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_engine_hooks.py path/to/converted-engine.jar
python3 patches/tests/run_hook_check.py path/to/converted-engine.jar
```

`--packaged` loads the helpers actually present in that engine, not recompiled replacement helpers. ColoredBar checks use Mac.APK's actual Bitmap/Canvas and draw a real Settings header. Lifecycle checks use a QuickJS JNI spy: they verify worker affinity, limit requests, cleanup and isolation logic, **not native deadline enforcement**. None starts or installs a launcher.

## Confirmed vs outstanding

- User-confirmed in alpha4: basic ColoredBar behaviour and independently packaged code. Logs confirm native QuickJS startup, an alert Promise callback and native Settings toggle callbacks.
- Alpha6 isolated packaged checks: Settings lazy loaders/header drawing, preferences, permanent Ruby exclusion and independent red navigation/bottom bars; Settings routing, controller/renderer verification and lifecycle logic. App Store asset selection and dock-app discovery have isolated coverage.
- Still needs a live trial: Ruby 1.8's red bars/Discord button, Settings/App Store/Phone fixes, exclusion refresh, transitions, concurrent alerts, infinite-loop interruption, heap/stack limits, multi-tweak failure isolation, install/update/uninstall cleanup and Safe Mode recovery. Do not call the runtime a hardened sandbox.

## Safe live testing

Never run stock and patched Spring simultaneously. Do not replace an engine APK in use or perform in-place respring testing: it has caused Java heap exhaustion and `eventfd` errors on Mac.APK. Build to a new output, keep the old APK and backup, fully quit Spring, configure the new build and deliberately reopen it using the installation guide. New/updated v2 code needs a full launcher reopen; its installer does not restart Spring.

Before and after any queued `.sapp` or engine change, clearly tell the person what changed. A watcher in compatible patched engines can import `.sapp` updates live, but that does not reload an engine APK. Reopen the updated app itself; when in doubt, fully quit and reopen the launcher. Native Animaper/ColoredBar preference changes do not need respring on compatible engines.

Check each tweak's actual page in **Spring Settings**, not only its status in Ruby. Test toggles/back navigation, failed/disabled code, uninstall with preserved preferences, and a fresh launch. Recheck protected layout digests after a live trial; do not delete layouts to make a test pass. FreeMe and DockIn remain unfinished; the old free-icon test is not FreeMe.

## Recovery

If Spring cannot start, fully close it, then run `python3 tools/prepare_safe_mode.py` with the documented environment. Reopen original Spring, start the bridge and jailbreak into Safe Mode. Preserve `.ruby-state/backups/` and old APKs. Safe Mode should skip executable code and optional tweak effects; Ruby's own red appearance remains independent. Recovery needs further live verification.

Do not delete Ruby, WinterX, saved icon positions or page files to reset the jailbreak. Removing a tweak preserves its preferences/state/data. Never restore a backup over a running launcher.
