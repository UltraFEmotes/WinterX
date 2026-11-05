# Development status — 2026-11-05

## Selected combined local test

- Selected engine: `builds/WinterXSpring-0.8.1-ssh-terminal-snowflake-dev.apk`, SHA-256 `adbc9df090bed714afb4121df8b9927cd3478ae810e783fe1964d75115f1f664` (**7,017 converted classes**). It includes the interactive `winterx>` prompt, blue-snowflake Neofetch, guarded `.sapp` commands, normal-scroll/folder fixes and cylindrical Barrel.
- Latest authorized preparation completed **2026-11-05 21:00 local**, after the user confirmed Spring fully closed; it stayed stopped before/after. Fresh backup: `.ruby-state/backups/20261105-210035-879469-before-local-combined`. **All 485 then-current persisted entries** and protected layouts matched the backup with **zero changed paths**. Current effect selection, keys/packs/app data and the original five package pins were preserved. Preparation did **not** launch Spring. The earlier 20:16 renderer-actions preparation/484-entry backup and its subsequently user-launched engine are preserved as history.
- Mac.APK's configured data path had become a root alias (`0.8.1` → `0_8_1`). The first preparation attempt refused it before backup/selection. The corrected preparer resolves only that configured platform root, still rejects child links, and refuses writes/selection if the root changes during preparation. All 20 preparation safeguards pass. The alias itself was not modified.
- Launch remains user-controlled through `Start WinterX Local Test.command`. A selected APK or historical receipt is not proof of a currently running engine. Live rendering, SSH authentication/actions and phone compatibility remain user-trial items.
- Earlier alpha8/experimental2 plans, receipt history, APKs and backups are preserved. The separate default engine remains unchanged. No session was stopped, restarted or hot-patched during the correction work. Never restore old layouts over current data or run stock and patched Spring together.
- Companion 0.6 remains uninstalled/unsubmitted. No modified Spring APK or built bundle is redistributed.

## Blue snowflake and interactive SSH

The user requested a blue snowflake logo and the ability to type built-ins after logging in. The follow-up source adds an in-process `winterx>` prompt with Neofetch/info/app commands, help/exit, bounded line editing, Ctrl-C cancellation and disconnect cleanup. The report now uses a blue ASCII snowflake. One-shot command syntax remains supported.

The selected APK is above; its optional library is `builds/WinterX-SSH-0.1.0-terminal-snowflake-dev.jar`, SHA `3046e8c260dcb220df5a407061585b29a46a9eeaf09831bba79a299ea2b93104`. `--ssh-terminal` is its explicit preparation flag, keeping all four earlier pins/defaults valid. **Seven focused packaged jobs** pass, including interactive stream/keyboard/signal tests, SSH service/action guards, native Settings/boot, all 64 renderer cases and 12 Barrel checks. The native DEX/resources and every non-SSH/non-capability class are byte-identical to the verified renderer-actions build. Live SSH terminal behaviour still needs a user trial. See [interactive terminal instructions](ssh.md#interactive-winterx-terminal).

## Missing UI and grid correction

The live report of missing SSH/Message+ rows was reproduced in isolated packaged tests: the reviewed engine rejects Mac.APK's legitimate shared-data alias even with valid markers. SnowyHome import/loading and home API storage share the defect. The correction canonicalizes **only the platform-supplied application files root** and retains refusal of links beneath it, including `ruby/`, markers, preferences, keys, inboxes and pack revisions. Direct-root tests alone had missed this regression.

Repeated live `Invalid page capacity` fallbacks exposed a second defect: Spring's grid field stores **rows**, not total cells. FreeMe and the home API now share bounded, overflow-safe **rows × columns** capacity. Realistic four/five-row fixtures exercise 16/20 cells, full pages, moves and invalid dimensions without rewriting user layouts.

The historical UI-fix2 correction preserves the reviewed SSH synchronization and all five original package pins. Its checksum remains `3ca1213cf316081d958e2871caa367578595bfe5cb3de4cfd625972921c60169`. Its fixes are retained in the new selected engine; the earlier `ui-fix.apk` lacks the later SnowyHome correction.

`python3 tools/prepare_local_test.py --ui-fix` completed with Spring fully closed, a fresh backup and persisted-data comparison. The launcher continues to accept older reviewed plans and verifies/records each plan's actual pin. Neither script stops or restarts the user's session; launch stays under user control through `Start WinterX Local Test.command`.

## Historical Neofetch-only build

`builds/WinterXSpring-0.8.1-tweaks-batch2-neofetch-dev.apk`, SHA-256 `a1de2419994ccfa009e181af2d1ad7471332613de0af1e30c5d6464ca67e0987`, has **6,983 converted classes**. Its optional library is `builds/WinterX-SSH-0.1.0-neofetch-dev.jar`, SHA-256 `5d4ad90e8deedae3d65088fd79525edc7efed3427c081337560cf1321afcbc1d`. These older pins remain available and unchanged. The new selected engine includes the same information commands plus app actions.

The historical Neofetch-only build used a red WX logo; the selected follow-up uses the requested blue snowflake. Reported Android device/API/display values are separate from host OS and JVM counters; missing values are not invented. The report needs no shell, packages, root, private-file reads or unique identifiers. Help/plain output, control filtering, cancellation and actual command routing pass in-memory checks; live device metadata remains unverified.

`python3 tools/prepare_local_test.py --neofetch` is the explicit **fully stopped-session** upgrade path for that pin, using a fresh backup and the same five package pins. It has **not** been run. It never creates client keys, starts SSH, restores a backup or launches Spring. The existing default/reviewed/UI-fix2 pins remain unchanged.

## Renderer, Barrel and guarded SSH actions

- Normal-mode tile/dock/folder cache production and reuse now respect SnowyHome appearance. Sparse folder backgrounds/notches resolve the whole native page before filtering/indexing. Retained native cache contents, models, folder members and saved cells are preserved.
- [Barrel](animaper.md) uses a cylindrical projection and depth-dependent Canvas foreshortening at actual sparse-grid centres. The original eight effects/order/default remain intact. It is selected only by the user and excluded from dock/edit/open-folder/native launch transforms; Canvas/context cleanup covers exception paths.
- [SSH app commands](ssh.md#guarded-spring-app-commands): `winterx-app list`, `open`, `close`, and explicitly checksum-confirmed **new** `.sapp` installation. Native UI actions dispatch on the main thread; validated single-archive installation uses Spring's installer worker. Existing app/build/data roots are protected. Cancellation and session/key/root/enablement changes revoke queued actions; committed native actions are not rolled back.
- Optional library: `builds/WinterX-SSH-0.1.0-app-actions-dev.jar`, SHA-256 `599dbd800db8a3f042229b56ce3ce9f6183ca9dde738d90889b2253e7abfef01`. The new build flag is `WINTERX_BUILD_SSH_ACTIONS=1`; the explicit preparation flag is `--render-actions`, mutually exclusive with `--ui-fix` and `--neofetch`. Earlier defaults/pins and all five original bundle pins are unchanged.
- Ruby **1.9 source** exposes Barrel only with a native capability receipt and has a new trusted-script pin. Older Ruby 1.4–1.8 pins remain trusted. The app itself was not installed by this engine preparation; use native Spring Settings to select Barrel with existing Ruby versions. Ruby's independent red bars remain unaffected.

| Feature | Implemented in source/candidate | Still unverified or unsupported |
| --- | --- | --- |
| [SnowyHome](snowyhome.md) | Icon packs, badges, labels, corners; bounded native private-inbox ZIP import; trusted-root alias fix; no automatic selection/replacement/deletion | Live import, cache, folder/dock/rendering and Settings refresh |
| [Home APIs](tweak-runtime-design.md#experimental-home-api) | Asynchronous, manifest-declared snapshots and revision-checked same-page FreeMe cell moves; corrected capacity/storage; unlisted executable example | Cross-page/dock/folder mutation, custom animation APIs and live native dispatch |
| [SSH](ssh.md) | Optional Apache MINA SSHD engine, key authentication, explicit native Start/Stop, loopback SFTP/Android exec, Neofetch and guarded `.sapp` app commands | Live listener/auth/SFTP/info/app-action output, Android NIO/JCE/runtime compatibility, Mac.APK general shell exec, automatic status refresh and signing-compatible deployment |
| [Message+](messageplus.md) | Messages main-list Edit → native Settings; JPEG quality 65/85/95; native Settings rows; gesture cancellation and Safe Mode/removal fallback | Live UI/photo delivery; video sending and reactions are **not implemented** |

MessagePlus/SSH use their original checksum-pinned development bundles in the authorized local test. The executable Home API Example remains uninstalled. None is in a working catalogue. The old UI-fix2 library pin remains `bc30e922a54efb96f1657d7e51002c69e17af4d5fce649caa3a6620d9d7ec094`; newer commands require the new engine. Installation and boot never start SSH.

## Local iOS 27.2 icon packs

Two packs were built from the user's unchanged sheet: `builds/iOS-27.2-SnowyHome.zip` and `builds/iOS-27.2-Vivid-SnowyHome.zip`. Each maps **17 confirmed Spring IDs** using original 200×200 pixels. TV maps to Videos, News to Newsstand, Games to Game Center, Wallet to Passbook and Music to iPod. FaceTime, Health and Siri are extracted but unmapped and excluded from the ZIPs.

Both packs passed native import/picker/checksum/decode/renderer/pixel and preservation checks in disposable direct/aliased roots. **Neither was staged into Spring's inbox, imported, selected or published.** Supplied artwork and built ZIPs remain local; installation/selection needs separate authorization and a compatible corrected engine.

## Verification boundaries

Current checks passed **154 full-workspace / 146 source-only Python tests** and four JavaScript smoke runners. The renderer-actions baseline passed **27 verification jobs**, with fixture-only corrections verified in focused follow-ups; the terminal/snowflake update passed seven focused packaged jobs and byte-comparison of unchanged classes/resources. Coverage includes **64/64 packaged renderer cases**, **12/12 Animaper/Barrel checks**, SSH parsing/dispatch/interactive queues/cancellation, non-acting native action spies, real single-archive file import, Settings/layout/tweak/appearance regressions, **64 optional-flag combinations** and **four atomic no-write anchor rejections**. Four assembled flag configurations passed capability checks in direct/aliased roots. The **20 preparation safeguards** cover all five accepted engine pins, existing layouts/keys/preferences/packs, platform aliases and root retargeting. Earlier engines are valid renderer/Barrel negative controls. See the testing guide for packaged-versus-spied boundaries.

SSH locking was verified in APK DEX and converted JVM monitor instructions, not inferred from reflection's modifier: D8 lowers `synchronized` to explicit monitors. Behavioral tests confirm both Start and Stop block before changing request state and cancel queued Start before resource configuration. The reviewed engine passes the locking/direct-root checks but fails the newer alias regression; the final correction passes both roots. The original unsynchronized batch also fails the stronger lock test as an intentional negative control.

Message+ uses an alert spy; lifecycle uses a QuickJS JNI spy; SSH service/action tests use non-acting boundary spies with **no sockets or shell**. The native archive test imports only disposable fixture files and never creates a launcher or executes JS. Separate SSH configuration/command tests use in-memory streams and fixed Android metadata, without binding a port. No live app was installed/opened/closed during action tests. Automated results do not establish native resource limits, live device metadata, authenticated end-to-end actions, a hardened sandbox or message delivery.

## Remaining work

- User-controlled launch/trial of the prepared renderer/Barrel/actions engine, visible native Settings and explicit SSH Start/fingerprint verification using existing keys. Never launch a second session or automatically quit/restart, configure keys, or select a pack.
- User-controlled combined-test trials: normal-grid gaps/cross-page drops, native dock/folders, launch origins, caches/rendered motion and Settings refresh, without discarding saved data.
- Live Message+ UI and photo delivery; establish and implement the actual Messages video/reaction protocol rather than borrowing unrelated WhatsApp handling.
- Real Android/Windows/Linux trials, private-folder permissions/SELinux, native QuickJS, signing-compatible deployment and runtime recovery. **Never uninstall/reinstall Spring to bypass signing.**
- Rooted/rootless architecture remains unfinished; rootless must include a limited no-Shizuku baseline. No device/root/network setup or universal compatibility claim follows from these local checks.
- SSH Android compatibility and an explicitly authorized listener/auth/SFTP/exec trial; broader third-party home/animation APIs.
- Native runtime deadline/heap/stack, concurrent alerts, multi-tweak isolation, update/uninstall and Safe Mode recovery; Ruby's always-red bars/Discord and expanded Settings/App Store/Phone coverage.

Working catalogues remain **only Animaper and ColoredBar**. Implemented source, unlisted drafts, isolated checks and live-confirmed features are distinct readiness levels.
