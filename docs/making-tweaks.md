# Making WinterX tweaks

This guide covers how to write, build, install and publish your own tweak for **Spring 0.8.1** running WinterX. It starts with a step-by-step tutorial, then documents everything a tweak can contain.

- [What a tweak is](#what-a-tweak-is)
- [Tutorial: your first tweak](#tutorial-your-first-tweak)
- [The manifest](#the-manifest)
- [The Java API](#the-java-api)
- [Hooking any method](#hooking-any-method)
- [Running code inside apps](#running-code-inside-apps)
- [Named hook points](#named-hook-points)
- [Settings pages](#settings-pages)
- [Saving data](#saving-data)
- [Features and dependencies](#features-and-dependencies)
- [Artwork](#artwork)
- [Bundling an app](#bundling-an-app)
- [Debugging](#debugging)
- [Limits and rules](#limits-and-rules)
- [Publishing](#publishing)
- [JavaScript tweaks](#javascript-tweaks)

## What a tweak is

A tweak is a `.springys` file: a ZIP archive containing a `manifest.json`, your editable Java source, and that source compiled twice (a JVM `classes.jar` and an Android `classes.dex`). Ruby installs it; WinterX loads it the next time Spring is opened through WinterX.

WinterX itself contains **no tweaks**. A tweak is a Java class that changes Spring in two ways, and can mix them freely:

- **Hook any method** in Spring, Cydia-style. Every one of Spring's 22,000+ methods (Home, Settings, Mail, Maps, Messages, the App Store, the lock screen, anything Spring draws or decides) can be hooked by name. Your hook can look at or change the arguments, run the original, change its result, or skip it entirely. See [Hooking any method](#hooking-any-method).
- **Run JavaScript inside apps.** A tweak can ship scripts that run inside any Spring app (`.sapp`), or all of them, before the app's own code, and change anything the app does. See [Running code inside apps](#running-code-inside-apps).
- **Named hook points**: a set of stable, documented places WinterX already exposes for common jobs (Settings pages, drawing Home icons, dock and grid layout, artwork). They're simpler to use and keep working when Spring's internals shuffle. See [Named hook points](#named-hook-points).

The official tweaks (Animaper, ColoredBar, DockIn, FreeMe, Message+, SnowyHome, SSH, Gravity, Harlem Shake, Android Keyboard, LegacyBooter) are ordinary packages that use this same API and install the same way, so their source is a good set of worked examples (`extensions/packages/<name>/source/`). [Hook Demo](../examples/hook-demo/) shows method hooking, and [Hello Native](../examples/native-hello/) shows Settings pages. Gravity is a good example of per-frame animation, method hooks (it hooks Spring's touch handling and animation loop) and drawing icons somewhere other than their cell; Harlem Shake shows timed animation, playing audio and opening the system file picker; Android Keyboard shows hooking Spring's text input and adding your own Android view (for the on-screen keyboard). LegacyBooter shows bundling an app, noticing when Spring opens it (by hooking `QuickJs.u`, which evaluates every app's `main.js`), and drawing a WebView over Spring's screen on both Android and Mac.APK.

There's no list of things a tweak is allowed to change. If Spring does it, a tweak can hook it. A tweak can also:

- add pages to **Spring Settings → WINTERX TWEAKS** (or have none at all),
- bring its own apps that install and uninstall with it,
- save its own data, declare features, and depend on other tweaks, including shared libraries other people publish.

If a tweak goes wrong, **Safe Mode** in Ruby starts Spring with no tweak code at all, so you can always get back in and remove it. WinterX's and Ruby's own classes are the one thing that can't be hooked, so nothing can disable that way out.

A tweak **doesn't need** a Settings page. Leave out `settings_entry` and the `settings.*` hooks and it simply won't appear in the Settings list.

> **Trust.** Tweak code runs inside Spring with Spring's own permissions. Each tweak gets its own classloader, and a crashing tweak is switched off rather than taking Spring down, but this is **not a security sandbox**. Only install tweaks whose source you trust. That's why every package must ship its source.

## Tutorial: your first tweak

This builds a tweak called **Hello Native** that adds a Settings page with a counter button. The finished version is in [`examples/native-hello/`](../examples/native-hello/).

### 1. Get the tools

Tweaks can be built on **macOS, Linux or Windows**. You need:

- **Python 3.9+** and a **JDK 17 or newer** (set `JAVA_HOME` if `javac` isn't on your PATH),
- the **Android SDK** with a platform (`sdkmanager "platforms;android-34"`) and build-tools (`sdkmanager "build-tools;36.0.0"`); set `ANDROID_HOME` if it isn't in the usual place,
- [**apktool**](https://apktool.org) (only for building the core),
- [**dex2jar**](https://github.com/pxb1988/dex2jar) (only for building the core; set `WINTERX_DEX2JAR` to its `d2j-dex2jar` script). On a Mac with Mac.APK installed, Mac.APK's converter is used instead,
- your own copy of **Spring 0.8.1** (`Spring-0.8.1.apk`, SHA-256 `f07f980fe681a6de9c4ce8735ae1c0bb0f852f447fbdb925d2dec37cf9778e5c`).

Check what's found:

```sh
python3 tools/toolchain.py
```

It lists each tool and where it came from; every path can be overridden with an environment variable (see the top of `tools/toolchain.py`). On Windows, use `py -3` wherever this guide says `python3`. The core and tweaks built this way are the same on every system; the Spring DEX in the core comes out byte-identical with or without Mac.APK.

### 2. Build the WinterX API once

Your tweak compiles against two JARs that are generated from your own Spring APK:

```sh
python3 extensions/build.py runtime /path/to/Spring-0.8.1.apk out/core
```

This gives you:

| File | What it is |
| --- | --- |
| `out/core/winterx-native-api.jar` | The WinterX API: `NativeTweak`, `TweakContext`, `NativePlatform` |
| `out/core/spring-api.jar` | Spring's own classes (`E1.*`, `x1.*`, …), so you can use its models |
| `out/core/native-api.json` | Every hook point with its exact Java signature, fallback and policy |

Keep these local. They're derived from Spring and must not be published.

### 3. Make the package folder

```text
my-tweak/
├── manifest.json
├── assets/                 optional: icon.png, previews
└── source/
    └── com/example/mytweak/
        └── MyTweak.java
```

Everything under `source/` is compiled. Use your own Java package name (not `winterx.*`, `android.*`, Spring's packages, etc.; those are rejected).

### 4. Write the manifest

```json
{
  "format": "winterx.springys/3",
  "type": "tweak",
  "runtime": "java",
  "api": "winterx.native/1",
  "id": "com.example.hello",
  "name": "Hello",
  "version": "1.0.0",
  "author": "Your Name",
  "license": "MIT",
  "description": "Adds a counter to Spring Settings.",
  "source": "https://github.com/you/hello",
  "entry": "com.example.mytweak.MyTweak",
  "capabilities": ["native.hooks"],
  "exports": ["settings.page", "settings.tap"],
  "settings_entry": "main"
}
```

`exports` lists exactly which hook points your class answers. Every field is explained in [The manifest](#the-manifest).

### 5. Write the class

```java
package com.example.mytweak;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.util.Collections;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

public final class MyTweak implements NativeTweak {
    private TweakContext context;
    private int count;

    @Override public void start(TweakContext context) {
        this.context = context;           // called once when Spring opens
    }

    @Override public Object call(String point, Object[] args) {
        if (!context.active()) return null;
        if ("settings.page".equals(point) && "main".equals(args[0])) {
            String row = "winterx-tw-r/" + context.id() + "/main/add";
            V6 button = Z3.g(Z3.a, row, "Count: " + count, null, null, null, 0x18);
            W6 section = new W6("HELLO", null, null, null, Collections.singletonList(button));
            return new T6("winterx-tw-p/" + context.id(), "Hello", Collections.singletonList(section));
        }
        if ("settings.tap".equals(point) && "main".equals(args[0]) && "add".equals(args[1])) {
            count++;
        }
        return null;                      // null = "I have nothing to change"
    }
}
```

This counter resets when Spring reopens. [Saving data](#saving-data) shows how to keep it.

### 6. Build it

```sh
python3 extensions/build.py package my-tweak out/hello-1.0.0.springys \
  --sdk out/core/winterx-native-api.jar --spring-api out/core/spring-api.jar
python3 tools/springys_tool.py inspect out/hello-1.0.0.springys
```

The builder compiles your source, produces the JAR and DEX, pins every file's SHA-256 in the manifest and validates the archive. Choose a new output filename each time; it won't overwrite an existing one.

If your tweak uses a third-party library, pass its JAR with `--library`. Its classes and any `licenses/` notices are included in your package (see how SSH does it in [native-packages.md](native-packages.md)).

### 7. Install and test it

1. Get the `.springys` onto the device, then in Ruby open **Packages → Local Packages → Import Package…** (or publish it in a repository).
2. Open your package and tap **Install**. Ruby shows the install console and its steps; wait for **Return to Ruby**. WinterX's core checks and installs the package itself, which takes a few seconds; the Ruby bridge is only needed for adding or refreshing sources.
3. Fully close Spring and reopen it **through WinterX**. Code is only loaded at startup.
4. Open **Settings → WINTERX TWEAKS → Hello** and tap the button.

To change your tweak: edit, rebuild with a new version number, and **Install** again (Ruby shows it as an update), then reopen Spring. To remove it, use **Remove** in Ruby. Its saved data is kept.

If something goes wrong, see [Debugging](#debugging). If Spring itself won't behave, turn on **Safe Mode** in Ruby: no tweak code runs at all in Safe Mode.

## The manifest

| Field | Required | Meaning |
| --- | --- | --- |
| `format` | yes | `"winterx.springys/3"` |
| `type` | yes | `"tweak"` |
| `runtime` | yes | `"java"` |
| `api` | yes | `"winterx.native/1"` |
| `id` | yes | Unique reverse-domain ID, lowercase letters/digits separated by `.` or `-` (`com.example.hello`). It identifies updates, so never change it |
| `name` | yes | Display name, up to 80 characters |
| `version` | yes | `1.0`, `1.2.3`, `1.2.3.4`, optionally with `-beta.1` or `+build` |
| `author` | yes | Up to 120 characters |
| `license` | yes | For example `MIT`, up to 80 characters |
| `description` | yes | Shown in Ruby, up to 4000 characters |
| `source` | yes | Public **HTTPS** link to your source code (no credentials or `#fragment`). Ruby shows it as **Source Code** |
| `entry` | yes | Fully-qualified name of your `NativeTweak` class |
| `capabilities` | yes | Exactly `["native.hooks"]` |
| `exports` | yes | 1–128 hook point names your class handles (see [Hook points](#hook-points)) |
| `settings_entry` | no | Adds your tweak to **WINTERX TWEAKS**. The value is the page key passed to `settings.page` when the user opens it (`"main"` is conventional) |
| `features` | no | Up to 32 feature names you provide, for example `example.counter` |
| `requires` | no | Up to 16 IDs of other native tweaks that must be installed first |
| `icon` | no | A PNG/JPEG inside `assets/` |
| `previews` | no | Up to 5 PNG/JPEG screenshots inside `assets/` |
| `apps` | no | Up to 4 Spring apps to install with the tweak, as `apps/<Name>.sapp` (see [Bundling an app](#bundling-an-app)) |
| `inject` | no | Up to 16 `{ "apps": [...], "script": "inject/<name>.js" }` entries: scripts to run inside those apps (see [Running code inside apps](#running-code-inside-apps)) |
| `files` | written by the builder | SHA-256 of every code, source and notice file. Don't write it yourself |

Hook and feature names are lowercase words joined by `.` or `-`, such as `render.icon.begin`.

## The Java API

### `NativeTweak`

Your `entry` class implements `winterx.extension.NativeTweak` and needs a public no-argument constructor.

```java
public interface NativeTweak {
    default void start(TweakContext context) throws Exception {}
    Object call(String point, Object[] arguments) throws Exception;
    default void stop() throws Exception {}
}
```

- **`start(context)`** runs once when Spring opens, after any tweaks you `require` have started. Don't assume Home has drawn yet. Load your saved settings here.
- **`call(point, arguments)`** runs whenever Spring reaches one of your exported hook points. `arguments` matches that point's signature. Return a value of the declared type to change Spring's behaviour, or `null` to leave it unchanged. Many calls happen on Spring's UI and render threads, so keep them fast and never block.
- **`stop()`** runs when your tweak is switched off (it failed, it was removed or updated, or Safe Mode). Close anything you opened.

If `start` or `call` throws, or `call` returns the wrong type, WinterX switches your tweak off for the rest of that session (see [Debugging](#debugging)). Other tweaks keep working, and Spring falls back to its normal behaviour.

### `TweakContext`

| Method | Returns |
| --- | --- |
| `id()` | Your package ID |
| `active()` | `false` once your tweak has been switched off. Check it before doing work in `call` |
| `files()` | Spring's private files folder |
| `data(name)` | A `File` in your own data folder (`winterx-tweaks/<id>/data/<name>`). `name` must be a simple filename |
| `call(point, args, fallback)` | Ask the other installed tweaks to handle `point` (first non-null answer wins, otherwise `fallback`). Use it to talk to a tweak you depend on |
| `hook(method, hook)` | Hook any Spring method (see [Hooking any method](#hooking-any-method)) |
| `canHook(method)` | Whether this core can hook that method |

### `NativePlatform`

Small read-only helpers for Spring's obfuscated models:

| Method | Returns |
| --- | --- |
| `editProfile(E1.O1 edit)` | The Home layout profile (`E1.i6`) for an edit/drag session, or `null` |
| `appId(Object model)` | The app ID of an app model (`E1.a`), or `null` |
| `screenWidth(Object profile)` / `screenHeight(...)` | Size of a layout profile (`E1.i6`), or 0 |

### Spring's classes

Spring is shipped obfuscated, so its classes have short names like `E1.T6` or `x1.i1`. They're in `spring-api.jar` and you can use them directly. WinterX doesn't document their fields beyond what this guide and `NativePlatform` cover. The most reliable way to learn one is to see how an official tweak uses it, for example `grep -rn "E1.q6" extensions/packages`. Commonly seen types:

| Class | What it is |
| --- | --- |
| `E1.T6`, `E1.W6`, `E1.V6`, `E1.Z3` | Settings page, section, row and row factory ([Settings pages](#settings-pages)) |
| `E1.i6` | Home layout profile (screen size and grid) |
| `E1.c` | A Home grid cell (row/column) |
| `E1.a` | An app (its ID is field `a`) |
| `E1.q6` | An app or icon being drawn or opened |
| `E1.O1` | A Home edit/drag session |
| `M1.b` | A screen position returned by location hooks |
| `x1.i1` | Spring's Home controller |
| `com.guille.spring.LauncherActivity` | Spring's Android activity |

## Hooking any method

This is the Cydia Substrate-style API: pick any method in Spring by its signature and wrap it with your own code.

```java
@Override public void start(TweakContext context) {
    context.hook("Lx1/c2;->h()LE1/o;", call -> {
        Object result = call.proceed();   // run the original (and any hooks after yours)
        // ...change result...
        return result;
    });
}
```

Register hooks in `start()`. They stay active until your tweak is switched off or removed.

### The hook API

`context.hook(method, hook)` registers a hook. `method` is the method's signature in either form:

- smali form: `Lx1/c2;->h()LE1/o;` (exactly as listed in `hookable-methods.txt`)
- dotted form: `x1.c2.h()LE1/o;`

The descriptor in brackets is the JVM descriptor (`I` int, `Z` boolean, `J` long, `F` float, `D` double, `V` void, `Lpkg/Class;` objects, `[` arrays). It's required because Spring's obfuscated classes often have several methods with the same short name.

`context.canHook(method)` tells you whether the current core can hook a method. Use it if you want to work across several WinterX versions.

Your hook receives a `MethodHooks.Call`:

| Member | What it is |
| --- | --- |
| `call.method` | The signature being called |
| `call.self` | The object the method was called on (`null` for static methods) |
| `call.args` | The arguments, boxed (`int` arrives as `Integer` and so on). You can replace elements |
| `call.proceed()` | Run the next tweak's hook for this method, or the original if none are left, with `call.args`. Returns the result |
| `call.original(args...)` | Run the original method directly with the given arguments, skipping any remaining hooks |

Whatever your hook returns becomes the method's result. For `void` methods the return value is ignored, so return `null`.

### Patterns

```java
// Before: look at or change the arguments, then run the original.
context.hook("Lorg/mozilla/javascript/TokenStream;->isAlpha(I)Z", call -> {
    call.args[0] = (int)'a';
    return call.proceed();
});

// After: run the original, then change what it returned.
context.hook("Lorg/mozilla/javascript/TokenStream;->isHexDigit(I)Z", call -> !((Boolean)call.proceed()));

// Replace: return your own value and never run the original.
context.hook("Lsome/Class;->isEnabled()Z", call -> Boolean.TRUE);

// Skip a void method in some cases.
context.hook("Lsome/Class;->vibrate(J)V", call -> quiet ? null : call.proceed());

// Call the original twice, or with different arguments.
context.hook("Lsome/Class;->draw(Landroid/graphics/Canvas;)V", call -> {
    call.original(call.args[0]);
    return call.original(call.args[0]);
});
```

When the original throws, `proceed()` rethrows that same exception unchanged, so you can catch it or let it go. Returning a value of the wrong type (or `null` from a method returning a primitive) is treated as a mistake: the original's result is used instead.

### Several tweaks hooking one method

Hooks chain in load order (alphabetical by package ID, dependencies first). The first tweak's hook runs first. When it calls `proceed()`, the next tweak's hook runs, and so on, until the last `proceed()` runs Spring's original. A hook that doesn't call `proceed()` stops the chain there. This is how two tweaks can both change the same thing without knowing about each other.

### Finding the method to hook

Spring is obfuscated, so classes have names like `x1.c2` and methods are `a`, `b`, `h`. Ways in:

1. **The list.** Building the core writes `out/core/hookable-methods.txt`, every hookable signature, one per line. Search it.
2. **Decompile.** Open `out/core/spring-api.jar` (or the Spring APK) in a decompiler such as [jadx](https://github.com/skylot/jadx) to read Spring's code as Java. Follow string constants: searching for text you see on screen (`"about-network"`, `"Wi-Fi"`, an asset name like `mail.png`) leads you to the code that uses it.
3. **javap.** `javap -p -cp out/core/spring-api.jar x1.c2` lists a class's fields and methods with their exact types.
4. **Log it.** Hook a candidate with `call -> { android.util.Log.d("MyTweak", call.method + " " + java.util.Arrays.toString(call.args)); return call.proceed(); }` and watch `adb logcat` while you use Spring.

Inside a hook you'll often need Spring's private fields. Use reflection (`getDeclaredField`, `setAccessible(true)`) or the public fields that the obfuscated classes expose directly from `spring-api.jar`.

### Worked example: Hook Demo

[`examples/hook-demo`](../examples/hook-demo/) changes the Network name in **Settings → General → About** to "WinterX ❄". Decompiling Spring shows that `x1.c2.h()` builds the device status object that Settings reads, and that it stores the carrier under the key `"about-network"` in one of its maps. So the tweak hooks that method, runs the original, and edits the map in the result:

```java
context.hook("Lx1/c2;->h()LE1/o;", call -> {
    Object status = call.proceed();
    for (Field field : status.getClass().getDeclaredFields()) {
        if (!Map.class.isAssignableFrom(field.getType())) continue;
        field.setAccessible(true);
        Map<String, Object> values = (Map<String, Object>)field.get(status);
        if (values != null && values.containsKey("about-network")) values.put("about-network", "WinterX \u2744");
    }
    return status;
});
```

It has no Settings page and no named hook points; its manifest just needs at least one entry in `exports` (any name, for example `"hooks.none"`).

### Rules and costs

- **What's hookable:** every method in Spring's code with a body, except constructors and static initialisers, and except Android/AndroidX library classes and WinterX's and Ruby's own classes. A handful of methods whose register layout can't take the hook check are also left out; they simply aren't in `hookable-methods.txt`.
- **Cost:** a method nobody hooks pays one field read and a branch. A hooked call costs around a couple of microseconds plus whatever your hook does. Spring calls drawing and layout methods many times per frame, so keep hooks on those quick and avoid allocating or touching files there.
- **Threads:** your hook runs on whatever thread called the method, often Spring's UI or render thread. Never block it.
- **Failures:** if your hook throws (rather than the original), WinterX switches your tweak off for that session, writes `last-error.txt`, and the call carries on as if your hook weren't there. Other tweaks keep working.
- **Removal and Safe Mode:** removing your tweak in Ruby stops its hooks within about a second. Safe Mode loads no tweaks, so no hooks are registered.
- **Spring updates:** obfuscated names are specific to Spring 0.8.1, which is the version WinterX supports. Named hook points are the stable option for code you want to keep working across WinterX releases; method hooks give you everything else.

## Running code inside apps

Spring apps (`.sapp` files, like the ones in the App Store) are written in JavaScript. A tweak can add its own JavaScript to them, the way Cydia tweaks inject into App Store apps. Your script runs in the app's own JavaScript context, **after Spring's UIKit is set up and before the app's `main.js`**, so it can replace or wrap anything the app will use.

1. Put the script in an `inject/` folder in your package, for example `inject/snowflake-titles.js`.
2. Declare which apps it runs in:

   ```json
   "inject": [
     { "apps": ["me.example.inject-target"], "script": "inject/snowflake-titles.js" },
     { "apps": ["*"], "script": "inject/every-app.js" }
   ]
   ```

   `apps` lists app IDs (the `id` in each app's `app.json`), or `"*"` for every app. The builder pins each script's hash, and WinterX checks it again before every run.

Spring's UIKit puts every class on the global object (`UIViewController`, `UILabel`, `UITableViewController`, `UIAlertView`, `UIApplication` and the rest; see the SDK's `docs/api.md`). So wrapping one is plain JavaScript:

```js
// inject/snowflake-titles.js: add a snowflake to every screen title in the app.
(function () {
  var Original = UIViewController;
  function SnowflakeController(options) {
    if (options && typeof options.title === "string") options.title = "\u2744 " + options.title;
    return new Original(options);
  }
  SnowflakeController.prototype = Original.prototype;
  UIViewController = SnowflakeController;
})();
```

Other things a script can do: wrap `UIAlertView.show` to change or silence alerts, replace `fetch` to see or rewrite network calls, add a button to an app's screens, keep extra data with the app's `storage`, or change values an app reads. Wrap things in a function (as above) so your own variables don't leak into the app.

[`examples/inject-demo`](../examples/inject-demo/) bundles a small app and injects the script above into it; opening the app shows "❄ Inject Target" although the app's own code says "Inject Target".

Rules:

- Scripts run each time the app starts, in the order tweaks load. They have exactly the app's own permissions; injection doesn't grant more.
- If a script throws, WinterX switches its tweak off (with `last-error.txt`) and the app starts normally.
- WinterX's own apps (Ruby, WinterX, IExplored) are never injected into, even with `"*"`.
- Scripts must be UTF-8 and at most 256 KB each.
- A tweak that only injects still needs its Java entry class, but it can be empty (implement `call` to return `null`), as in Inject Demo.

## Named hook points

### How a hook is called

When Spring reaches a hook point, WinterX goes through the installed tweaks that **export** that point, in load order (alphabetical by package ID, with dependencies before the tweaks that need them). The point's **policy** decides how the answers combine:

| Policy | Behaviour |
| --- | --- |
| `first` | The first tweak returning non-`null` wins; later tweaks aren't asked. If all return `null`, Spring uses its **fallback** (its normal behaviour) |
| `all` | Every tweak is called. These are notifications (`void`), so return `null` |
| `and` | A boolean that's `true` unless any tweak returns `false` |
| `or` | A boolean that's `false` unless any tweak returns `true` |

`begin`/`end` pairs (`render.home.begin` → `render.home.end`, drag begin → drop) always deliver the ending call to the same tweak that handled the beginning, even if it was removed in between, so you can always clean up.

`native-api.json` from your build is the authoritative list: each entry has the `point`, its JVM `descriptor` (argument and return types), the `fallback` and the `policy`. Exporting a name that isn't a real hook point isn't an error; it's just never called.

### All hook points (`winterx.native/1`)

Arguments are listed in order (`args[0]`, `args[1]`, …). "Used by" points to an official tweak whose source shows the hook in use.

**Settings**

| Point | Arguments → return | Policy | Notes |
| --- | --- | --- | --- |
| `settings.page` | `String page` → `E1.T6` | first | Build one of your Settings pages. See [Settings pages](#settings-pages) |
| `settings.tap` | `String page, String row` | all | A row `winterx-tw-r/<your-id>/<page>/<row>` was tapped |
| `settings.rows` | `List rows` | all | The root Settings rows list, for advanced additions |
| `settings.action` | `String rowId` (or `String, x1.i1`) | all | Older row-ID actions used by official tweaks; prefer `settings.tap` |
| `settings.handle` | `String rowId` → `Boolean` | or | Return `true` if you handled a row ID (used by ColoredBar) |

**Home drawing**

| Point | Arguments → return | Policy | Notes |
| --- | --- | --- | --- |
| `render.home.begin` | `Canvas, long time, E1.S1, E1.l4` → `Object` | first | Start of a Home frame. Return any object to take over the frame; it's passed back to `render.home.end`. Used by Animaper |
| `render.home.icon-context` | `E1.q6 icon, I1.b0` | all | The icon about to be drawn in this frame |
| `render.home.end` | `Object` | all | End of the frame, with your object from `begin` |
| `render.icon.begin` | `Canvas, E1.i6 profile, int, int` → `Integer` | first | Before one icon is drawn. Transform the canvas and return its save count (0 = untouched) |
| `render.icon.end` | `Canvas, int saveCount` | all | Restore after the icon |
| `home.draw-location` | `E1.i6, E1.c cell, int, int` → `M1.b` | first | Where an icon is drawn this frame (Animaper's page effects) |
| `render.icon-bitmap` | `E1.a app, Bitmap` → `Bitmap` | first | Replace an app's icon image (SnowyHome icon packs) |
| `render.badge-artwork` | `Map` → `Map` | first | Replace badge artwork (SnowyHome) |
| `render.hide-labels` | → `Boolean` | or | `true` hides icon labels |
| `render.custom-icons-enabled` | → `Boolean` | or | `true` while you're supplying icon bitmaps |
| `cache.tiles-allowed` | → `Boolean` | and | Return `false` to stop Spring caching Home tiles while you animate |
| `cache.folder-layers-allowed` | → `Boolean` | and | Same for folder layers |

**Home layout and dragging**

| Point | Arguments → return | Policy | Notes |
| --- | --- | --- | --- |
| `home.location` | `E1.i6, E1.c, int` → `M1.b` | first | Resting position of an icon |
| `home.edit-location` | `E1.O1, int, int` → `M1.b` | first | Position while editing |
| `home.animated-location` | `E1.O1, int, int` → `M1.b` | first | Position while icons animate in edit mode |
| `home.hover` | `E1.O1, float x, float y, int` → `E1.I1` | first | Drop target while dragging |
| `home.drag-begin` | `E1.O1, int, int` | all | A drag started |
| `home.before-drop` | `E1.O1` | all | A drag is about to drop |
| `home.pointer` | `x1.i1, int` | all | Pointer events on Home |
| `home.custom-grid-enabled` | → `Boolean` | first | `true` to use your own grid (FreeMe) |
| `home.entries` | `List, E1.i6, int page` → `List` | first | The icons placed on a page |
| `home.launch-location` | `x1.i1, E1.A0` → `M1.b` | first | Where the app-open animation starts |
| `home.delete-hit` | `x1.i1, float, float` → `String` | first | Which icon's delete badge was hit |
| `home.snapshot` | `x1.i1` → `JSONObject` | first | Read-only snapshot of Home |
| `home.move` | `x1.i1, JSONObject request` → `JSONObject` | first | Move an icon (FreeMe) |
| `folder.background-entries` | `E1.q6` → `List` | first | Entries drawn behind a folder |

**Dock**

| Point | Arguments → return | Policy | Notes |
| --- | --- | --- | --- |
| `dock.normalize-capacity` | `List` → `Integer` | first | How many dock slots (default at least 4). Used by DockIn |
| `dock.edit-capacity` | `E1.O1` → `Integer` | first | Dock slots while editing |
| `dock.geometry-enabled` | `x1.i1` → `Boolean` | first | `true` to use your own dock geometry |
| `dock.location` | `E1.i6, int, int` → `M1.b` | first | Position of a dock slot |
| `dock.hit` | `x1.i1, float, float` → `E1.A0` | first | Which dock icon was touched |
| `dock.delete-hit` | `x1.i1, float, float` → `String` | first | Which dock delete badge was hit |
| `dock.launch-size` | `x1.i1, String appId` → `Integer` | first | Icon size used for the open animation |
| `dock.hover` | `E1.O1, float, float, int, E1.i6` → `E1.I1` | first | Dock drop target while dragging |
| `dock.edit-location` | `E1.O1, int, int, E1.i6` → `M1.b` | first | Dock slot position while editing |
| `dock.motion-begin` | `E1.O1, E1.i6` | all | Dock animation started |
| `dock.frame` | `x1.i1, List, long time` | all | One dock animation frame |
| `dock.icon.begin-native` / `-motion` / `-legacy` | `Canvas, E1.q6, …` → `Integer` | first | Before a dock icon is drawn; return a canvas save count |
| `dock.icon.end` | `Canvas, int` | all | Restore after a dock icon |

**Apps, artwork, Messages and media**

| Point | Arguments → return | Policy | Notes |
| --- | --- | --- | --- |
| `app.observe` | `E1.q6` | all | An app is being shown (ColoredBar uses it to know which app is open) |
| `assets.app-bars` | `Map artwork, String appId` → `Map` | first | Replace an app's navigation-bar artwork |
| `assets.settings` | `Object, Object` → `Object` | first | Replace Settings artwork |
| `messages.list-button` | `E1.N0` → `E1.N0` | first | Replace the Messages list button (Message+) |
| `messages.pointer-down` / `-move` / `-up` | `x1.i1, float x, float y` → `Boolean` | first | Touches in Messages; `true` = consumed |
| `messages.pointer-cancel` | `LauncherActivity` | all | Touch cancelled |
| `media.photo-quality` | `int` → `Integer` | first | JPEG quality for sent photos |

## Settings pages

Settings pages use Spring's own native Settings models, so they look exactly like the rest of Settings.

**IDs.** With `settings_entry` set, your tweak appears under **WINTERX TWEAKS**. Opening it calls `settings.page` with your `settings_entry` value.

| ID | Meaning |
| --- | --- |
| `winterx-tw-p/<id>` | Your main page (`settings.page` receives `settings_entry`) |
| `winterx-tw-p/<id>/<page>` | Another page of yours (`settings.page` receives `<page>`) |
| `winterx-tw-r/<id>/<page>/<row>` | A tappable row. Tapping calls `settings.tap(page, row)` |

**Building a page**, following the official tweaks:

```java
// A tappable row (title, no link):
V6 row = Z3.g(Z3.a, "winterx-tw-r/" + id + "/main/add", "Add one", null, null, null, 0x18);
// A row that opens another of your pages (4th argument = page to open):
String sub = "winterx-tw-p/" + id + "/colours";
V6 link = Z3.g(Z3.a, sub, "Colours", sub, null, null, 0x18);
// A section: header, optional note, optional footer, null, rows.
W6 section = new W6("OPTIONS", null, "Footer text under the rows.", null, Arrays.asList(row, link));
// The page: its own ID, title, sections.
return new T6("winterx-tw-p/" + id, "My Tweak", Collections.singletonList(section));
```

There's no separate toggle or checkmark widget. The official tweaks show a selected choice by putting `✓ ` in front of the title. Always build the page from your current state. Don't rely on Spring redrawing the open page straight after a tap; going back and reopening it shows the new state.

## Saving data

Use `context.data("name.txt")` for your files. They live in `winterx-tweaks/<id>/data/` and **survive updates and removal**, so a reinstall picks up where the user left off. Good practice, as in Hello Native:

- write to a temporary file in the same folder, `sync`, then rename it over the real one,
- refuse symlinks (`Files.isSymbolicLink`) and validate what you read back,
- keep files small, and load them in `start` rather than on every `call`.

Don't write into Spring's own files (layouts, preferences) or other tweaks' folders.

## Features and dependencies

**`features`** announce what your tweak provides (for example `animation.page-effects`). At startup WinterX writes the features of every running tweak to `ruby/capabilities-v1.json`, which apps and tools such as Ruby can read to check whether something is available. Pick names under your own prefix.

**`requires`** lists other tweaks that must be installed first. Ruby refuses to install yours without them, refuses to remove a tweak something else needs, and refuses dependency cycles. At startup dependencies start first, and if a dependency fails or is removed, your tweak is switched off too.

Tweaks can't see each other's classes (each has its own classloader). To talk to a dependency, call a hook point it exports with `context.call(point, args, fallback)`.

## Artwork

Put PNG or JPEG files under `assets/` and reference them with `icon` and `previews` (up to 5). Ruby shows them on the package page.

## Bundling an app

A tweak can carry Spring apps (`.sapp` files) that are installed and removed together with it, such as a companion app for its settings or a utility it adds to Home.

1. Put each app in an `apps/` folder in your package: `apps/MyApp.sapp` (a normal Spring app archive with `app.json` and `main.js`).
2. List them in the manifest: `"apps": ["apps/MyApp.sapp"]`. The builder pins their hashes like every other file.

When the tweak is installed, WinterX hands each app to Spring's own installer, so it appears on Home the same way any imported app does. When the tweak is removed (or an update drops an app), the app is removed the next time Spring opens through WinterX. Its saved data in `sapps-data/` is kept, so reinstalling brings it back as it was.

Rules: up to 4 apps per package; each needs an `app.json` with an `id` (reverse-domain, lowercase) and a positive integer `build`; two apps in one package can't share an ID; and WinterX's own apps (Ruby, WinterX, IExplored) can't be replaced. Bundled apps need a WinterX core with the built-in package manager (`winterx-pm-v1`).

## Debugging

- **Switched off after an error.** If your tweak throws or returns the wrong type, it's disabled for the session, `stop()` is called, and the error is written to `winterx-tweaks/<id>/last-error.txt` in Spring's files folder. Spring behaves as if it weren't installed. Fix, rebuild, reinstall, reopen.
- **Logging.** Use `android.util.Log` with your own tag and read it with `adb logcat` (rooted Android) or Mac.APK's log.
- **Nothing happens.** Check that the point is in `exports`, spelled exactly as in `native-api.json`, that you reopened Spring through WinterX after installing, and that Safe Mode is off.
- **Wrong argument types.** Compare your casts with the descriptor in `native-api.json`.
- **Recovery.** Ruby's **Safe Mode** stops all tweak code from running; leave it and reopen Spring to load tweaks again.
- **Local checks** (macOS with Mac.APK, which provides the Java runtime these run Spring in). `python3 extensions/check.py out/core/core-engine.jar <folder-of-springys>` loads packages against the real converted engine (see the official packages for how the checks are written).

## Limits and rules

- Archive: 12 MiB compressed, 32 MiB expanded, 128 entries, 16 MiB per file, 128 KiB manifest, 256 KiB per source file.
- At most 128 exports, 32 features, 16 dependencies, and 16 native tweaks installed at once.
- Your classes can't use reserved package names (`android.*`, `java.*`, `winterx.*`, Spring's packages, …) and can't contain the official tweaks' classes.
- The source must be included and must build the code that's shipped. Links, directories, encrypted entries and undeclared files are refused, and every file's hash is checked before install.
- Install, update and remove only take effect after Spring is reopened through WinterX.

## Publishing

1. Publish your source publicly (the `source` URL).
2. Put your `.springys` files and an `index.json` on any static HTTPS host:

   ```json
   {
     "format": "winterx.repository/1",
     "name": "My Repository",
     "packages": [
       { "url": "packages/hello-1.0.0.springys", "sha256": "<64 lowercase hex characters>" }
     ]
   }
   ```

3. Users add the `index.json` URL in Ruby under **Sources → Add Source…**.

Use versioned filenames and update the hash whenever you rebuild. Ruby reads the name, description, author and artwork from the package itself. Full details are in [Creating a Ruby repository](repository-design.md).

## JavaScript tweaks

There's also a simpler JavaScript format (`winterx.springys/2`). It runs in an isolated QuickJS worker per tweak and has a much narrower API: declarative Settings pages with buttons and toggles, alerts, saved state/files, and an experimental Home snapshot/move API. It **can't** use hook points, draw, or change layouts beyond that. Use it for small utilities; use Java for anything that changes how Spring looks or behaves. See [the JavaScript tweak runtime](tweak-runtime-design.md) and `examples/code-tweak/`. JavaScript tweaks haven't been tested live on rooted Android yet.
