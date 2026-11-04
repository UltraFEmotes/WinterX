# Release checklist

Before the final public release, remove the three development test tweaks from Ruby's catalogue and the built-in repository index and packages. The development builds may keep them for testing. Verify that no test entries appear in browsing, search, local imports bundled with the release, or the default source. Preserve users' installed test data and do not silently uninstall anything.

Verify repository, update, removal, Safe Mode and recovery flows on supported devices, review third-party assets and licensing, and update the public documentation to match the features actually shipped.

Built-in tweaks with preferences must expose them in **Spring's actual Settings app**, using native iOS 6 styling. Check Animaper's effects, ColoredBar's exact colour and per-app exclusions, SnowyHome's icon packs/badges/labels/corners and SSH's service/authentication controls when those implementations are ready. A Ruby-only preferences screen does not satisfy this requirement.

The experimental source update and ColoredBar catalogue publication are authorized after the alpha4 live confirmation. Do not describe alpha6 automated checks as live verification or a hardened sandbox. Never publish the executable developer example or test tweaks in the built-in index. Full native-limit, update/uninstall, Safe Mode and recovery trials remain required before calling the runtime stable.

SSH, SnowyHome, FreeMe (normal grid cells with gaps across home pages; stock dock/folders), DockIn (4–7 dock icons, default 4), generic third-party home hooks, rooted Android/emulators and Windows/Linux adapters are still outstanding. Do not offer unfinished catalogue entries as working tweaks.
