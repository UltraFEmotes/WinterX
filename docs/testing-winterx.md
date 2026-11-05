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

The current 2026-11-05 workspace passed **154 Python tests**. Coverage includes package validation, revisions/rollback, actual-engine gates, renderer/Barrel/SSH-action/prompt capabilities and all five pinned local-test engines. The **20 preparation safeguards** preserve saved effects/layouts/keys/preferences/packs/code state, accept only the configured platform-root alias, reject child links/root retargeting and refuse restoring old data after external edits. Windows/ADB/SSH transport and UI/bootstrap tests use mocks; they are not live platform verification.

`python3 tools/check_source_tests.py` passes **146 fixture-independent tests**. It omits the two SDK/APK/generated-theme modules; those local inputs are intentionally not distributed. All four JavaScript smoke runners pass, including Ruby's original eight effects, capability-gated Barrel and explicit selection preservation. Tweak/file requests load the SDK lazily; only `.sapp` operations need it.

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
python3 patches/tests/check_ssh_actions.py path/to/converted-engine.jar --packaged
python3 patches/tests/check_ssh_native_archive.py path/to/converted-engine.jar
python3 patches/tests/check_animaper.py path/to/converted-engine.jar
python3 patches/tests/check_renderer_transitions.py path/to/converted-engine.jar
python3 patches/tests/check_appearance.py path/to/engine.apk path/to/converted-engine.jar
python3 patches/ssh/check.py path/to/converted-engine.jar --javac /opt/homebrew/opt/openjdk/bin/javac
```

`--packaged` loads the helpers actually present in that engine, not recompiled replacement helpers. ColoredBar checks use Mac.APK's actual Bitmap/Canvas and draw a real Settings header. Lifecycle checks use a QuickJS JNI spy: they verify worker affinity, limit requests, cleanup and isolation logic, **not native deadline enforcement**. Standalone `check.py`, trusted-file and inbox checks compile current sources with isolated fixtures; they are not packaged-engine evidence. None starts or installs a launcher.

Message+ exercises real packaged native button/header and Settings models/pointer entries with an alert/application spy, not live UI or delivery. SSH service tests use a no-socket engine spy to check serialized Start/Stop before state changes, pre-worker/busy cancellation, resource ownership, failed Start and Safe Mode/removal/key-change stopping. They test actual monitor contention rather than reflection modifiers, since D8 lowers synchronized methods into explicit monitor instructions. The original unsynchronized batch fails the stronger test as a negative control. The separate `patches/ssh/check.py` takes the **new info-capable library or converted engine** plus `--javac`/`--java` paths; it checks actual configuration/authentication without starting a listener. It drives real built-in neofetch command dispatch/lifecycle using in-memory streams and fixed Android metadata objects, with no shell or SSH connection. It verifies branding/aliases/help/plain output, reported-vs-host labels, bounded/control-safe values, privacy and exits/cancellation/failures. These are not real Android metadata or connection tests.

The strengthened Settings/storage checks exercise direct and aliased platform files roots while refusing child links. The reviewed engine fails the alias cases despite valid markers. FreeMe/home API fixtures now use native four/five-row grids with 16/20 cells, not row count as capacity. The final UI-fix2 candidate passes these regressions. The real-pack runner imports/selects only in disposable fixtures and checks native picker/checksums/PNG decoding/renderer pixels and preservation; it never installs into the user's Spring. `--source-snowy` explicitly overlays current sources and is not packaged-engine evidence.

The combined renderer/Barrel/actions candidate passes **64/64 packaged renderer cases** and **12/12 Animaper checks**, including native cache production/consumption, queued/retained layers, normal scrolling, sparse four/six-column two-page cylinder pixel references, Settings and Canvas/context exception cleanup. Old engines reach the expected rendering regressions as negative controls. `check_patch_matrix.py path/to/decoded-stock --artifacts path/to/new-report` verifies **64/64 optional flag combinations** and four atomic no-file-write anchor failures. Four assembled flag configurations also passed capability/receipt checks in direct and aliased roots.

SSH app-command tests exercise exact parsing/confirmation/checksums, bounded queues/output/deadlines, cancellation and at-most-once exits with in-memory backends. `check_ssh_actions.py --packaged` uses the actual helper but non-acting native spies: it verifies main-thread actions, foreground-close completion, genuine cleanup dispatch, native folder shapes, scoped new-app install, existing data protection and session/key/root guards. The native-archive runner uses real packaged `J1.P` file-import code plus a narrow icon-adapter spy against disposable roots; it creates no launcher and executes no JS. None of these tests installs, opens or closes a live app.

## Confirmed vs outstanding

- User-confirmed in alpha4: basic ColoredBar behaviour and independently packaged code. Logs confirm native QuickJS startup, an alert Promise callback and native Settings toggle callbacks.
- Alpha6 isolated packaged checks: Settings lazy loaders/header drawing, preferences, permanent Ruby exclusion and independent red navigation/bottom bars; Settings routing, controller/renderer verification and lifecycle logic. App Store asset selection and dock-app discovery have isolated coverage.
- The selected test is `WinterXSpring-0.8.1-ssh-terminal-snowflake-dev.apk`, checksum `adbc9df090bed714afb4121df8b9927cd3478ae810e783fe1964d75115f1f664`, with the original five tweaks, renderer/Barrel/actions and interactive blue-snowflake SSH. User-confirmed stopped-session preparation at 21:00 local used backup `20261105-210035-879469-before-local-combined`, preserving all **485 current persisted entries** with zero changed paths. It did not launch Spring. Earlier plans, engines, backups/defaults and package pins remain preserved.
- Historical alpha8-local checks covered native Settings/artwork, lifecycle spies, appearance, sparse cells/rollback/cancellation/app-list changes and DockIn caches/size interpolation/launch rectangles/renderer exceptions. They did not exercise the newly reproduced alias and realistic grid-capacity defects. Complete native pointer/folder workflows, rendered motion and visible Settings refresh remain live-unverified; neither layout tweak is a working catalogue entry.
- Historical UI-fix2 passed 17 isolated runners; Neofetch-only passed 18. The 7,008-class renderer/actions baseline passed 27 verification jobs. The **7,017-class terminal/snowflake update** passed seven focused packaged jobs, with unchanged native/resource and non-SSH class bytes verified. Actual terminal/rendering/import/Settings/photo delivery and Android behaviour still need user trials. See [development status](development-status.md).
- Still needs a live trial: Ruby 1.8's red bars/Discord button, Settings/App Store/Phone fixes, exclusion refresh, transitions, concurrent alerts, infinite-loop interruption, heap/stack limits, multi-tweak failure isolation, install/update/uninstall cleanup and Safe Mode recovery. Do not call the runtime a hardened sandbox.

## Safe live testing

Never run stock and patched Spring simultaneously. Do not replace an engine APK in use or perform in-place respring testing: it has caused Java heap exhaustion and `eventfd` errors on Mac.APK. Build to a new output, keep the old APK and backup, fully quit Spring, configure the new build and deliberately reopen it using the installation guide. New/updated v2 code needs a full launcher reopen; its installer does not restart Spring.

Before and after any queued `.sapp` or engine change, clearly tell the person what changed. A watcher in compatible patched engines can import `.sapp` updates live, but that does not reload an engine APK. Reopen the updated app itself; when in doubt, fully quit and reopen the launcher. Native Animaper/ColoredBar preference changes do not need respring on compatible engines.

The local launcher accepts five explicit pins: reviewed, UI-fix2, Neofetch, renderer-actions and SSH-terminal/snowflake. It requires a fresh receipt, the plan's checksum, the sole matching process and all five package receipts before recording activation. `--ssh-terminal`, `--render-actions`, `--ui-fix` and `--neofetch` are mutually exclusive; the no-flag default is unchanged. Preparation requires Spring stopped, takes a fresh backup and verifies every persisted entry. It never launches Spring, performs SSH app actions, configures keys/listeners, changes effects or stages packs. The platform-root alias is resolved once and rechecked before writes; child links stay refused. Pinned binaries are not distributed. Launch is user-controlled; old receipts are not proof of a running engine.

Check each tweak's actual page in **Spring Settings**, not only its status in Ruby. Test toggles/back navigation, failed/disabled code, uninstall with preserved preferences, and a fresh launch. Recheck protected layout digests after a live trial; do not delete layouts to make a test pass. FreeMe and DockIn remain unfinished; the old free-icon test is not FreeMe.

## Recovery

If Spring cannot start, fully close it, then run `python3 tools/prepare_safe_mode.py` with the documented environment. Reopen original Spring, start the bridge and jailbreak into Safe Mode. Preserve `.ruby-state/backups/` and old APKs. Safe Mode should skip executable code and optional tweak effects; Ruby's own red appearance remains independent. Recovery needs further live verification.

Do not delete Ruby, WinterX, saved icon positions or page files to reset the jailbreak. Removing a tweak preserves its preferences/state/data. Never restore a backup over a running launcher.
