# ColoredBar (development)

ColoredBar is an experimental built-in package with a native page in **Spring Settings → ColoredBar** when enabled. Basic behaviour was live-confirmed in alpha4 on Mac.APK on 2026-11-05. New coverage fixes, transitions and recovery still need explicit live checks.

## Preferences

- **Presets:** eight convenient starting colours.
- **Custom Hex Colour:** select each of the six `RRGGBB` digits from `0`–`F`, allowing any exact 24-bit RGB colour without an Android-style dialog. Current digits and the chosen hex value appear in Settings.
- **Excluded Apps:** checked apps retain their original navigation artwork. Apps are collected read-only from Spring's home pages and dock, including `.sapp` IDs. Previously saved exclusions remain visible if the app is no longer present.

The colour and exclusions are saved as `files/ruby/coloredbar.color` and `files/ruby/coloredbar.exclusions.json`. Removing the tweak does not delete preferences.

## Coverage fixes and Ruby branding

Alpha6 source covers Settings' separate lazy artwork loaders and App Store's custom `ios6/apps/appstore/NavBar.png`, including deferred drawing. Excluded Apps now discovers plain dock/folder app records as well as page icons; Phone and other dock apps can be excluded. The earlier engine skipped these paths. Shadow images, search glyphs and other apps' bottom bars stay stock.

Ruby IDs `sapp:com.ruby.manager` and `com.ruby.manager` are permanently excluded from ColoredBar. Ruby's red (`#C9253D`) navigation and bottom tabs are its own built-in appearance, active without any tweak marker and in Safe Mode. Ruby never appears as a toggleable exclusion. Both skins tint immutable per-render views, leaving shared bitmap caches, home icons and saved page/position files untouched.

The alpha6 packaged-engine checks passed with Mac.APK's actual Bitmap/Canvas: both Settings loaders, fallback cache, header drawing, colour changes, exclusions and Safe Mode. Ruby branding and App Store asset selection have isolated checks; a live user trial is still needed. A full launcher reopen on the rebuilt engine is required. Installing ColoredBar's small archive alone cannot add compiled engine fixes. Ruby 1.8's Discord button additionally needs the new trusted-script pin.

## Rendering

Spring caches stock assets. ColoredBar instead wraps the artwork maps in the two per-app render dispatchers, using the ID of the app actually being rendered (including transition/screenshot rendering). It creates cached tinted copies without modifying stock bitmaps, shading/alpha, wallpaper or shadow assets. Safe Mode and excluded apps use the original map. Preferences are reread within 500 ms; no respring is requested.

Only shared `UINavigationBar*.png` artwork is affected. Apps drawing custom toolbars, custom nav artwork or solid colours are not recoloured by this adapter. Actual UI redraw timing, transitions and bitmap behavior still require live checks.

`builtin-repo/sources/coloredbar` is a draft source package. Keep it out of the published index until the native Settings/navigation, exclusions and Safe Mode flows are tested on the running development engine.

```sh
python3 patches/tests/check_coloredbar.py <converted-Spring.jar>
```

This test uses real Spring Settings models with a software-bitmap double, not a running launcher.
