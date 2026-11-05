# Message+ — unlisted development tweak

Message+ targets **Spring 0.8.1 Messages**, not WhatsApp. It replaces only the main conversation list's left **Edit** button with **Settings**, presenting Spring's native alert-based settings. It also adds **Message+** in native **Settings → WINTERX TWEAKS**. Thread buttons and unrelated apps retain native routing.

## Implemented

- JPEG photo quality: **65** (smaller), **85** (stock), **95** (higher). This changes the existing Messages photo processor only; existing resizing/size limits and original photos remain unchanged.
- Native button/header models, scaled hit geometry, drag-out/reentry and cancelled-touch handling. Unrelated gestures fall through to Spring.
- Persistent quality at `files/ruby/messageplus/photo-quality`; only the three bounded values are accepted. Linked/malformed storage falls back to stock. Removal preserves preferences; Safe Mode restores stock and refuses changes.
- Unlisted package `com.winterx.messageplus`, hook `tweak.messageplus`. The Mac bridge requires a checksum-verified running engine with ABI `messageplus-settings-photo-v1` **and actual native calls**. Marker updates require no restart on a compatible engine.

**Video sending and reactions are not implemented.** The actual Messages REST/WebSocket transport has not established those payloads or rendering paths. The Settings copy explicitly reports them unavailable; no pretend reaction, unsupported upload or message is sent. WhatsApp's separate MP4 handling is not evidence of Messages support.

## Separate build and checks

The selected reviewed batch2 includes these hooks, and Message+ was enabled by explicitly authorized stopped-session preparation. A live report found the UI missing despite the correct engine and marker: its path guard rejected Mac.APK's legitimate shared-data alias. The correction canonicalizes only the platform-supplied files root and still refuses redirects beneath it. It is in a separate, unselected UI-fix candidate; the running reviewed engine is not hot-patched. See [development status](development-status.md).

Source build opt-in: `WINTERX_BUILD_MESSAGEPLUS=1` alongside the normal build flags. Build to a new filename and do not replace/select an engine in use.

```sh
python3 tools/springys_tool.py build builtin-repo/sources/messageplus builds/MessagePlus-dev.springys
python3 patches/tests/check_messageplus.py path/to/converted-engine.jar --packaged
```

The checker verifies real packaged button/header models, both iOS 4/6 root rows, native Settings routing and pointer entries, quality bounds, Safe Mode/removal and child-link refusal, with an **alert/application spy**. It runs against both direct and aliased platform files roots; the original reviewed build passes the direct case but fails the alias regression. It does not start Spring or send anything. Live visual fit, concurrent alerts, Settings redraw and photo delivery remain unverified. Message+ stays outside working catalogues until those checks and real transport enhancements are complete.
