# WinterX `.springys` packages — draft version 1

A `.springys` package is a ZIP containing `manifest.json` and, optionally, the images that its manifest references. It is separate from Spring's `.sapp` app format. This format is experimental.

```text
example.springys
├── manifest.json
└── assets/
    ├── icon.png
    ├── preview-1.png
    └── preview-2.jpg
```

```json
{
  "format": "winterx.springys/1",
  "id": "me.example.settings-test",
  "name": "Settings Button Test",
  "version": "1.0.0",
  "author": "Example",
  "description": "Adds a test button to Spring Settings.",
  "hook": "test.settings",
  "icon": "assets/icon.png",
  "previews": ["assets/preview-1.png", "assets/preview-2.jpg"]
}
```

`id` is a stable, lowercase, reverse-domain-style package identifier. Keep it unchanged for updates. `version` is a dotted numeric version with an optional prerelease/build suffix. `description` is plain text; `icon` is optional; `previews` contains up to five optional PNG/JPEG images. The name and artwork are for display in Ruby.

`hook` identifies a tweak implementation provided by the installed WinterX engine. The manifest is declarative: version 1 does not run shell scripts, native binaries, JavaScript or arbitrary package code. A package that names a hook the installed engine does not implement must not be marked installed. This means authors cannot yet add new behavior simply by choosing a new hook. A future extension mechanism needs its own design and testing.

Limits: 12 MB compressed, 24 MB expanded, 16 ZIP entries and 2 MB per image. Artwork paths must be inside `assets/`, must be referenced by the manifest, and cannot contain `.` or `..` path components. Directories, links, encrypted ZIP entries and duplicate entries are rejected. Images must be PNG or JPEG. ZIP contents are validated before installation. A repository-provided SHA-256 must match the downloaded package.

The local `tools/springys.py` validator implements these package and artwork checks. Ruby includes experimental local and repository package browsing and install, update, and removal integration for supported hooks. Repository support has automated tests but needs live testing; this is not yet a stable specification. See [Creating a Ruby repository](repository-design.md).

## Building a local draft package

Use the included `examples/settings-test` directory as a starting point. Edit the manifest and artwork, then run:

```sh
python3 tools/springys_tool.py build examples/settings-test /tmp/settings-test.springys
python3 tools/springys_tool.py inspect /tmp/settings-test.springys
```

The builder validates the resulting archive and refuses to overwrite an existing file. This is a package authoring tool. Ruby can import a package locally through Packages → Local Packages; this path still needs live testing. Only hooks built into WinterX can have behavior, so the example cannot be used to write arbitrary new tweaks.

The included Settings test package uses the same hook as the original built-in test. If that test is already installed manually, remove it from the built-in test page before installing the `.springys` version. This prevents package removal from accidentally deleting an independently installed tweak.
