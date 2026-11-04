# SnowyHome — unlisted development tweak

SnowyHome implements **icon packs, badge colours, hidden icon labels and corner controls** using Spring 0.8.1's native Settings. Its draft was installed/enabled with DockIn and FreeMe for the selected local test, without launching Spring during preparation. It is not in the working catalogue; complete live UI validation remains outstanding.

## Engine and readiness

- Ordinary Ruby operations require a verified **running** engine with `snowyhome-render-v1` and actual renderer hooks. Helpers alone are not enough. The narrowly scoped combined-test preparer can activate the three checksum-pinned home drafts only while Spring is stopped and after a fresh backup.
- The selected experimental2 engine has 5,195 converted classes; an earlier read-only check matched its sole process and checksum/receipt. The latest check found Spring closed; a retained receipt is not a live-engine guarantee. **This engine does not include the newer private-inbox import.** The separate, unselected batch2 includes import/home APIs/optional SSH/Message+ and converted to 6,979 classes. Packaged bitmap/icon-resolver/native Settings and import-preservation checks pass; they do **not** establish visible pointer/folder/dock/launch behaviour or Android compatibility. See [development status](development-status.md).
- `builtin-repo/sources/snowyhome/manifest.json` is an unlisted v1 compiled-hook draft, not an executable third-party example. Compatible Mac.APK installs/removals change only the live marker; they do not restart Spring or erase preferences, packs, saved pages or FreeMe cells. Incompatible engines refuse the request.

Build a **new, separate** engine from the exact original APK and documented local dependencies:

```sh
WINTERX_BUILD_ANIMAPER=1 WINTERX_BUILD_TRUSTED_FILES=1 WINTERX_BUILD_INBOX=1 \
  WINTERX_BUILD_SNOWYHOME=1 python3 patches/icon_positions/build.py \
  Spring-0.8.1.apk builds/WinterXSpring-snowy-experimental.apk
```

This builds only. Do not replace an engine in use, silently change the selected combined test, or start a second Spring process. No patched APK is distributed, and the unsigned output must not be installed as an Android update.

## Native controls

**Settings → Tweaks → SnowyHome** has:

- **Icon Pack:** Stock Icons or a verified revision; newer engines also offer **Import Icon Pack** from the private inbox.
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

Outputs must be new. Export creates `my-export/<package-sha256>/` with a pinned manifest and icons. **It does not install or select the pack, connect to a device, or write to Spring's private folder.** For an explicitly authorized trial, back up current data and use verified private-folder access. On the selected experimental2, copy the exported revision into `files/ruby/snowyhome/packs/`, then choose it in Settings.

On newer import-capable engines, copy the ZIP into `files/ruby/snowyhome/inbox/`, then open **SnowyHome → Icon Pack → Import Icon Pack** and select its name. Import runs on a worker and updates its status; return to/reopen the native page to see completion and select the verified revision. It publishes a checksum-named revision without selecting it, deleting the source ZIP or replacing an existing revision—even if that existing revision is invalid. Preferences, layouts and other packs stay unchanged. The inbox scan is limited to 32 entries and accepts bounded, simple ZIP filenames. Automatic completion redraw is not live-verified.

There is no Ruby icon-pack picker or portable pack installer. The portable inventory/transaction processor must not be used to bypass its write allowlist. A current batch2 build on disk is not evidence that the selected/running engine supports import.

Limits: 1–128 app mappings, 16 MiB archive, 32 MiB expanded bytes, 64 KiB manifest, 1 MiB per icon, square PNG dimensions 16–1024 px. Links, path traversal, executable/unreferenced files, duplicate/case-colliding filenames, Windows reserved filenames, checksum mismatches and animated PNGs are refused by the authoring validator. Native loading checks bounded files, PNG structure/CRC/dimensions and checksums before decoding. Checksums provide integrity, not author trust or a hardened sandbox.

## Rendering and checks

The icon resolver returns a private same-size bitmap copy. Native folder composites and shared source artwork remain stock; missing/invalid mapped images fall back to the original. Corner masks apply only to app-icon copies. Badge artwork uses a read-only map view and copied pixels. Own copies are cached with a 16 MiB/128-entry bound and are not recycled while Spring may still display them. Native precomposed label/badge artwork is bypassed, never cleared, while SnowyHome is active. No page JSON, hit geometry or app model is rewritten.

```sh
python3 tools/check_source_tests.py
python3 patches/tests/check_snowyhome.py /path/to/converted-experimental.jar --packaged
python3 patches/tests/check_engine_hooks.py /path/to/converted-experimental.jar
```

Without `--packaged`, the SnowyHome runner overlays current sources; that is **not** evidence that the chosen APK includes them. Live tests must still check home/dock/edit/folder transitions, native caches and dynamic icons, Settings refresh, Safe Mode, removal and interaction with FreeMe/DockIn/Animaper.
