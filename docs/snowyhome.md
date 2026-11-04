# SnowyHome — unlisted development tweak

SnowyHome implements **icon packs, badge colours, hidden icon labels and corner controls** using Spring 0.8.1's native Settings. It is not in the working catalogue and has not been installed or live-tested.

## Engine and readiness

- Requires a verified **running** engine with `snowyhome-render-v1` and the actual renderer hooks. Helpers alone are not enough. The prepared **alpha8-local does not support SnowyHome**; its APK, selection and backup remain unchanged.
- A separate local experimental engine was built and converted to 5,195 classes. Packaged-helper bitmap tests, real icon-resolver and native Settings-controller routing, and JVM bytecode verification passed. These checks do **not** start Spring or establish visible pointer/folder/dock/launch behaviour or Android compatibility.
- `builtin-repo/sources/snowyhome/manifest.json` is an unlisted v1 compiled-hook draft, not an executable third-party example. Compatible Mac.APK installs/removals change only the live marker; they do not restart Spring or erase preferences, packs, saved pages or FreeMe cells. Incompatible engines refuse the request.

Build a **new, separate** engine from the exact original APK and documented local dependencies:

```sh
WINTERX_BUILD_ANIMAPER=1 WINTERX_BUILD_TRUSTED_FILES=1 WINTERX_BUILD_INBOX=1 \
  WINTERX_BUILD_SNOWYHOME=1 python3 patches/icon_positions/build.py \
  Spring-0.8.1.apk builds/WinterXSpring-snowy-experimental.apk
```

This builds only. Do not replace an engine in use, change the prepared alpha8 selection, or start a second Spring process. No patched APK is distributed, and the unsigned output must not be installed as an Android update.

## Native controls

**Settings → Tweaks → SnowyHome** has:

- **Icon Pack:** Stock Icons or a locally exported, verified revision.
- **Badge Colour:** stock/red/blue/green/purple/orange/graphite. White glyphs, highlights, transparent margins, alpha and badge dimensions are preserved.
- **Icon Corners:** stock/square/subtle/rounded/soft/circle. A square mask cannot recreate opaque corners already missing from stock artwork; use square pack artwork when needed.
- **Hide Icon Labels:** suppresses drawing, not app names or memberships.

Safe Mode immediately uses stock drawing and refuses preference actions. Removal preserves `ruby/snowyhome/preferences.json` and `ruby/snowyhome/packs/`. Settings changes use the existing native layout action/redraw dispatch; visible redraw remains a live-test item.

## Author an icon pack

Install Pillow as documented in the main README. Make a local directory containing `manifest.json` and square, single-frame PNGs in `icons/`. Example source manifest:

```json
{
  "format": "winterx.iconpack/1",
  "id": "me.example.myicons",
  "name": "My Icons",
  "author": "Example Author",
  "version": "0.1.0",
  "icons": {
    "mail": {"file": "icons/mail.png"},
    "sapp:me.example.app": {"file": "icons/example.png"}
  }
}
```

Map actual Spring app IDs, not display names. Native folders (`folder:*` and `folder-utilities`) cannot be replaced. Multiple app IDs can intentionally share one image. The builder fills in each file's SHA-256; the packed manifest requires it.

```sh
python3 tools/iconpack_tool.py build my-icon-source my-icons.zip
python3 tools/iconpack_tool.py inspect my-icons.zip
python3 tools/iconpack_tool.py export my-icons.zip my-export
```

Outputs must be new. Export creates `my-export/<package-sha256>/` with a pinned manifest and icons. **It does not install or select the pack, connect to a device, or write to Spring's private folder.** For an explicitly authorized developer trial, back up data and copy the exported revision into `files/ruby/snowyhome/packs/` using verified private-folder access, then choose it in Settings on a compatible engine. There is no Ruby pack-import UI or portable pack installer yet. Do not use the inventory bridge or its transaction allowlist to bypass this limitation.

Limits: 1–128 app mappings, 16 MiB archive, 32 MiB expanded bytes, 64 KiB manifest, 1 MiB per icon, square PNG dimensions 16–1024 px. Links, path traversal, executable/unreferenced files, duplicate/case-colliding filenames, Windows reserved filenames, checksum mismatches and animated PNGs are refused by the authoring validator. Native loading checks bounded files, PNG structure/CRC/dimensions and checksums before decoding. Checksums provide integrity, not author trust or a hardened sandbox.

## Rendering and checks

The icon resolver returns a private same-size bitmap copy. Native folder composites and shared source artwork remain stock; missing/invalid mapped images fall back to the original. Corner masks apply only to app-icon copies. Badge artwork uses a read-only map view and copied pixels. Own copies are cached with a 16 MiB/128-entry bound and are not recycled while Spring may still display them. Native precomposed label/badge artwork is bypassed, never cleared, while SnowyHome is active. No page JSON, hit geometry or app model is rewritten.

```sh
python3 tools/check_source_tests.py
python3 patches/tests/check_snowyhome.py /path/to/converted-experimental.jar --packaged
python3 patches/tests/check_engine_hooks.py /path/to/converted-experimental.jar
```

Without `--packaged`, the SnowyHome runner overlays current sources; that is **not** evidence that the chosen APK includes them. Live tests must still check home/dock/edit/folder transitions, native caches and dynamic icons, Settings refresh, Safe Mode, removal and interaction with FreeMe/DockIn/Animaper.
