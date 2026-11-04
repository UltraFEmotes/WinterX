# Development status — 2026-11-05

## Selected combined local test

- Selected engine: `builds/WinterXSpring-0.8.1-snowyhome-experimental2.apk`, SHA-256 `49bf7482544ab22bc528c482c25e5133c1ddef94cff4e5192bc8383abd52bc9f` (5,195 converted classes; twelve isolated runners passed).
- After the user confirmed Spring was closed, preparation backed up current data to `.ruby-state/backups/20261105-090438-945182-before-local-combined` and installed/enabled the **SnowyHome, DockIn and FreeMe** drafts together. All eleven preparation safeguards passed. Inventoried persisted changes were limited to those three activation markers and the package registry; saved pages/positions/preferences/executable-tweak data were preserved.
- Preparation did **not** launch Spring. An earlier read-only check verified one running process against the matching receipt, engine checksum and overlay; the latest check found **Spring closed**, with selection/checksum preserved. A retained receipt is historical, not proof of a running engine or visible behaviour. No session was stopped, restarted or modified for batch development.
- The earlier alpha8 plan, receipt history, APKs and backups are preserved. The separate default engine remains unchanged. Never restore old layouts over current data or run stock and patched Spring together.
- Companion 0.6 remains uninstalled/unsubmitted. No modified Spring APK or built bundle is redistributed.

## Separate batch2 development

Latest review build: `builds/WinterXSpring-0.8.1-tweaks-batch2-reviewed.apk`, SHA-256 `71fc52605f2d32294597dd9496956e72b3a02d485b4b233703087d6a75ae980d`, **6,979 converted classes**. It serializes SSH Start/Stop requests so cancellation cannot be lost before worker submission. The original batch2 (`ac27c2697ed81d0f7f27900e331edbcb5a56e35129fb874a50594568c9f8d453`) is preserved as an earlier build, not the reviewed candidate. Both use Animaper, trusted-files, inbox, SnowyHome and Message+ flags plus the optional SSH library. **Neither is selected, installed or launched.** They do not silently upgrade the user's combined test.

| Feature | Implemented in source/batch2 | Still unverified or unsupported |
| --- | --- | --- |
| [SnowyHome](snowyhome.md) | Icon packs, badges, labels, corners; bounded private-inbox ZIP import in native Settings; no automatic selection/replacement/deletion | Live import, cache, folder/dock/rendering and Settings refresh |
| [Home APIs](tweak-runtime-design.md#experimental-home-api) | Asynchronous, manifest-declared snapshots and revision-checked same-page FreeMe cell moves; unlisted executable example | Cross-page/dock/folder mutation, custom animation APIs and live native dispatch |
| [SSH](ssh.md) | Optional Apache MINA SSHD engine, key authentication, native explicit Start/Stop, loopback SFTP/Android shell exec as Spring's UID | Android NIO/JCE/runtime compatibility, listener/connection/command trial and signing-compatible deployment |
| [Message+](messageplus.md) | Messages main-list Edit → native Settings; JPEG quality 65/85/95; native Settings rows; gesture cancellation and Safe Mode/removal fallback | Live UI/photo delivery; video sending and reactions are **not implemented** |

Unlisted development bundles for Message+, SSH and the Home API Example were built and inspected locally. None was installed or added to a working catalogue. The optional SSH library checksum is `bc30e922a54efb96f1657d7e51002c69e17af4d5fce649caa3a6620d9d7ec094`.

## Verification boundaries

Current local source passed **132 full-workspace / 124 source-only Python tests** and all four JavaScript smoke runners. The reviewed batch passed **all fifteen isolated runners**, covering native Settings/artwork, executable-tweak Settings/lifecycle, renderer/controller hooks, sparse layout/dock persistence and motion, appearance, SnowyHome/import preservation, home API guards, Message+ models/touch entries and optional SSH configuration/authentication/service ownership. Trusted-file/inbox runners are standalone source fixtures, not packaged-hook evidence.

SSH locking was verified in APK DEX and converted JVM monitor instructions, not inferred from reflection's modifier: D8 lowers `synchronized` to explicit monitors. Behavioral tests confirm both Start and Stop block before changing request state and cancel queued Start before resource configuration. Packaged and source-overlay modes pass; the original unsynchronized batch fails this stronger test as an intentional negative control.

Message+ uses an alert spy; lifecycle uses a QuickJS JNI spy; SSH service cancellation/resource ownership uses an engine spy with **no sockets or shell**. Separate SSH configuration tests never bind a port. No actual message, server connection, Android deployment or user-data reset was performed. Automated results do not establish native resource limits, a hardened sandbox or end-to-end delivery.

## Remaining work

- User-controlled combined-test trials: normal-grid gaps/cross-page drops, native dock/folders, launch origins, caches/rendered motion and Settings refresh, without discarding saved data.
- Live Message+ UI and photo delivery; establish and implement the actual Messages video/reaction protocol rather than borrowing unrelated WhatsApp handling.
- Real Android/Windows/Linux trials, private-folder permissions/SELinux, native QuickJS, signing-compatible deployment and runtime recovery. **Never uninstall/reinstall Spring to bypass signing.**
- SSH Android compatibility and an explicitly authorized listener/auth/SFTP/exec trial; broader third-party home/animation APIs.
- Native runtime deadline/heap/stack, concurrent alerts, multi-tweak isolation, update/uninstall and Safe Mode recovery; Ruby's always-red bars/Discord and expanded Settings/App Store/Phone coverage.

Working catalogues remain **only Animaper and ColoredBar**. Implemented source, unlisted drafts, isolated checks and live-confirmed features are distinct readiness levels.
