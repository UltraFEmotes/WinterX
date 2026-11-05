# FreeMe and DockIn development

These are **unfinished Spring 0.8.1 tweaks**, not working catalogue entries. The built-in catalogue still contains only Animaper and ColoredBar. Their drafts were installed/enabled with SnowyHome in the selected combined local test after a fresh stopped-session backup; preparation did not launch Spring or replace saved layouts. Complete live UI checks remain outstanding. Newer development builds remain separate and unselected; see [development status](development-status.md).

## FreeMe

FreeMe places home icons in Spring's normal grid cells rather than arbitrary pixel coordinates. Its separate `files/ruby/freeme-slots-v1.json` stores sparse cells; it never migrates the old `icon-positions-v1.json` or directly rewrites Spring's page JSON.

A live reviewed-batch log exposed repeated `Invalid page capacity` fallbacks. Spring's native `GridProfile` stores **rows** and **columns**, not total cells: four rows × four columns means 16 cells. The correction shares a bounded, overflow-safe rows × columns calculation with the home API. New fixtures use real four/five-row profiles with 16/20 icons instead of the former unrealistic 16-row fixture. No saved cells or native pages are rewritten to resolve this code error.

Implemented hooks cover home drawing, tapping, launch origins, edit positions, hover targets and delete badges. Same-page, cross-page and new-page drops snap to empty cells. A collision or persistence failure restores the original native lists instead of overlapping or discarding icons. Dock-to-home drops also snap to an empty cell and restore both memberships on failure. Existing-folder and home-to-dock transfers retain Spring's native routing. Legacy free-pixel drop handling is skipped while FreeMe is active, including native dock/folder drags without a sparse-grid snapshot.

The source-only `builtin-repo/sources/freeme` package selects `tweak.freeme`. Installation requires `freeme-grid-v1` in a checksum/process-verified running engine, not simply a selected APK or the old free-icon test. Installation/removal changes its live marker without restarting Spring and preserves saved cells and preferences. Alpha6 does **not** implement this ABI. Later engines do, and the draft is enabled in the authorized reviewed local test; its capacity correction remains in the unselected UI-fix2 candidate.

Active home-drag snapshots now handle cancellation and disabling the tweak mid-drag without committing sparse cells. An `ACTION_CANCEL` hook marks the snapshot before native pointer dispatch. If Spring changes native app membership while a pointer is held, FreeMe retains the current native lists rather than restoring an obsolete snapshot over additions/removals. These cases pass packaged controller checks; complete dock/folder pointer workflows and live UI validation are still required. Isolated transient-hole simulations do not validate Spring's complete pointer/event loop.

## DockIn

Native Spring Settings contains the 4–7 capacity choices, with **4 as the default and minimum**. Invalid preferences fall back to 4. Changes are refused if the live icon count is unknown, a drag is active or still settling, or reducing capacity would exclude existing dock icons. Settings reads the selection through its native page factory and requests another animation frame after an action, without navigation or a restart.

Alpha8 adds experimental count-aware geometry, uniform per-icon Canvas transforms in both native dock drawing paths, exact tap bounds, delete-badge mapping, launch origins, edit coordinates, hover/admission and native normalization/reorder hooks. The dock shelf and shared artwork remain unchanged. Four-icon geometry stays stock.

Existing 5–7-icon docks keep recovery geometry after removal or Safe Mode, while new-slot admission returns to the normal four-icon limit. The normalizer preserves existing extra icons instead of silently moving them home. This narrow data/access safeguard is distinct from enabling the tweak in Safe Mode.

Alpha8 separates 150 ms smoothstep icon-size interpolation from Spring's native position/rotation animations. `O1.w` keeps its animation and settled-position caches; `O1.v` supplies the new target coordinates. Animation entries are keyed by identity rather than the mutable Kotlin object's hash/equality. Actual app-launch sizes use `H6` through five launch hooks, not folder-transition `S1` geometry. Direct smali renderer wrappers restore Canvas state on both success and exceptions.

**DockIn is not a released/working-catalogue tweak.** Its unlisted `builtin-repo/sources/dockin` draft selects `tweak.dockin` and requires `dockin-native-v1`, motion/controller hooks and app-launch sizing in a checksum/process-verified running engine. A local `DockIn-0.1.0-alpha.springys` was built, not installed or published in the catalogue. Install/remove changes only its live marker and preserves capacity, sparse cells and native layouts. Packaged checks pass; complete native pointer workflows, visual refresh and live animation trials remain required. Do not manually enable it in a user's running engine as part of automated tests.

## Isolated checks

The final UI-fix2 candidate converted to 6,979 JVM classes without launching Spring and passed all 17 isolated runners. Native layout checks now include full 16/20-cell pages using four/five-row profiles. FreeMe coverage includes grid/reload/transfers/rollback, changing app lists and home-drag cancellation. DockIn covers geometry, native touch/delete/edit/hover/normalization, `H6` launch rectangles, native position caches, size interpolation, renderer exceptions, settling guards and Safe Mode/removal preservation. Both iOS 4/6 editing modes are exercised. Canvas checks record coordinates; they are not a rendered live UI trial. Earlier alpha8's eleven-runner result is historical and preceded the realistic capacity regression.

```sh
python3 patches/icon_positions/check.py
python3 patches/icon_positions/check_patched.py path/to/converted-engine.jar
python3 patches/tests/check_layout_settings.py path/to/converted-engine.jar --packaged
python3 -m unittest discover -s tests -q
```

All test data uses temporary directories. `--source-layout` overlays current layout sources for development only; it is not packaged-engine verification. The selected local test is the **reviewed batch2**, checksum `71fc52605f2d32294597dd9496956e72b3a02d485b4b233703087d6a75ae980d`; it fails the newly strengthened capacity fixture. The separate UI-fix candidate contains the source correction but remains unselected until a stopped-session upgrade is authorized and checked. Never replace, restart or install over a running Spring session to test these hooks. See [current development status](development-status.md).
