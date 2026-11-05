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

The current 2026-11-05 development workspace passed **134 Python tests**. Coverage includes package validation, staged revisions/rollback, running-engine/status gates, FreeMe/DockIn/SnowyHome/Message+ data protection, both explicitly pinned stopped-session local tests, plan-specific startup receipts, icon packs, home capabilities and portable locking/transfers/recovery/inventory/repositories/SSH-client safeguards. Windows APIs, ADB and SSH use simulated/mocked tests on macOS, not live platform verification. A POSIX host-shell test exercises remote script quoting with disposable files. UI/bootstrap checks use JavaScript mocks, not Spring's native runtime. Missing gitignored SDK/APK/theme fixtures in a fresh checkout are not live runtime failures.

`python3 tools/check_source_tests.py` passes **126 fixture-independent tests** with current source. It explicitly omits the two SDK/APK/generated-theme modules. Full discovery without those inputs still reports eight missing-input errors; those fixtures are intentionally not distributed. All four JavaScript smoke runners passed locally. Tweak/file requests load the Spring SDK lazily; only `.sapp` operations require it.

To check a newly built APK, first convert it with Mac.APK's DEX converter **without launching Spring**, then run against the resulting JAR:

```sh
python3 patches/tests/check_coloredbar.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_tweak_settings.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_tweak_lifecycle.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_engine_hooks.py path/to/converted-engine.jar
python3 patches/tests/run_hook_check.py path/to/converted-engine.jar
python3 patches/tests/check_layout_settings.py path/to/converted-engine.jar --packaged
python3 patches/icon_positions/check_patched.py path/to/converted-engine.jar
python3 patches/tests/check_snowyhome.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_iconpacks.py path/to/converted-engine.jar path/to/real-pack.zip
python3 patches/tests/check_home_api.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_messageplus.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_ssh_service.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_appearance.py path/to/engine.apk path/to/converted-engine.jar
```

`--packaged` loads the helpers actually present in that engine, not recompiled replacement helpers. ColoredBar checks use Mac.APK's actual Bitmap/Canvas and draw a real Settings header. Lifecycle checks use a QuickJS JNI spy: they verify worker affinity, limit requests, cleanup and isolation logic, **not native deadline enforcement**. Standalone `check.py`, trusted-file and inbox checks compile current sources with isolated fixtures; they are not packaged-engine evidence. None starts or installs a launcher.

Message+ exercises real packaged native button/header and Settings models/pointer entries with an alert/application spy, not live UI or delivery. SSH service tests use a no-socket engine spy to check serialized Start/Stop before state changes, pre-worker/busy cancellation, resource ownership, failed Start and Safe Mode/removal/key-change stopping. They test actual monitor contention rather than reflection modifiers, since D8 lowers synchronized methods into explicit monitor instructions. The original unsynchronized batch fails the stronger test as a negative control. The separate `patches/ssh/check.py` takes the optional library or converted batch2 JAR plus `--javac`/`--java` paths; it checks actual configuration/authentication without Start or any shell. Do not interpret these as an Android connection test.

The strengthened Settings/storage checks exercise direct and aliased platform files roots while refusing child links. The reviewed engine fails the alias cases despite valid markers. FreeMe/home API fixtures now use native four/five-row grids with 16/20 cells, not row count as capacity. The final UI-fix2 candidate passes these regressions. The real-pack runner imports/selects only in disposable fixtures and checks native picker/checksums/PNG decoding/renderer pixels and preservation; it never installs into the user's Spring. `--source-snowy` explicitly overlays current sources and is not packaged-engine evidence.

## Confirmed vs outstanding

- User-confirmed in alpha4: basic ColoredBar behaviour and independently packaged code. Logs confirm native QuickJS startup, an alert Promise callback and native Settings toggle callbacks.
- Alpha6 isolated packaged checks: Settings lazy loaders/header drawing, preferences, permanent Ruby exclusion and independent red navigation/bottom bars; Settings routing, controller/renderer verification and lifecycle logic. App Store asset selection and dock-app discovery have isolated coverage.
- The selected local test is **SnowyHome + DockIn + FreeMe + MessagePlus + SSH**, engine `WinterXSpring-0.8.1-tweaks-batch2-reviewed.apk`, checksum `71fc52605f2d32294597dd9496956e72b3a02d485b4b233703087d6a75ae980d`. Authorized stopped-session preparation used fresh backup `20261105-141024-762093-before-local-combined`, preserving layouts/preferences/code data and installing only the two additional pinned hooks. No launcher was started by preparation. A later read-only check verified its sole running process, matching receipt and checksum; it was left untouched. Earlier plans, data, engines, backups and the default engine remain unchanged.
- Historical alpha8-local checks covered native Settings/artwork, lifecycle spies, appearance, sparse cells/rollback/cancellation/app-list changes and DockIn caches/size interpolation/launch rectangles/renderer exceptions. They did not exercise the newly reproduced alias and realistic grid-capacity defects. Complete native pointer/folder workflows, rendered motion and visible Settings refresh remain live-unverified; neither layout tweak is a working catalogue entry.
- The separate **UI-fix2 correction candidate** includes [SnowyHome](snowyhome.md) import, [same-page home APIs](tweak-runtime-design.md#experimental-home-api), [optional SSH](ssh.md) and [Message+](messageplus.md), and passed all **17 isolated runners** (6,979 converted classes), including both actual local iOS 27.2 icon packs. It remains unselected/uninstalled/unlaunched while the reviewed test runs. Video/reactions are unsupported; live rendering/import/Settings/photo delivery/Android SSH remain unverified. See [development status](development-status.md) for the final checksum and diagnosis.
- Still needs a live trial: Ruby 1.8's red bars/Discord button, Settings/App Store/Phone fixes, exclusion refresh, transitions, concurrent alerts, infinite-loop interruption, heap/stack limits, multi-tweak failure isolation, install/update/uninstall cleanup and Safe Mode recovery. Do not call the runtime a hardened sandbox.

## Safe live testing

Never run stock and patched Spring simultaneously. Do not replace an engine APK in use or perform in-place respring testing: it has caused Java heap exhaustion and `eventfd` errors on Mac.APK. Build to a new output, keep the old APK and backup, fully quit Spring, configure the new build and deliberately reopen it using the installation guide. New/updated v2 code needs a full launcher reopen; its installer does not restart Spring.

Before and after any queued `.sapp` or engine change, clearly tell the person what changed. A watcher in compatible patched engines can import `.sapp` updates live, but that does not reload an engine APK. Reopen the updated app itself; when in doubt, fully quit and reopen the launcher. Native Animaper/ColoredBar preference changes do not need respring on compatible engines.

The local launcher accepts only the two explicit reviewed/UI-fix2 engine pins and requires a fresh startup receipt, that plan's checksum, the matching sole process and all five installed package receipts before writing `active.json`. `tools/prepare_local_test.py --ui-fix` is the explicit stopped-session correction path; without the flag it retains the reviewed pin. Preparation backs up and activates only the five pinned drafts, verifies persisted-data preservation and never launches Spring. The pinned builds/bundles are not distributed; this preparer is not a generic source-build installer. `Start WinterX Local Test.command` is the user-controlled launch. A saved receipt/PID is not proof that the engine is still active. `--source-layout` is a development overlay, not packaged-build verification. Neither icon pack is staged/selected without separate authorization.

Check each tweak's actual page in **Spring Settings**, not only its status in Ruby. Test toggles/back navigation, failed/disabled code, uninstall with preserved preferences, and a fresh launch. Recheck protected layout digests after a live trial; do not delete layouts to make a test pass. FreeMe and DockIn remain unfinished; the old free-icon test is not FreeMe.

## Recovery

If Spring cannot start, fully close it, then run `python3 tools/prepare_safe_mode.py` with the documented environment. Reopen original Spring, start the bridge and jailbreak into Safe Mode. Preserve `.ruby-state/backups/` and old APKs. Safe Mode should skip executable code and optional tweak effects; Ruby's own red appearance remains independent. Recovery needs further live verification.

Do not delete Ruby, WinterX, saved icon positions or page files to reset the jailbreak. Removing a tweak preserves its preferences/state/data. Never restore a backup over a running launcher.
