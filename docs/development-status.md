# Development status — 2026-11-05

## Selected combined local test

- Selected engine: `builds/WinterXSpring-0.8.1-tweaks-batch2-ui-fix2.apk`, SHA-256 `3ca1213cf316081d958e2871caa367578595bfe5cb3de4cfd625972921c60169` (**6,979 converted classes**).
- After the user reported missing rows and Spring was verified closed, `--ui-fix` preparation backed up current data to `.ruby-state/backups/20261105-151024-650025-before-local-combined`. **SnowyHome, DockIn, FreeMe, MessagePlus and SSH** remain installed/enabled with their original five pins. All 440 persisted file/link entries and six protected layout hashes matched the fresh backup, with zero changed persisted paths. Preparation did **not** launch Spring.
- The user subsequently launched the correction. Read-only checks matched its sole running process, current receipt, checksum and overlay; this is not visual confirmation or a permanent running-engine guarantee. The earlier reviewed engine's cold launch had loaded all 6,979 classes with matching deployed Settings/Message+/SSH bytecode, proving the original missing UI was a path-guard defect rather than stale deployment.
- Earlier alpha8/experimental2 plans, receipt history, APKs and backups are preserved. The separate default engine remains unchanged. No session was stopped, restarted or hot-patched during the correction work. Never restore old layouts over current data or run stock and patched Spring together.
- Companion 0.6 remains uninstalled/unsubmitted. No modified Spring APK or built bundle is redistributed.

## Missing UI and grid correction

The live report of missing SSH/Message+ rows was reproduced in isolated packaged tests: the reviewed engine rejects Mac.APK's legitimate shared-data alias even with valid markers. SnowyHome import/loading and home API storage share the defect. The correction canonicalizes **only the platform-supplied application files root** and retains refusal of links beneath it, including `ruby/`, markers, preferences, keys, inboxes and pack revisions. Direct-root tests alone had missed this regression.

Repeated live `Invalid page capacity` fallbacks exposed a second defect: Spring's grid field stores **rows**, not total cells. FreeMe and the home API now share bounded, overflow-safe **rows × columns** capacity. Realistic four/five-row fixtures exercise 16/20 cells, full pages, moves and invalid dimensions without rewriting user layouts.

The selected UI-fix2 correction preserves the reviewed SSH synchronization and all five original package pins. The earlier `ui-fix.apk` lacks the subsequent SnowyHome correction and is not the selected final correction.

`python3 tools/prepare_local_test.py --ui-fix` completed with Spring fully closed, a fresh backup and persisted-data comparison. The launcher continues to accept older reviewed plans and verifies/records each plan's actual pin. Neither script stops or restarts the user's session; launch stays under user control through `Start WinterX Local Test.command`.

## WinterX Neofetch-style info — separate, unselected build

`builds/WinterXSpring-0.8.1-tweaks-batch2-neofetch-dev.apk`, SHA-256 `a1de2419994ccfa009e181af2d1ad7471332613de0af1e30c5d6464ca67e0987`, has **6,983 converted classes**. Its separate optional library is `builds/WinterX-SSH-0.1.0-neofetch-dev.jar`, SHA-256 `5d4ad90e8deedae3d65088fd79525edc7efed3427c081337560cf1321afcbc1d`. It does not replace the running UI-fix2 engine or its library.

The built-in `neofetch` / `winterx-info` SSH exec command renders a red WinterX/WX logo and bounded system information. Reported Android device/API/display values are separate from host OS and JVM counters; missing values are not invented. It needs no shell, package installation, root, private-file reads or unique device identifiers. Authentication/loopback/Start/Stop/Safe Mode guards remain unchanged. Help/plain output, control filtering, error/exit/cancellation handling and actual command-factory routing pass in-memory fixture checks against both the library and converted APK; live connection and real device metadata remain unverified.

`python3 tools/prepare_local_test.py --neofetch` is the explicit **fully stopped-session** upgrade path for that pin, using a fresh backup and the same five package pins. It has **not** been run. It never creates client keys, starts SSH, restores a backup or launches Spring. The existing default/reviewed/UI-fix2 pins remain unchanged.

| Feature | Implemented in source/candidate | Still unverified or unsupported |
| --- | --- | --- |
| [SnowyHome](snowyhome.md) | Icon packs, badges, labels, corners; bounded native private-inbox ZIP import; trusted-root alias fix; no automatic selection/replacement/deletion | Live import, cache, folder/dock/rendering and Settings refresh |
| [Home APIs](tweak-runtime-design.md#experimental-home-api) | Asynchronous, manifest-declared snapshots and revision-checked same-page FreeMe cell moves; corrected capacity/storage; unlisted executable example | Cross-page/dock/folder mutation, custom animation APIs and live native dispatch |
| [SSH](ssh.md) | Optional Apache MINA SSHD engine, key authentication, explicit native Start/Stop, loopback SFTP/Android exec; new in-process branded `neofetch`/`winterx-info` | Live listener/auth/SFTP/info output, Android NIO/JCE/runtime compatibility, Mac.APK general shell exec, automatic status refresh and signing-compatible deployment |
| [Message+](messageplus.md) | Messages main-list Edit → native Settings; JPEG quality 65/85/95; native Settings rows; gesture cancellation and Safe Mode/removal fallback | Live UI/photo delivery; video sending and reactions are **not implemented** |

MessagePlus/SSH use their original checksum-pinned development bundles in the authorized local test. The executable Home API Example remains uninstalled. None is in a working catalogue. The selected UI-fix2 SSH library checksum remains `bc30e922a54efb96f1657d7e51002c69e17af4d5fce649caa3a6620d9d7ec094`; install never starts its listener. The newer info command is not retroactively available in that running engine.

## Local iOS 27.2 icon packs

Two packs were built from the user's unchanged sheet: `builds/iOS-27.2-SnowyHome.zip` and `builds/iOS-27.2-Vivid-SnowyHome.zip`. Each maps **17 confirmed Spring IDs** using original 200×200 pixels. TV maps to Videos, News to Newsstand, Games to Game Center, Wallet to Passbook and Music to iPod. FaceTime, Health and Siri are extracted but unmapped and excluded from the ZIPs.

Both packs passed native import/picker/checksum/decode/renderer/pixel and preservation checks in disposable direct/aliased roots. **Neither was staged into Spring's inbox, imported, selected or published.** Supplied artwork and built ZIPs remain local; installation/selection needs separate authorization and a compatible corrected engine.

## Verification boundaries

Current source/new-build checks passed **136 full-workspace / 128 source-only Python tests**, all four JavaScript smoke runners and **18 isolated check jobs**: the 17 engine/standalone regression jobs plus the separate new SSH library check (**24/24 aggregate jobs**). This includes real built-in command-factory dispatch and info lifecycle against the library and converted APK, actual packaged Settings/renderer/controller hooks, FreeMe/DockIn, SnowyHome/real packs, home API guards, Message+ and SSH. The **15 stopped-session safeguard tests** pass across all three explicit pins; they preserve keys/preferences/packs and refuse selection or automatic backup restoration after an external key edit. Direct/aliased roots and realistic grid dimensions are exercised. Standalone grid/trusted-file/inbox runners compile source fixtures; they are not packaged-hook evidence. The earlier UI-fix2 baseline passed 134/126 Python and 17 isolated jobs; its intermediate indentation issue was fixed before those runs. The launcher fixture now also canonicalizes its temporary root, avoiding macOS `/var` versus `/private/var` path-equality failures.

SSH locking was verified in APK DEX and converted JVM monitor instructions, not inferred from reflection's modifier: D8 lowers `synchronized` to explicit monitors. Behavioral tests confirm both Start and Stop block before changing request state and cancel queued Start before resource configuration. The reviewed engine passes the locking/direct-root checks but fails the newer alias regression; the final correction passes both roots. The original unsynchronized batch also fails the stronger lock test as an intentional negative control.

Message+ uses an alert spy; lifecycle uses a QuickJS JNI spy; SSH service cancellation/resource ownership uses an engine spy with **no sockets or shell**. Separate SSH configuration/info tests never bind a port or start a shell; the built-in command uses in-memory streams and fixed Android metadata objects. No actual message, SSH server connection, Android deployment or user-data reset was performed by development tools. Automated results do not establish native resource limits, real device metadata, a hardened sandbox or end-to-end delivery.

## Remaining work

- User-controlled stopped-session neofetch upgrade when desired, visible **Settings → WINTERX TWEAKS → SSH/Message+** and Messages main-list **Settings** verification. The UI-fix2 correction is already user-launched; do not launch a second session. No automatic quit, launch, key setup or pack selection.
- User-controlled combined-test trials: normal-grid gaps/cross-page drops, native dock/folders, launch origins, caches/rendered motion and Settings refresh, without discarding saved data.
- Live Message+ UI and photo delivery; establish and implement the actual Messages video/reaction protocol rather than borrowing unrelated WhatsApp handling.
- Real Android/Windows/Linux trials, private-folder permissions/SELinux, native QuickJS, signing-compatible deployment and runtime recovery. **Never uninstall/reinstall Spring to bypass signing.**
- SSH Android compatibility and an explicitly authorized listener/auth/SFTP/exec trial; broader third-party home/animation APIs.
- Native runtime deadline/heap/stack, concurrent alerts, multi-tweak isolation, update/uninstall and Safe Mode recovery; Ruby's always-red bars/Discord and expanded Settings/App Store/Phone coverage.

Working catalogues remain **only Animaper and ColoredBar**. Implemented source, unlisted drafts, isolated checks and live-confirmed features are distinct readiness levels.
