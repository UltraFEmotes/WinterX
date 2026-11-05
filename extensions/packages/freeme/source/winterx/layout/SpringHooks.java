package winterx.layout;

import E1.O1;
import E1.i6;
import E1.c;
import java.util.ArrayList;
import java.util.List;
import java.util.WeakHashMap;

/** Version-specific Spring 0.8.1 hooks shared by FreeMe and the legacy position test. */
public final class SpringHooks {
    private static final WeakHashMap<O1, Snapshot> snapshots = new WeakHashMap<>();
    private static final class Snapshot {
        final int page, index;
        final String id;
        final ArrayList<ArrayList<String>> pages;
        final ArrayList<String> dock;
        Snapshot(int page, int index, String id, ArrayList<ArrayList<String>> pages, ArrayList<String> dock) {
            this.page = page; this.index = index; this.id = id; this.pages = pages; this.dock = dock;
        }
    }
    private static i6 profile(O1 edit) {
        try {
            if (!(edit.d instanceof x1.P0)) return null;
            java.lang.reflect.Field field = x1.P0.class.getDeclaredField("w");
            field.setAccessible(true);
            x1.i1 spring = (x1.i1)field.get(edit.d);
            return spring == null ? null : spring.e;
        } catch (ReflectiveOperationException | RuntimeException ex) {
            return null;
        }
    }
    // Spring's renderer/profile uses pixels (usually 640 wide), while O1's
    // editing controller uses 320-wide logical points.
    private static float editScale(i6 profile) { return profile.b / 320.0f; }
    private static int availableHeight(i6 profile) {
        float dockPoints = E1.t.j ? 96.0f : 89.0f;
        return Math.max(profile.e + 1, profile.c - Math.round(dockPoints * editScale(profile)));
    }
    public static E1.I1 hover(O1 edit, float x, float y, int page) {
        i6 profile = profile(edit);
        E1.I1 dock = winterx.extension.NativeHooks.dock_hover(edit, x, y, page, profile);
        return dock != null ? dock : FreeMe.hover(edit, x, y, page, profile);
    }

    private static boolean occupied(Snapshot snapshot, O1 edit, i6 profile, float x, float y) {
        List<String> page = snapshot.pages.get(snapshot.page);
        for (int i = 0; i < page.size(); i++) {
            String other = page.get(i);
            if (other.equals(snapshot.id) || other.startsWith("\u0000")) continue;
            int[] point = IconRuntime.position(snapshot.page, other, profile.b, availableHeight(profile), profile.e, profile.e);
            if (point == null) {
                M1.b grid = E1.d4.w(profile, i / edit.b, i % edit.b);
                point = new int[] {((Number)grid.h).intValue(), ((Number)grid.w).intValue()};
            }
            if (x < point[0] + profile.e && x + profile.e > point[0] &&
                y < point[1] + profile.e && y + profile.e > point[1]) return true;
        }
        return false;
    }

    private static void restoreOriginalOrder(O1 edit, Snapshot snapshot) {
        edit.e.clear();
        for (ArrayList<String> page : snapshot.pages) edit.e.add(new ArrayList<>(page));
        edit.f.clear(); edit.f.addAll(snapshot.dock);
        ((List<String>)edit.e.get(snapshot.page)).set(snapshot.index, "\u0000hole");
        edit.n = snapshot.page;
        edit.o = snapshot.index;
        edit.D = null;
        edit.P++;
    }

    /** Shared by the home renderer and hit testing; retain Spring's position when absent. */
    public static M1.b location(i6 profile, c entry, int page) {
        M1.b original = E1.d4.w(profile, entry.b, entry.c);
        if (FreeMe.enabled()) return original;
        int[] position = IconRuntime.position(page, entry.a.a, profile.b, availableHeight(profile), profile.e, profile.e);
        return position == null ? original : new M1.b(Integer.valueOf(position[0]), Integer.valueOf(position[1]));
    }

    /** Return an edit-mode position, or null to retain Spring's animation/grid logic. */
    public static M1.b editLocation(O1 edit, int page, int index) {
        M1.b dock = winterx.extension.NativeHooks.dock_edit_location(edit, page, index, profile(edit));
        if (dock != null) return dock;
        if (FreeMe.enabled()) return FreeMe.editLocation(edit, page, index, profile(edit));
        if (page < 0 || !IconRuntime.enabled()) return null;
        try {
            List<?> list = edit.s(page);
            i6 profile = profile(edit);
            if (profile == null || list == null || index < 0 || index >= list.size()) return null;
            Object id = list.get(index);
            if (!(id instanceof String)) return null;
            int[] position = IconRuntime.position(page, (String)id, profile.b, availableHeight(profile), profile.e, profile.e);
            float scale = editScale(profile);
            return position == null || scale <= 0 ? null : new M1.b(Float.valueOf(position[0] / scale), Float.valueOf(position[1] / scale));
        } catch (RuntimeException ex) {
            android.util.Log.e("WinterX", "Could not resolve edit position", ex);
            return null;
        }
    }
    /** DockIn must retain Spring's cached reorder/settling motion, whose targets use patched v(). */
    public static M1.b animatedLocation(O1 edit, int page, int index) {
        if (page == -1 && winterx.extension.NativeHooks.dock_edit_location(edit, page, index, profile(edit)) != null) return null;
        return editLocation(edit, page, index);
    }
    public static void pointer(x1.i1 spring, int action) {
        if (action != 3) return;
        if (spring != null && spring.W1 != null) FreeMe.cancel(spring.W1);
    }

    /** Preserve original lists before Spring starts its temporary grid reorder. */
    public static synchronized void begin(O1 edit, int page, int index) {
        FreeMe.begin(edit, page, index);
        if (edit.m != null) return;
        snapshots.remove(edit);
        if (FreeMe.enabled()) return;
        if (!IconRuntime.enabled() || page < 0) return;
        if (profile(edit) == null) {
            android.util.Log.w("WinterXIcons", "Free drag unavailable: Spring profile could not be resolved");
            return;
        }
        try {
            if (page >= edit.e.size()) return;
            List<?> original = (List<?>)edit.e.get(page);
            if (index < 0 || index >= original.size() || !(original.get(index) instanceof String)) return;
            String id = (String)original.get(index);
            if (id.startsWith("\u0000")) return;
            ArrayList<ArrayList<String>> pages = new ArrayList<>();
            for (Object pageList : edit.e) pages.add(new ArrayList<>((List<String>)pageList));
            snapshots.put(edit, new Snapshot(page, index, id, pages, new ArrayList<String>(edit.f)));
            android.util.Log.i("WinterXIcons", "Free drag started on page " + page + ", slot " + index);
        } catch (RuntimeException ex) {
            android.util.Log.e("WinterX", "Could not begin free placement", ex);
        }
    }

    /** Save same-page drops and restore the original order before Spring finishes its drag. */
    public static synchronized void beforeDrop(O1 edit) {
        if (FreeMe.beforeDrop(edit, profile(edit))) return;
        // Dock/folder drags without a FreeMe snapshot are native, never legacy free-pixel drags.
        if (FreeMe.enabled()) return;
        Snapshot snapshot = snapshots.remove(edit);
        if (!IconRuntime.enabled()) return;
        if (snapshot == null) {
            if (edit.m != null && edit.m.b >= 0) {
                edit.D = null;
                android.util.Log.w("WinterXIcons", "Free drag ended without a saved starting state");
            }
            return;
        }
        E1.M1 drag = edit.m;
        i6 profile = profile(edit);
        if (drag == null || profile == null || !snapshot.id.equals(drag.a)) {
            edit.D = null;
            android.util.Log.w("WinterXIcons", "Free drag state changed before the drop");
            return;
        }
        // In free-placement mode, a hover over another icon must not turn into
        // a folder. The collision check below keeps icons separate.
        edit.D = null;
        if (edit.J != null || edit.w != snapshot.page) {
            IconRuntime.forget(snapshot.page, snapshot.id);
            android.util.Log.i("WinterXIcons", "Free drag left its original page");
            return;
        }
        float scale = editScale(profile);
        if (scale <= 0) return;
        float editingIconSize = E1.t.j ? 60.0f : 59.0f;
        float x = (drag.f - drag.c - editingIconSize / 2.0f) * scale;
        float y = (drag.g - drag.d - 37.0f) * scale;
        int height = availableHeight(profile);
        if (!Float.isFinite(x) || !Float.isFinite(y) || x < -profile.e / 2.0f ||
            x > profile.b - profile.e / 2.0f || y < 0 || y > height - profile.e / 2.0f) {
            restoreOriginalOrder(edit, snapshot);
            android.util.Log.i("WinterXIcons", "Free drag outside the page; original layout restored");
            return;
        }
        x = Math.max(0, Math.min(profile.b - profile.e, x));
        y = Math.max(0, Math.min(height - profile.e, y));
        try {
            boolean blocked = occupied(snapshot, edit, profile, x, y);
            if (!blocked && !IconRuntime.record(snapshot.page, snapshot.id, x, y, profile.b, height, profile.e, profile.e)) {
                android.util.Log.w("WinterXIcons", "Free drag could not save its position");
                restoreOriginalOrder(edit, snapshot);
                return;
            }
            restoreOriginalOrder(edit, snapshot);
            android.util.Log.i("WinterXIcons", blocked ? "Free drag overlaps another icon; original position restored" : "Free drag saved on page " + snapshot.page);
        } catch (RuntimeException ex) {
            android.util.Log.e("WinterX", "Could not finish free placement", ex);
        }
    }
}
