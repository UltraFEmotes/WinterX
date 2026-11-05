# Development status — 2026-11-05

## Selected combined local test

- Selected engine: `builds/WinterXSpring-0.8.1-tweaks-batch2-reviewed.apk`, SHA-256 `71fc52605f2d32294597dd9496956e72b3a02d485b4b233703087d6a75ae980d` (**6,979 converted classes**).
- After the user requested the upgrade and Spring was verified closed, preparation backed up current data to `.ruby-state/backups/20261105-141024-762093-before-local-combined`. **SnowyHome, DockIn, FreeMe, MessagePlus and SSH** are installed/enabled. Inventory differences were limited to the two new MessagePlus/SSH markers and Ruby's package registry; saved pages, positions, preferences and executable-tweak data were preserved. Preparation did **not** launch Spring.
- The latest read-only check, 2026-11-05 at 14:39 local time, verified one running reviewed-engine process against its receipt, checksum and overlay, with all five regular markers and no Safe Mode. Its cold launch loaded all 6,979 classes, and deployed Settings/Message+/SSH bytecode matches the reviewed engine. This is timestamped evidence, not a permanent running-engine guarantee or proof that the UI works.
- Earlier alpha8/experimental2 plans, receipt history, APKs and backups are preserved. The separate default engine remains unchanged. No session was stopped, restarted or hot-patched during the correction work. Never restore old layouts over current data or run stock and patched Spring together.
- Companion 0.6 remains uninstalled/unsubmitted. No modified Spring APK or built bundle is redistributed.

## Missing UI and grid diagnosis — separate correction candidate

The live report of missing SSH/Message+ rows was reproduced in isolated packaged tests: the reviewed engine rejects Mac.APK's legitimate shared-data alias even with valid markers. SnowyHome import/loading and home API storage share the defect. The correction canonicalizes **only the platform-supplied application files root** and retains refusal of links beneath it, including `ruby/`, markers, preferences, keys, inboxes and pack revisions. Direct-root tests alone had missed this regression.

Repeated live `Invalid page capacity` fallbacks exposed a second defect: Spring's grid field stores **rows**, not total cells. FreeMe and the home API now share bounded, overflow-safe **rows × columns** capacity. Realistic four/five-row fixtures exercise 16/20 cells, full pages, moves and invalid dimensions without rewriting user layouts.

Final candidate: `builds/WinterXSpring-0.8.1-tweaks-batch2-ui-fix2.apk`, SHA-256 `3ca1213cf316081d958e2871caa367578595bfe5cb3de4cfd625972921c60169`, **6,979 converted classes**. It preserves the reviewed SSH synchronization and all five original package pins. **It is not selected, installed or launched.** The earlier `ui-fix.apk` lacks the subsequent SnowyHome correction and is not the final candidate.

`python3 tools/prepare_local_test.py --ui-fix` explicitly selects the final pin only with Spring fully closed, after a fresh backup and persisted-data comparison. This command has **not** been run. The launcher continues to accept the existing reviewed plan and verifies/records each plan's actual pin. Neither script stops or restarts the user's session; launch stays under user control through `Start WinterX Local Test.command`.

| Feature | Implemented in source/candidate | Still unverified or unsupported |
| --- | --- | --- |
| [SnowyHome](snowyhome.md) | Icon packs, badges, labels, corners; bounded native private-inbox ZIP import; trusted-root alias fix; no automatic selection/replacement/deletion | Live import, cache, folder/dock/rendering and Settings refresh |
| [Home APIs](tweak-runtime-design.md#experimental-home-api) | Asynchronous, manifest-declared snapshots and revision-checked same-page FreeMe cell moves; corrected capacity/storage; unlisted executable example | Cross-page/dock/folder mutation, custom animation APIs and live native dispatch |
| [SSH](ssh.md) | Optional Apache MINA SSHD engine, key authentication, native explicit Start/Stop, loopback SFTP/Android shell exec as Spring's UID | Android NIO/JCE/runtime compatibility, listener/connection/command trial and signing-compatible deployment |
| [Message+](messageplus.md) | Messages main-list Edit → native Settings; JPEG quality 65/85/95; native Settings rows; gesture cancellation and Safe Mode/removal fallback | Live UI/photo delivery; video sending and reactions are **not implemented** |

MessagePlus/SSH use their original checksum-pinned development bundles in the authorized local test. The executable Home API Example remains uninstalled. None is in a working catalogue. The optional SSH library checksum is `bc30e922a54efb96f1657d7e51002c69e17af4d5fce649caa3a6620d9d7ec094`; install never starts its listener.

## Local iOS 27.2 icon packs

Two packs were built from the user's unchanged sheet: `builds/iOS-27.2-SnowyHome.zip` and `builds/iOS-27.2-Vivid-SnowyHome.zip`. Each maps **17 confirmed Spring IDs** using original 200×200 pixels. TV maps to Videos, News to Newsstand, Games to Game Center, Wallet to Passbook and Music to iPod. FaceTime, Health and Siri are extracted but unmapped and excluded from the ZIPs.

Both packs passed native import/picker/checksum/decode/renderer/pixel and preservation checks in disposable direct/aliased roots. **Neither was staged into Spring's inbox, imported, selected or published.** Supplied artwork and built ZIPs remain local; installation/selection needs separate authorization and a compatible corrected engine.

## Verification boundaries

Current local source passed **134 full-workspace / 126 source-only Python tests** and all four JavaScript smoke runners. The final correction candidate passed **all 17 isolated runners**, including actual packaged Settings/renderer/controller hooks, native FreeMe/DockIn, SnowyHome and real packs, home API guards, Message+ and SSH. Direct/aliased root cases and realistic grid dimensions are now exercised. Standalone grid/trusted-file/inbox runners compile source fixtures; they are not packaged-hook evidence. An intermediate test indentation error was fixed before these successful suite runs.

SSH locking was verified in APK DEX and converted JVM monitor instructions, not inferred from reflection's modifier: D8 lowers `synchronized` to explicit monitors. Behavioral tests confirm both Start and Stop block before changing request state and cancel queued Start before resource configuration. The reviewed engine passes the locking/direct-root checks but fails the newer alias regression; the final correction passes both roots. The original unsynchronized batch also fails the stronger lock test as an intentional negative control.

Message+ uses an alert spy; lifecycle uses a QuickJS JNI spy; SSH service cancellation/resource ownership uses an engine spy with **no sockets or shell**. Separate SSH configuration tests never bind a port. No actual message, server connection, Android deployment or user-data reset was performed. Automated results do not establish native resource limits, a hardened sandbox or end-to-end delivery.

## Remaining work

- User-controlled stopped-session correction, then visible **Settings → WINTERX TWEAKS → SSH/Message+** and Messages main-list **Settings** verification. No automatic quit, launch or pack selection.
- User-controlled combined-test trials: normal-grid gaps/cross-page drops, native dock/folders, launch origins, caches/rendered motion and Settings refresh, without discarding saved data.
- Live Message+ UI and photo delivery; establish and implement the actual Messages video/reaction protocol rather than borrowing unrelated WhatsApp handling.
- Real Android/Windows/Linux trials, private-folder permissions/SELinux, native QuickJS, signing-compatible deployment and runtime recovery. **Never uninstall/reinstall Spring to bypass signing.**
- SSH Android compatibility and an explicitly authorized listener/auth/SFTP/exec trial; broader third-party home/animation APIs.
- Native runtime deadline/heap/stack, concurrent alerts, multi-tweak isolation, update/uninstall and Safe Mode recovery; Ruby's always-red bars/Discord and expanded Settings/App Store/Phone coverage.

Working catalogues remain **only Animaper and ColoredBar**. Implemented source, unlisted drafts, isolated checks and live-confirmed features are distinct readiness levels.
