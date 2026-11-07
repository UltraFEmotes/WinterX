# Rootless Android

WinterX without root. Your computer builds **"Spring Launcher (WinterX)"**: a copy of your own Spring with WinterX's core built in, under its own app ID (`com.winterx.spring`), and installs it **beside** your original Spring. The original stays installed and untouched.

## Why a copy

Without root nothing can get into an app you already have: Android won't let one app reach into another's process or files. So WinterX goes in the only way left, inside a copy of Spring that's built from your phone's own Spring APK on your own computer and signed with your own key. Nobody ships a modified Spring; each person builds their own.

## Set it up

You need a computer (macOS, Linux or Windows) with adb, a JDK, apktool and the Android build-tools (the same tools as for [making tweaks](making-tweaks.md#1-get-the-tools)), and the phone with **USB debugging** on and Spring 0.8.1 or 0.9 Preview 1 installed.

1. Connect the phone and run **Start WinterX Rootless** (`Start WinterX Rootless.command` on macOS, `start-winterx-rootless.sh` on Linux, `start-winterx-rootless.bat` on Windows), or `python3 tools/rootless_launch.py start`.
2. It reads the installed Spring APK (no root needed), checks it's a supported version, builds the copy and installs it. The first build takes a few minutes; later runs reuse it until Spring or WinterX changes. Spring 0.9 Preview 1 works the same way: only the phone's own Spring is needed.
3. On the phone, sign in to Spring in the copy. If Android asks which app should open the sign-in link, choose **Spring Launcher (WinterX)**.
4. In the Home app settings that open, choose **Spring Launcher (WinterX)**.
5. Install tweaks from Ruby, as anywhere else. Every tweak in the built-in repository works rootless.

The first run creates your signing key in `~/.winterx/android/` (`winterx-signing.jks` and its password). **Back that folder up**: updates to the copy must be signed with the same key.

## Everyday commands

```sh
python3 tools/rootless_launch.py start              # build if needed, install or update, open
python3 tools/rootless_launch.py bridge             # Ruby's source refreshes and live status, while you use it
python3 tools/rootless_launch.py safe-mode on       # if a tweak keeps it from starting (off to undo)
python3 tools/rootless_launch.py backup copy.tar    # the copy's data: layouts, apps, tweaks
```

These reach the copy's files over USB with `adb run-as`, which works because the copy is built debuggable.

## Limits

- **A separate app.** The copy starts fresh: your original Spring's layouts, apps and settings don't carry over (Spring can't export them, and without root nothing can read them). Sign in again, and grant the keyboard, notification-badge and Double-Tap to Sleep permissions again if you used them.
- **Updates are manual.** Spring updates don't reach the copy. After Spring updates, run Start WinterX Rootless again: the copy updates in place and keeps its data, as long as you still have your signing key. WinterX updates work the same way, since the core is built in.
- **Debuggable.** The copy is a little slower than a release build, and anyone with USB-debugging access to the phone can read its data. Turn USB debugging off when you're not using the computer side.
- **Tweaks that need root** are marked **(Requires Root)** in Ruby and can't be installed. No built-in tweak needs root.
- **Recovery.** Safe Mode works as everywhere (see the command above). If the copy won't start, choose your original Spring as the Home app again, or uninstall Spring Launcher (WinterX).

## Tweak authors

See [Rootless installs](making-tweaks.md#rootless-installs): most tweaks need no changes; a tweak that reads files the user supplies should let them pick the file with the system file picker.
