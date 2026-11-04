# Making `.springys` packages

`.springys` is Ruby's experimental package format for WinterX. It is a ZIP archive containing a manifest, optional artwork and (in v2) JavaScript. It is different from Spring's `.sapp` app format and from a Debian `.deb`.

**Two experimental formats:** v1 selects a **hook already implemented by the installed WinterX engine**; inventing a hook does not create behaviour. V2 contains independently authored JavaScript using the [documented WinterX runtime API](tweak-runtime-design.md). Basic v2 execution is live-confirmed on Mac.APK, but limits and recovery still need live checks. Older engines cannot install v2. Native libraries and shell scripts are unsupported in both formats.

## What you need

- A checkout of [WinterX](../README.md) and Python 3, run from the checkout's root directory. Building and inspecting packages uses only Python's standard library.
- To try a package in Ruby, a compatible WinterX-jailbroken Spring 0.8.1 installation on Mac.APK, Ruby, and the running Ruby bridge. Follow the [installation guide](../README.md). Rooted Android is not supported yet.
- Optional: PNG or JPEG artwork that you have permission to distribute. Pillow is required by the bridge to generate list thumbnails; see the main install guide.

## 1. Create your package folder

The following example wraps the built-in `test.settings` hook. It adds the existing Ruby Test entry in Spring Settings; it does not implement a new Settings feature. From the WinterX checkout:

```sh
mkdir -p my-first-tweak/assets
cp examples/settings-test/assets/icon.png my-first-tweak/assets/icon.png
```

Create `my-first-tweak/manifest.json` in your editor with this content:

```json
{
  "format": "winterx.springys/1",
  "id": "me.example.first-tweak",
  "name": "My First Tweak",
  "version": "1.0.0",
  "author": "Example",
  "description": "Shows the existing Ruby Test entry in Spring Settings.",
  "hook": "test.settings",
  "icon": "assets/icon.png",
  "previews": []
}
```

Replace the name, author and ID with your own. Use a unique ID you control; for example, a reverse-domain name. Your folder should contain:

```text
my-first-tweak/
├── manifest.json
└── assets/
    └── icon.png
```

To add screenshots, put them in `assets/` and reference them in `previews`, for example `"previews": ["assets/screenshot-1.png", "assets/screenshot-2.jpg"]`. Replace the example icon with your own artwork. Only referenced files are packed; spelling and capitalization must match.

## 2. Build and check the archive

```sh
python3 tools/springys_tool.py build my-first-tweak /tmp/my-first-tweak-1.0.0.springys
python3 tools/springys_tool.py inspect /tmp/my-first-tweak-1.0.0.springys
```

The build command prints normalized metadata and the SHA-256. The inspector reads the finished archive, validates it, and prints its metadata. The builder refuses to overwrite an existing output: choose a new filename or deliberately remove your own old output first. Keep the source folder as well as the archive so you can make future versions.

A successful inspection proves the archive format is valid; it does **not** prove your installed WinterX build supports the named hook or that its behavior works on your device.

## 3. Try it in Ruby

1. Start the Ruby bridge and jailbreak Spring using WinterX. Open Ruby.
2. Open **Packages → Local Packages → Import Package…**, select your `.springys` file, and use **Refresh** if the imported list does not update. File-picker behavior can depend on the Spring/Mac.APK setup.
3. Select the package in **Imported**, review its information, and tap **Install**. Reopen Ruby after a restart if Spring asks for one. On Mac.APK, a stuck loading screen may require fully quitting and reopening Spring Launcher.
4. Open Spring's **Settings** and look for **Ruby Test**. If the Settings test was previously enabled independently in Ruby, remove that manually enabled test first: the package manager prevents taking ownership of an existing marker.
5. To remove the package, return to **Packages → Local Packages**, select it under **Installed**, and tap **Remove**. Changes to some hooks may restart Spring.

The import and package workflows are experimental and have not all been verified end-to-end in Spring. If a request stays pending, check that the bridge is running; its terminal reports failures.

## 4. Make an update

Keep the **same `id`** when updating a package. Change `version` (for example `1.0.0` to `1.1.0`), edit its description/artwork as appropriate, and build to a new filename:

```sh
python3 tools/springys_tool.py build my-first-tweak /tmp/my-first-tweak-1.1.0.springys
python3 tools/springys_tool.py inspect /tmp/my-first-tweak-1.1.0.springys
```

Import the new archive and open it under **Imported**; Ruby can show an **Update** action when the installed package has the same ID and a different archive hash. Registry updates are identified by ID and content hash; the current code does not compare versions to decide which one is newer. Do not assume version numbers prevent a downgrade. Remove the installed package through Ruby when it is no longer wanted.

To share packages through an HTTPS source, follow [Creating a Ruby repository](repository-design.md).

## Write your own code (v2)

Unlike the v1 example above, this package implements its own Settings action. Create `my-code-tweak/manifest.json`:

```json
{
  "format": "winterx.springys/2",
  "type": "tweak",
  "id": "me.example.my-code-tweak",
  "name": "My Code Tweak",
  "version": "1.0.0",
  "author": "Example",
  "description": "A native Settings action implemented by this package.",
  "entry": "tweak/main.js",
  "settings": {
    "main": {
      "title": "My Code Tweak",
      "sections": [{
        "rows": [{"id": "hello", "type": "button", "title": "Say Hello"}]
      }]
    }
  }
}
```

Create `my-code-tweak/tweak/main.js`:

```js
WinterX.on("settingsTap", function (page, row) {
  if (page === "main" && row === "hello") {
    WinterX.alert({title: "Hello", message: "This is my own code.", buttons: ["OK"]});
  }
});
```

Build and inspect with the same commands as v1, using your new folder and a new output filename. Install through Ruby on a checksum-verified **running runtime-capable engine**, then deliberately fully quit and reopen Spring. The installer stages the code; it never automatically restarts the launcher. Open **Settings → My Code Tweak → Say Hello**. A newly installed or updated script runs on the next full engine launch, not merely when Ruby is reopened.

See [`examples/code-tweak`](../examples/code-tweak/) for nested pages, toggles, state/data and an alert Promise callback, and the [runtime API](tweak-runtime-design.md) for supported calls and limits. Developer examples are source-only, not entries in the built-in repository. There is no arbitrary home-icon manipulation API yet.

## Manifest reference

`manifest.json` must be a UTF-8 JSON object. Duplicate keys are rejected. The formats are `winterx.springys/1` and `winterx.springys/2`. Both use the common metadata below.

| Field | Required | Rules and purpose |
| --- | --- | --- |
| `format` | Yes | `winterx.springys/1` (compiled hook) or `winterx.springys/2` (code). |
| `id` | Yes | Up to 120 characters. Lowercase letters and digits in groups separated by `.` or `-`, with at least one separator; e.g. `me.example.clock`. Keep it stable across updates. |
| `name` | Yes | Nonempty display name, at most 80 characters. |
| `version` | Yes | Up to 64 characters; two to four dot-separated numeric components, optionally followed by one `-` or `+` suffix using letters, digits, dots or hyphens. Examples: `1.0`, `1.2.3-beta.1`. |
| `author` | Yes | Nonempty display name, at most 120 characters. |
| `description` | Yes | Nonempty plain text, at most 4,000 characters. |
| `hook` | V1 only | Required for v1; forbidden in v2. Lowercase compiled hook identifier, up to 120 characters. |
| `icon` | No | A referenced PNG or JPEG path under `assets/`, or `null`. Ruby makes a 64 × 64 thumbnail for lists. |
| `previews` | No | An array of zero to five PNG/JPEG paths under `assets/`, displayed on the package detail page. Defaults to `[]`. |

Text fields cannot contain NUL characters or consist only of whitespace. Unknown manifest keys are currently ignored; do not depend on them to change behavior.

### V2 fields and Settings schema

- `type` must be `"tweak"`; `entry` must be `"tweak/main.js"`. That file must contain nonempty UTF-8 JavaScript, no NUL, at most 256 KiB. There are no arbitrary extra scripts or native libraries.
- `settings` is optional. If present, it must have `main`, and may have a `pages` object of additional named pages. At most 20 pages total; `pages` cannot redefine `main`.
- Each page may have `title` (at most 60 characters) and must have 1–40 `sections`. A section may have `id` and `title`, and needs 1–40 `rows`. Keep pages short enough to remain usable.
- Each row requires a page-unique `id`, nonempty `title` (at most 60 characters), and `type`: `button`, `toggle` or `page`. A `page` row also needs `page`, pointing to an existing page ID.
- Page/section/row IDs use lowercase letters, digits and hyphens, 1–40 characters. The native Settings UI handles navigation. Buttons/toggles dispatch `settingsTap`; toggle values persist as `"on"`/`"off"` in `WinterX.state.get().settings[page + "/" + row]`.

### Hooks in this experimental code

| Hook | Existing behavior | Notes |
| --- | --- | --- |
| `test.settings` | Ruby Test entry in Spring Settings | Requires a compatible patched engine; may restart Spring. |
| `test.colors` | Navigation-bar color test | Requires the local theme assets generated from the user's own Spring APK and a compatible engine. |
| `test.icons` | Free icon placement test | Requires a compatible engine; affects home-screen placement. |
| `tweak.animaper` | Home-screen page animation | Requires compatible hooks in the checksum-verified running engine. |
| `tweak.coloredbar` | Presets, exact RGB and app exclusions | Preferences are in Spring Settings; updated engines always exclude Ruby. |
| `tweak.freeme` | Sparse normal-grid cells and cross-page placement | Unlisted draft; requires `freeme-grid-v1` in the verified running engine. |
| `tweak.dockin` | Native 4–7-icon dock, default/minimum 4 | Unlisted draft; requires `dockin-native-v1`, motion and app-launch hooks. |

These are development hooks, not a stable public API. FreeMe/DockIn's packaged checks do not establish live correctness; see [layout development](layout-tweaks.md). Their live-marker installs/removals do not restart Spring or erase saved layout/preferences. Ruby's special `app.iexplored` handling is not a general-purpose `.springys` app installer. A v1 manifest cannot ship new code; use v2 for independent Settings behaviour. Generic home-screen/animation extensions still require engine development. Developer examples, layout drafts and the three test hooks are not published in the working built-in index.

## Artwork and archive limits

- Artwork paths start with `assets/`, end in `.png`, `.jpg`, or `.jpeg`, and cannot contain empty, `.` or `..` path components. Path and filename case matter.
- Use real PNG or JPEG files. PNG dimensions must each be between 1 and 4,096 pixels. Each artwork file must be nonempty and at most 2 MiB.
- V1 contains only `manifest.json` and referenced images; v2 also requires `tweak/main.js`. At most 20 entries, 12 MiB compressed, 24 MiB expanded, and a 128 KiB manifest. There can be at most five previews.
- Directory entries, symlinks, encrypted entries, duplicate archive names, and ZIP compression other than stored or deflate are rejected. Use the included builder to create a compatible archive.
- If creating a ZIP manually, put `manifest.json` at the archive root, include no directory entries, and run `inspect` on the result. Renaming an arbitrary ZIP to `.springys` does not make it valid.

## Troubleshooting

- **`Output already exists`:** build to a new filename.
- **`Invalid package ID, version or hook`:** check the identifier and version syntax above and remove uppercase characters from ID/hook.
- **Undeclared files:** remove extra ZIP files or fix artwork paths. The builder packs referenced artwork and the declared v2 entry only.
- **Invalid image or missing artwork:** check the file exists, its extension matches its actual format, its size is within limits, and the manifest's case matches.
- **Unsupported hook:** the archive is valid but this WinterX installation does not implement the requested behavior. Use a supported hook and engine; inventing a hook name does not install code.
- **Existing tweak already enabled:** remove the independently enabled test in Ruby before installing its package equivalent.
- **Bridge unavailable or operation pending:** restart the Ruby bridge, confirm Spring is jailbroken, and review the bridge terminal. Don't assume an interrupted operation succeeded.
- **Nothing changes after installing:** confirm installation and engine support, and that Safe Mode is off. V2 requires a deliberate full launcher reopen; inspect `last-error.txt` and runtime logs for failures. The built-in ColoredBar archive cannot upgrade engine hooks on its own.

The project is a beta. Back up Spring data before experimenting, and add repositories only from authors you trust.
