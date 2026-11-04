# FreeMe and DockIn development

These are **unfinished Spring 0.8.1 tweaks**, not working catalogue entries. The published built-in catalogue still contains only Animaper and ColoredBar. No FreeMe or DockIn package was installed during these checks.

## FreeMe

FreeMe places home icons in Spring's normal grid cells rather than arbitrary pixel coordinates. Its separate `files/ruby/freeme-slots-v1.json` stores sparse cells; it never migrates the old `icon-positions-v1.json` or directly rewrites Spring's page JSON.

Implemented hooks cover home drawing, tapping, launch origins, edit positions, hover targets and delete badges. Same-page, cross-page and new-page drops snap to empty cells. A collision or persistence failure restores the original native lists instead of overlapping or discarding icons. Dock-to-home drops also snap to an empty cell and restore both memberships on failure. Existing-folder and home-to-dock transfers retain Spring's native routing. Legacy free-pixel drop handling is skipped while FreeMe is active, including native dock/folder drags without a sparse-grid snapshot.

The source-only `builtin-repo/sources/freeme` package selects `tweak.freeme`. Installation requires `freeme-grid-v1` in a checksum/process-verified running engine, not simply a selected APK or the old free-icon test. Installation/removal changes its live marker without restarting Spring and preserves saved cells and preferences. Alpha6 does **not** implement this ABI; alpha7/7b/8 are separate development builds.

Still required: live UI validation, complete dock/folder transfer workflows, cancellation and changing app availability during a drag. Isolated transient-hole simulations do not validate Spring's complete pointer/event loop.

## DockIn

Native Spring Settings contains the 4–7 capacity choices, with **4 as the default and minimum**. Invalid preferences fall back to 4. Changes are refused if the live icon count is unknown, a drag is active, or reducing capacity would exclude existing dock icons.

Alpha8 adds experimental count-aware geometry, uniform per-icon Canvas transforms in both native dock drawing paths, exact tap bounds, delete-badge mapping, launch origins, edit coordinates, hover/admission and native normalization/reorder hooks. The dock shelf and shared artwork remain unchanged. Four-icon geometry stays stock.

Existing 5–7-icon docks keep recovery geometry after removal or Safe Mode, while new-slot admission returns to the normal four-icon limit. The normalizer preserves existing extra icons instead of silently moving them home. This narrow data/access safeguard is distinct from enabling the tweak in Safe Mode.

**DockIn is not yet usable as a released package.** Native edit-motion icon sizes, launch-animation scale, complete drag/controller transitions, exception-path Canvas restoration and live refresh still need integration/validation. No installable DockIn ABI or bridge hook is advertised, and no DockIn package is built or listed. Do not manually enable it in a user's running engine as part of automated tests.

## Isolated checks

The 2026-11-05 alpha8 development build converted to 5,186 JVM classes without launching Spring. Tests against the packaged classes cover FreeMe grid/reload/transfer rollback and DockIn 5–7-icon geometry, native touch/launch-origin/edit/hover/normalizer hooks, shrinking/active-drag guards and Safe Mode/removal preservation. Both iOS 4/6 editing modes are exercised. Canvas transform tests record coordinates; they are not a rendered live UI trial.

```sh
python3 patches/icon_positions/check.py
python3 patches/icon_positions/check_patched.py path/to/converted-engine.jar
python3 patches/tests/check_layout_settings.py path/to/converted-engine.jar --packaged
python3 -m unittest discover -s tests -q
```

All test data uses temporary directories. Keep the prepared alpha6 local-test launcher separate from development outputs; never replace, restart or install over a running Spring session to test these hooks.
