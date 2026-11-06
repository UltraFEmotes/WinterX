# WinterX & Ruby

WinterX is a fan-made project by WeirdMM for [Spring](https://spring.elguille.me), the iOS-style Android simulator. Ruby is its iOS 6-inspired package manager. This is a fun project built for experimenting with Spring and sharing tweaks with its community.

![Ruby's package screen in Spring](docs/images/ruby-packages.png)
![Spring's iOS-style Settings screen](docs/images/spring-settings.png)

WinterX targets **Spring 0.8.1**. Its core contains no tweaks, only the means to run them: tweaks are independently installed **Java/Dex code packages** that can hook any of Spring's methods Cydia-style, run their own JavaScript inside Spring apps, add Settings pages and bring their own apps. **Fresh installations include no tweaks.** Want to make one? Start with **[Making WinterX tweaks](docs/making-tweaks.md)**. Animaper and the other installed tweaks share **Settings → WINTERX TWEAKS**, while Ruby keeps its own red bars independently.

The rooted workflow preserves Spring's original APK and app identity. Building and launching work from **macOS, Linux and Windows**; live testing so far uses an **Android 10 ARM64 emulator driven from macOS**, so physical devices and the Linux/Windows hosts aren't verified yet, and rootless support is still to come. See [development status](docs/development-status.md). Message+ video sending and reactions remain unfinished.

## Try the development build

1. [Build the core and apps locally](docs/native-packages.md) using your separately obtained Spring APK/SDK.
2. Follow the [rooted Android/emulator setup](docs/rooted-android.md) (`tools/rooted_launch.py setup`, then the start script for your OS) or the [Mac.APK core workflow](docs/native-packages.md#macapk-core-workflow).
3. Install Ruby and WinterX through Spring's Developer Mode/inbox importer.
4. In Ruby, open the built-in repository and install the tweaks you want. When the install console finishes, fully reopen Spring through WinterX to load them.

Packages: [Animaper](docs/animaper.md), [ColoredBar](docs/coloredbar.md), [FreeMe and DockIn](docs/layout-tweaks.md), [SnowyHome](docs/snowyhome.md), [Message+](docs/messageplus.md), [SSH](docs/ssh.md), plus two just-for-fun tweaks: **Gravity** (shake the phone and the Home icons fall, tumble and can be thrown around) and **Harlem Shake** (a remake of the 2013 meme tweak: one icon dances, then they all do at the drop), and **Android Keyboard** (type into Spring with your real keyboard on Mac.APK, or use your phone's own keyboard, instead of the iOS one), and **LegacyBooter** (an app that runs the original iPhone on iPhone OS 1.0 inside Spring, using kelindi's iphone-1-emulator). SSH starts only through its explicit Settings control.

Spring itself and its APK are not part of WinterX. Ruby and WinterX are independent fan projects and are not affiliated with Spring, Apple, or Cydia.

## Developers

- **[Making WinterX tweaks](docs/making-tweaks.md)**: tutorial and full reference (manifest, Java API, every hook point, Settings pages, publishing)
- [Build a `.springys` package](docs/springys-format.md)
- [Create a repository](docs/repository-design.md)
- [WinterX testing and recovery](docs/testing-winterx.md)
- [Built-in repository development](builtin-repo/README.md)
- [Actual executable-tweak implementation and API](docs/tweak-runtime-design.md)
- [Native code packages and public hooks](docs/native-packages.md) · [Standalone community example](examples/native-hello/)
- [FreeMe and DockIn](docs/layout-tweaks.md) · [Portable bridge/SSH-client development](docs/android-bridge.md)

Check and build the Ruby app with Spring SDK r10:

```sh
python3 SpringSDK-r10/tools/spring_pack.py check Ruby
python3 tools/build_sapp.py Ruby out/Ruby.sapp
python3 -m unittest discover -s tests -q
node tests/ruby_ui_smoke.js
```

Reviewed source/docs are published separately. Third-party Spring assets, the Spring APK/SDK, private app data and build outputs are excluded; third-party artwork must not be assumed to be covered by the project source license.

## License

Original WinterX and Ruby project code is available under the [MIT License](LICENSE). Third-party software, artwork, trademarks, and Spring screenshots retain their respective owners' rights and are not relicensed by that license. The Spring APK and SDK are excluded from the source repository.
