# Hello Native

A standalone Java/Dex tweak using the public `winterx.native/1` API. Official packages use this same `NativeTweak` interface and installation path.

Build your local core/API first, following [Native packages](../../docs/native-packages.md). Then:

```sh
python3 extensions/build.py package examples/native-hello out/hello-native.springys \
  --sdk out/core/winterx-native-api.jar --spring-api out/core/spring-api.jar
```

Import the resulting `.springys` in **Ruby → Packages → Local Packages**, tap **Install**, and fully close/reopen Spring through WinterX. Open **Settings → WINTERX TWEAKS → Hello Native** and tap the counter. Reopen its page to see the saved value.

The counter lives in `winterx-tweaks/me.example.hello-native/data/counter.txt`. Removing and reinstalling the package keeps this value. Installation does not select an animation or modify Home layouts. The package is an optional example, not a preinstalled tweak.

`settings.page` returns Spring's native Settings model; `settings.tap` receives the page and row IDs for this package only. The included editable source, JVM JAR and Android DEX are independently hash-pinned in the built package.
