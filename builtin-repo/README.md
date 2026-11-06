# Ruby's built-in repository

This local index is Ruby's always-present **built-in source**. It lists the ten official source-backed Java/Dex code packages: **Animaper, ColoredBar, DockIn, FreeMe, Message+, SnowyHome and SSH** (0.2.x), **Gravity** (0.1.0) **Harlem Shake** (0.1.2) and **Android Keyboard** (0.1.0). Ruby shows it as "Ruby's Built-in Repository" on Mac.APK and in rooted Android sessions (`tools/android_runtime.py` uses this folder by default).

Listing a package never installs it. A fresh WinterX core ships with **zero tweaks installed**; each package is installed only when the user taps Install in Ruby, then loads after Spring is reopened through WinterX. Preferences for every installed package live in Spring Settings → **WINTERX TWEAKS**. Each package needs a WinterX core with the native package runtime (`winterx-native-hooks-v1`); older engines show it as unavailable.

Package archives are versioned (`packages/<name>-<version>.springys`). Older archives in `packages/` (the earlier JavaScript/hook-based Animaper and ColoredBar, Settings Button Test, UI Color Test, Free Icon Placement Test and IExplored) are kept for existing users and history but are not listed. Preserve existing users' data; never uninstall anything silently.

SSH stays stopped until it is explicitly started in its Settings page with a configured key. Message+ video and reactions are unfinished. Harlem Shake doesn't include the song: tap its song row and pick an audio file of your own (the system file picker; a real macOS dialog on Mac.APK).

See the [native package guide](../docs/native-packages.md), [rooted Android guide](../docs/rooted-android.md) and [repository guide](../docs/repository-design.md).
