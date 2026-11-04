# Development status — 2026-11-05

## Local alpha8

- Selected local test: `builds/WinterXSpring-0.8.1-layout-alpha8-local.apk`.
- SHA-256: `e1fc328e5cb794f8d8ebbac713e9cfaba6d7db08af14c5c13345c80137b6c6db`.
- All eleven isolated runners passed (packaged-engine checks plus standalone storage/trust/inbox checks); the converted build contains 5,188 classes. Python regressions passed 116 private-workspace tests and 108 public source-only tests, plus four JavaScript smoke runners.
- Prepared only after Spring was fully stopped, using fresh backup `.ruby-state/backups/20261105-030135-006501-before-local-alpha8`. Existing page/position hashes matched the backup. The prior plan/receipt, APKs and backups remain available.
- **Not launched during preparation.** Use `Start WinterX Local Test.command` yourself, not the stock launcher. Never run both. The launcher rejects stale plans/receipts and verifies the matching sole process before recording success. The separate default engine remains unchanged.
- Companion 0.6 and unlisted layout drafts were not installed or submitted. No modified Spring APK is published in the source repository.

## More than alpha8

The actual executable `.springys/2` implementation, authoring example and API/format docs are published source. Separate QuickJS workers execute package-authored code with native Settings, scoped storage and alerts. Basic execution/callbacks were confirmed by the user on alpha4; alpha8 packaged spies do not establish native resource-limit enforcement, complete isolation or recovery. Generic third-party home-icon/animation APIs remain unfinished.

FreeMe/DockIn gained native cache-preserving motion/launch hooks, exception-safe Canvas restoration, cancellation/app-list-change safeguards, live Settings refresh routing and unlisted package gates. Neither is promoted into the working catalogue; complete live pointer/folder/rendered-motion trials remain required.

Portable work includes bounded ADB/directory/SSH-client transports, host locks, conflict-preserving recovery journals and a bounded Ruby inventory/repository processor. Android tweak install/remove requests are refused until running-engine and runtime reconciliation/deployment can be validated. No on-device SSH daemon, network connection, APK signing bypass or service installation was performed.

## SnowyHome source and separate experiment

[SnowyHome](snowyhome.md) now implements verified local icon-pack authoring/loading, same-size private icon copies, badge tinting, hidden labels and corner masks, with actual native Settings. It has an unlisted capability-gated package draft; simulated install/removal preserves preferences/packs/layouts and never restarts Spring. The separate `builds/WinterXSpring-0.8.1-snowyhome-experimental2.apk` (SHA-256 `49bf7482544ab22bc528c482c25e5133c1ddef94cff4e5192bc8383abd52bc9f`, 5,195 converted classes) passed all twelve isolated runners (packaged software-bitmap/native-controller/icon-resolver/JVM checks plus standalone fixtures). Retained badge-artwork views restore stock in Safe Mode. **Not selected, installed or launched. Alpha8 remains unchanged and incompatible with this tweak.** Live-status/Safe Mode routing recognizes the verified experiment without changing the default. Pack-import UI and complete live rendering/cache/folder/Safe Mode trials remain outstanding.

Current source passed **125 full-workspace / 117 public source-only Python tests**, plus all four JavaScript smoke runners in each checkout. The alpha8 evidence above remains a separate earlier check; it does not cover SnowyHome.

## Remaining work

- One user-controlled alpha8 Spring session: visual drag/drop/folder/dock/launch/Settings trials, fresh process/receipt verification and protected-data checks.
- Real Android target plus Windows/Linux hosts: permissions, SELinux, native QuickJS/architecture, signing-compatible data-preserving deployment and runtime recovery. Never uninstall/reinstall stock Spring to bypass a signature mismatch.
- SnowyHome pack-import UI and live validation; an on-device SSH service with authentication/native Settings; generic third-party home APIs.
- Full native runtime deadline/heap/stack, concurrent-alert, multi-tweak, update/uninstall and Safe Mode recovery trials.
- User confirmation of Ruby's always-red bars/Discord link, companion 0.6 and expanded Settings/App Store/Phone coverage.

The working repository index continues to contain **only Animaper and ColoredBar**. Source progress, unlisted drafts, automated checks and live-confirmed features are different readiness levels.
