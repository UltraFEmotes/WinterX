# Animaper and Barrel

Animaper keeps its original eight effects—Wave, Cascade, Bounce, Orbit, Ripple, Columns, Fan and Zigzag—and adds **Barrel** on compatible Spring **0.8.1** engines. The default remains Wave. Upgrading, opening Settings or enabling the tweak does not replace a saved selection.

## Selecting Barrel

Enable Animaper, then open its page in **Spring Settings → Animaper** and select **Barrel**. Changes apply on the next home redraw; no respring is needed. Safe Mode/removal suppresses the effect and preserves `files/ruby/animaper.mode` and all saved layouts.

Barrel needs both native drawing wrappers and `animaper-barrel-v1`. New Settings pages omit it when those wrappers are absent. Ruby **1.9** also checks the runtime capability receipt before offering or saving Barrel; older Ruby versions still offer the original eight choices. The new engine retains the trusted-script hashes for Ruby 1.4–1.8, so existing installed Ruby apps keep working. Ruby 1.9's source/build number and hash are separate; updating the engine does not install that app automatically.

## Rendering

Barrel projects each icon's actual sparse-grid centre onto a rotating vertical cylinder. Depth and the local surface angle change horizontal/vertical scale as well as position. It is not a renamed positional Wave effect. Icon artwork, label, shadow and badge share the Canvas transform.

The native page scroll remains authoritative. Each frame uses the real page index, Spring's page offset and the current grid geometry; it does not assume a dense four-column page. Settled/offscreen frames are identity transforms. The effect is restricted to normal home-page drawing; dock, open-folder, edit and native launch/close transforms stay on their native paths.

The frame owns its Canvas state. Nested frames, foreign canvases and other threads cannot reuse its icon context; normal and exception exits restore Canvas/context state. Incompatible precomposed native tiles are bypassed at production and consumption while Barrel is active. Existing retained cache contents and all app models/page files/saved cells are preserved.

## Verification

```sh
python3 patches/icon_positions/check.py
python3 patches/tests/check_animaper.py path/to/converted-engine.jar
python3 patches/tests/check_renderer_transitions.py path/to/converted-engine.jar
```

The packaged checks use real converted native drawing and Mac.APK Bitmap/Canvas with disposable direct/aliased files roots and both native variants. They include two-page sparse four/six-column pixel references, native exceptions, nested/foreign/thread contexts, Settings selection, Safe Mode/removal and file/artwork preservation. They never launch Spring or select an effect in the user's session. Actual visible motion still needs a user-controlled local trial; Android compatibility is not established by these checks.
