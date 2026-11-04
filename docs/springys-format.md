# Making `.springys` packages

`.springys` is Ruby's experimental package format for WinterX. It is a ZIP archive containing a manifest and optional artwork. It is different from Spring's `.sapp` app format and from a Debian `.deb`.

**Current limitation:** a package cannot contain executable tweak code. A manifest selects a **hook already implemented by the installed WinterX engine**. Making a package with a new hook name does not create a new tweak; the validator may accept the archive, but Ruby will reject the install if the engine/bridge does not support the hook. Scripts, JavaScript, native libraries, and other files cannot be included. The package format and workflow can change during beta.

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

## Manifest reference

`manifest.json` must be a UTF-8 JSON object. Duplicate keys are rejected. The exact format string is `winterx.springys/1`.

| Field | Required | Rules and purpose |
| --- | --- | --- |
| `format` | Yes | Must be `winterx.springys/1`. |
| `id` | Yes | Up to 120 characters. Lowercase letters and digits in groups separated by `.` or `-`, with at least one separator; e.g. `me.example.clock`. Keep it stable across updates. |
| `name` | Yes | Nonempty display name, at most 80 characters. |
| `version` | Yes | Up to 64 characters; two to four dot-separated numeric components, optionally followed by one `-` or `+` suffix using letters, digits, dots or hyphens. Examples: `1.0`, `1.2.3-beta.1`. |
| `author` | Yes | Nonempty display name, at most 120 characters. |
| `description` | Yes | Nonempty plain text, at most 4,000 characters. |
| `hook` | Yes | Up to 120 characters. Lowercase hook identifier such as `test.settings`; it must be implemented by the receiving WinterX version. |
| `icon` | No | A referenced PNG or JPEG path under `assets/`, or `null`. Ruby makes a 64 × 64 thumbnail for lists. |
| `previews` | No | An array of zero to five PNG/JPEG paths under `assets/`, displayed on the package detail page. Defaults to `[]`. |

Text fields cannot contain NUL characters or consist only of whitespace. Unknown manifest keys are currently ignored; do not depend on them to change behavior.

### Hooks in this experimental code

| Hook | Existing behavior | Notes |
| --- | --- | --- |
| `test.settings` | Ruby Test entry in Spring Settings | Requires a compatible patched engine; may restart Spring. |
| `test.colors` | Navigation-bar color test | Requires the local theme assets generated from the user's own Spring APK and a compatible engine. |
| `test.icons` | Free icon placement test | Requires a compatible engine; affects home-screen placement. |
| `tweak.animaper` | Home-screen page animation | Only offered by the bridge if it detects Animaper hooks in the configured engine. |

These are development hooks, not a stable public API. Ruby also has special app handling for IExplored; its `app.iexplored` entry should not be treated as a general-purpose `.springys` app installer. The bridge and engine must both support a hook. See `tools/ruby_bridge.py`, `tools/ruby_packages.py`, and `patches/icon_positions/` for the implementation. To create genuinely new behavior today, a developer must change and rebuild WinterX itself; the rebuilt engine and bridge would need to be installed by each user. A custom manifest alone cannot ship that code.

## Artwork and archive limits

- Artwork paths start with `assets/`, end in `.png`, `.jpg`, or `.jpeg`, and cannot contain empty, `.` or `..` path components. Path and filename case matter.
- Use real PNG or JPEG files. PNG dimensions must each be between 1 and 4,096 pixels. Each artwork file must be nonempty and at most 2 MiB.
- The package can contain only `manifest.json` and its referenced images. At most 16 entries, 12 MiB compressed, 24 MiB expanded, and a 128 KiB manifest. There can be at most five previews.
- Directory entries, symlinks, encrypted entries, duplicate archive names, and ZIP compression other than stored or deflate are rejected. Use the included builder to create a compatible archive.
- If creating a ZIP manually, put `manifest.json` at the archive root, include no directory entries, and run `inspect` on the result. Renaming an arbitrary ZIP to `.springys` does not make it valid.

## Troubleshooting

- **`Output already exists`:** build to a new filename.
- **`Invalid package ID, version or hook`:** check the identifier and version syntax above and remove uppercase characters from ID/hook.
- **`Package must contain only the manifest and its referenced artwork`:** remove extra ZIP files or fix artwork paths. The builder includes only referenced files.
- **Invalid image or missing artwork:** check the file exists, its extension matches its actual format, its size is within limits, and the manifest's case matches.
- **Unsupported hook:** the archive is valid but this WinterX installation does not implement the requested behavior. Use a supported hook and engine; inventing a hook name does not install code.
- **Existing tweak already enabled:** remove the independently enabled test in Ruby before installing its package equivalent.
- **Bridge unavailable or operation pending:** restart the Ruby bridge, confirm Spring is jailbroken, and review the bridge terminal. Don't assume an interrupted operation succeeded.
- **Nothing changes after installing:** confirm the package is listed as installed, the hook matches the engine, and Safe Mode is off. Some changes require restarting Spring; check the bridge output.

The project is a beta. Back up Spring data before experimenting, and add repositories only from authors you trust.
