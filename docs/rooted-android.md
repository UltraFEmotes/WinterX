# WinterX on a rooted Android phone or emulator

On Android, WinterX runs inside the **normally installed Spring 0.8.1 app**. Nothing is reinstalled: the APK, its signature, its app ID and your data stay exactly as they are. Your computer starts Spring with WinterX's core loaded, through Frida, and Spring then runs your tweaks.

This works from **macOS, Linux and Windows**. It's been tested end to end on an Android 10 (API 29) ARM64 emulator from macOS. The Linux and Windows steps use the same Python launcher; they haven't been run on those systems yet, so please report anything that goes wrong.

## What you need

On the device:

- **Spring 0.8.1**, installed normally, signed in, and with **Developer Mode** turned on in Spring's Settings.
- **Root over adb.** Emulator images without Google Play give you this with `adb root`. On a rooted phone, a root manager providing `su` works too. WinterX never roots a device for you.
- An **arm64-v8a** or **x86_64** CPU (most phones and most emulators).

On your computer:

| Tool | macOS | Linux | Windows |
| --- | --- | --- | --- |
| Python 3.9+ | `brew install python` or python.org | your package manager | python.org (includes `py`) |
| Frida's Python bindings | `python3 -m pip install frida==17.25.2` | same | `py -3 -m pip install frida==17.25.2` |
| adb (Android platform-tools) | Android Studio, or `sdkmanager platform-tools` | same, or your package manager | Android Studio, or `sdkmanager platform-tools` |
| Node.js (to build the loader once) | nodejs.org or `brew install node` | your package manager | nodejs.org |
| A WinterX core | built with [`extensions/build.py`](native-packages.md#build-the-core-locally) | same | same |

The launcher downloads the matching **Frida server** for your device's CPU from Frida's official releases and checks its SHA-256 before pushing it. Pinned hashes: arm64 `7bb6219131819c11e5fe53b3e32fae0b8d1ff4c2a9c35c1a549d2703ea0f3b9b`, x86_64 `81a916d8e5e23c01350a31521b364489751785a17954b340cfaa644b8c474d19`.

Check that everything is found with:

```sh
python3 tools/toolchain.py
```

## One-time setup

Connect the device (or start the emulator) and check `adb devices` lists it. Then, from the WinterX folder:

```sh
python3 tools/rooted_launch.py setup --core out/core
```

(On Windows use `py -3` instead of `python3`.)

Setup checks root, puts the Frida server on the device, verifies that the installed Spring is the supported 0.8.1, **backs up Spring's private data** to your computer, and copies WinterX's core files into Spring's own folder. If Spring is open, it asks before closing it. Your layouts, settings and sign-in are kept.

Setup is stored per device in `~/.winterx/android/devices/<serial>/` (`%USERPROFILE%\.winterx\...` on Windows). Keep that folder: it holds the backup and the record of what was staged. Set `WINTERX_HOME` to keep it somewhere else.

Run setup again whenever you build a new core.

## Start Spring with WinterX

| macOS | Linux | Windows |
| --- | --- | --- |
| double-click **Start WinterX Android.command** | `./start-winterx-android.sh` | double-click **start-winterx-android.bat** |

Or run `python3 tools/rooted_launch.py start` directly. Spring opens showing the WinterX boot screen. **Keep that window open while you use Spring**: it also serves Ruby when you add or refresh sources. Installing and removing tweaks happens inside WinterX itself and doesn't need it.

When Spring is closed (swiped away, force-stopped, or the device shuts down), the window says the session has ended. Start it again to bring WinterX back. If Spring was opened normally, without WinterX, the launcher asks before closing it.

With more than one device connected, choose one with `--serial <serial from adb devices>` or the `WINTERX_SERIAL` environment variable. To use a particular Python (for example one in a virtual environment with Frida installed), set `WINTERX_PYTHON` for the wrapper scripts.

## Install Ruby, WinterX and tweaks

With Developer Mode on, copy the apps you built into Spring's inbox; Spring installs them on its own:

```sh
adb push out/Ruby.sapp /sdcard/Android/data/com.guille.spring/files/sapps-inbox/
adb push out/WinterX.sapp /sdcard/Android/data/com.guille.spring/files/sapps-inbox/
```

Open **Ruby**: the built-in repository is already listed under Sources. Pick a tweak and tap **Install**; Ruby shows the install console until it's done. Fully close Spring and start it again with WinterX to load new tweaks, then find their settings in **Settings → WINTERX TWEAKS**.

## Recovery

- **Safe Mode** in Ruby starts Spring with no tweak code at all. Use it if a tweak misbehaves, remove the tweak in Ruby, leave Safe Mode, and start Spring with WinterX again.
- A tweak that crashes is switched off for that session and its error is written to `winterx-tweaks/<id>/last-error.txt` in Spring's files.
- Package installs are journalled: an interrupted install or removal is finished or rolled back the next time WinterX handles a request.
- Spring's APK is never replaced or uninstalled, and the backup from setup is never restored automatically. To go back to plain Spring, just open Spring normally instead of through WinterX.

## Troubleshooting

| Message | What to do |
| --- | --- |
| `This device has no root over adb` | Use an emulator image without Google Play (`adb root` works there), or a rooted phone with `su`. |
| `Frida … is installed but WinterX needs 17.25.2` | `python3 -m pip install frida==17.25.2` for the Python the launcher runs with. |
| `No pinned Frida server for this CPU` | Only arm64-v8a and x86_64 are supported. |
| `This device isn't set up yet` | Run `setup --core out/core` first. |
| `Launch didn't start; retrying once…` | A Frida attach timeout; the launcher retries automatically. If it fails twice, run it again. |
| Spring opens without the WinterX boot screen | It was opened normally. Close it and use the launcher. |

## Advanced: the lower-level tool

`tools/rooted_launch.py` wraps `tools/android_runtime.py`, which you can drive directly (`inspect`, `stage`, `launch --bridge`) with an explicit `--state` folder and your own Frida server. See [portable bridge details](android-bridge.md) for older read-only transports.
