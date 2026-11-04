# Ruby's built-in repository

This local index contains **Animaper and ColoredBar**, with matching source and hosted packages in [Ruby-Repo](https://github.com/UltraFEmotes/Ruby-Repo). Both select compiled hooks in compatible WinterX engines and use Spring's actual Settings app for preferences. The built-in source works through the Mac.APK bridge.

ColoredBar provides presets, exact RGB hex colours and app exclusions. Updated engines permanently exclude Ruby, whose red navigation and bottom tabs are its own built-in appearance. Basic ColoredBar behaviour was live-confirmed on Mac.APK; newer coverage fixes and recovery remain experimental.

Settings Button Test, UI Color Test, Free Icon Placement Test and the executable developer example stay outside this index. Preserve existing users' test data; do not silently uninstall it. SnowyHome, SSH, FreeMe and DockIn remain unfinished.

See the [package guide](../docs/springys-format.md), [ColoredBar notes](../docs/coloredbar.md) and [repository guide](../docs/repository-design.md).

The `sources/freeme` and `sources/dockin` manifests are unlisted drafts requiring verified running engines with `freeme-grid-v1` and `dockin-native-v1`, respectively. Alpha6 is incompatible; the prepared alpha8-local engine includes both. Neither draft is installed automatically. See [layout development status](../docs/layout-tweaks.md) before a developer trial.

`sources/snowyhome` is a separate unlisted draft requiring **snowyhome-render-v1** hooks, which the prepared alpha8 **does not include**. Icon-pack authoring/loading and native appearance controls passed isolated source/packaged checks in a separate experiment, not live validation. See [SnowyHome development](../docs/snowyhome.md). Nothing is added to this catalogue automatically.
