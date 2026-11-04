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

## Remaining work

- One user-controlled alpha8 Spring session: visual drag/drop/folder/dock/launch/Settings trials, fresh process/receipt verification and protected-data checks.
- Real Android target plus Windows/Linux hosts: permissions, SELinux, native QuickJS/architecture, signing-compatible data-preserving deployment and runtime recovery. Never uninstall/reinstall stock Spring to bypass a signature mismatch.
- SnowyHome icon packs, badge colours, hidden labels and corner controls; an on-device SSH service with authentication/native Settings; generic third-party home APIs.
- Full native runtime deadline/heap/stack, concurrent-alert, multi-tweak, update/uninstall and Safe Mode recovery trials.
- User confirmation of Ruby's always-red bars/Discord link, companion 0.6 and expanded Settings/App Store/Phone coverage.

The working repository index continues to contain **only Animaper and ColoredBar**. Source progress, unlisted drafts, automated checks and live-confirmed features are different readiness levels.
