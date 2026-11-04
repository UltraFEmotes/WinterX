# Release checklist

Before the final public release, remove the three development test tweaks from Ruby's catalogue and the built-in repository index and packages. The development builds may keep them for testing. Verify that no test entries appear in browsing, search, local imports bundled with the release, or the default source. Preserve users' installed test data and do not silently uninstall anything.

Verify repository, update, removal, Safe Mode and recovery flows on supported devices, review third-party assets and licensing, and update the public documentation to match the features actually shipped.

Built-in tweaks with preferences must expose them in **Spring's actual Settings app**, using native iOS 6 styling. Check Animaper's effects, ColoredBar's exact colour and per-app exclusions, SnowyHome's icon packs/badges/labels/corners and SSH's service/authentication controls when those implementations are ready. A Ruby-only preferences screen does not satisfy this requirement.

The experimental source/docs update, including independently authored executable-tweak support, is authorized; current work is not limited to alpha8. Do not describe alpha8 packaged checks as live verification or a hardened sandbox. Never publish the executable developer example, layout drafts or test tweaks in the working built-in index. Full native-limit, update/uninstall, Safe Mode and recovery trials remain required before calling the runtime stable. Exclude APKs, companion binaries, SDKs, personal data, backups and private handoff records from source publication.

FreeMe/DockIn now have unlisted native-hook drafts and packaged checks, but complete live pointer/visual validation is still outstanding. SnowyHome (icon packs/badges/labels/corners), the on-device SSH service/native Settings, generic third-party home hooks and verified Android runtime deployment/reconciliation remain unfinished. Portable inventory/repositories, transfers/recovery and a pinned noninteractive SSH-client transport exist; they do not constitute live Windows/Linux/Android support or the SSH tweak. Do not offer unfinished catalogue entries as working tweaks.
