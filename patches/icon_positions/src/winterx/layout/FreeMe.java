package winterx.layout;

import android.app.ActivityThread;
import android.app.Application;
import E1.O1;
import E1.c;
import E1.i6;
import java.io.File;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/** Spring 0.8.1 grid-cell placement. Never edits Spring's page JSON or old free-icon data directly. */
public final class FreeMe {
    public static final String ABI = "freeme-grid-v1";
    private static final String HOLE = "\u0000hole";
    private static final WeakHashMap<O1, Snapshot> snapshots = new WeakHashMap<>();
    private static final class Snapshot {
        final int page, index;
        final String id;
        boolean cancelled;
        final ArrayList<ArrayList<String>> pages = new ArrayList<>();
        final ArrayList<String> dock;
        Snapshot(O1 edit, int page, int index, String id) {
            this.page = page; this.index = index; this.id = id;
            for (Object list : edit.e) pages.add(new ArrayList<>((List<String>)list));
            dock = new ArrayList<>(edit.f);
        }
    }
    private FreeMe() {}
    static File folder() {
        Application app = ActivityThread.currentApplication();
        return app == null ? null : new File(app.getFilesDir(), "ruby");
    }
    public static boolean installed() {
        File dir = folder();
        return dir != null && !new File(dir, "safe-mode.enabled").isFile() && new File(dir, "freeme.enabled").isFile();
    }
    public static boolean enabled() { return installed() && !new File(folder(), "freeme.disabled").isFile(); }
    private static File file() { return new File(folder(), "freeme-slots-v1.json"); }
    private static int capacity(i6 profile) { return profile.k.a; }
    private static List<String> ids(List<c> entries) {
        List<String> result = new ArrayList<>();
        for (c entry : entries) result.add(entry.a.a);
        return result;
    }
    /** Immutable per-use entries: stock row/column models and folders are never mutated. */
    public static List<c> entries(List<c> original, i6 profile, int page) {
        if (!enabled() || page < 0) return original;
        try {
            Map<String, Integer> slots = GridSlots.load(file()).resolve(page, ids(original), capacity(profile));
            List<c> result = new ArrayList<>();
            for (c entry : original) {
                int slot = slots.get(entry.a.a);
                result.add(new c(entry.a, slot / profile.k.b, slot % profile.k.b));
            }
            return result;
        } catch (Exception ex) {
            android.util.Log.e("WinterXFreeMe", "Could not resolve home grid", ex);
            return original;
        }
    }
    public static M1.b animation(x1.i1 spring, E1.A0 target) {
        if (!enabled() || target == null || target.a == E1.z0.w) return null;
        try {
            int page = target.a == E1.z0.h ? 0 : target.c;
            List<c> original = page == 0 ? spring.L1 : (List<c>)spring.S1.get(page - 1);
            c entry = entries(original, spring.e, page).get(target.b);
            return E1.d4.w(spring.e, entry.b, entry.c);
        } catch (RuntimeException ex) { return null; }
    }
    public static M1.b editLocation(O1 edit, int page, int index, i6 profile) {
        if (!enabled() || page < 0 || profile == null) return null;
        try {
            List<String> live = new ArrayList<>((List<String>)edit.s(page));
            String id = live.get(index);
            if (HOLE.equals(id)) {
                Snapshot saved = snapshots.get(edit);
                if (saved == null || saved.page != page) return null;
                live.set(index, saved.id); id = saved.id;
            }
            live.remove(HOLE);
            int slot = GridSlots.load(file()).resolve(page, live, edit.a).get(id);
            M1.b point = E1.d4.w(profile, slot / edit.b, slot % edit.b);
            float scale = profile.b / 320.0f;
            return new M1.b(((Number)point.h).floatValue() / scale, ((Number)point.w).floatValue() / scale);
        } catch (Exception ex) { return null; }
    }
    /** Native hover target in sparse cells; existing folders keep Spring's folder routing. */
    public static E1.I1 hover(O1 edit, float centerX, float centerY, int page, i6 profile) {
        if (!enabled() || profile == null || edit.m == null || edit.J != null || page < 0) return null;
        float scale = profile.b / 320f;
        if (scale <= 0 || !Float.isFinite(centerX) || !Float.isFinite(centerY) ||
            centerY >= profile.c / scale - (E1.t.j ? 96f : 89f)) return null;
        try {
            List<String> list = (List<String>)edit.s(page);
            if (list == null) return null;
            List<String> live = new ArrayList<>(list);
            Snapshot saved = snapshots.get(edit);
            int hole = live.indexOf(HOLE);
            if (hole >= 0 && saved != null && saved.page == page) live.set(hole, saved.id);
            else live.remove(HOLE);
            Map<String, Integer> slots = GridSlots.load(file()).resolve(page, live, edit.a);
            float x = (centerX - (E1.t.j ? 30f : 29.5f)) * scale, y = (centerY - 37f) * scale;
            for (int index = 0; index < list.size(); index++) {
                String id = list.get(index); Integer slot = slots.get(id);
                if (slot == null) continue;
                M1.b point = E1.d4.w(profile, slot / edit.b, slot % edit.b);
                float px = ((Number)point.h).floatValue(), py = ((Number)point.w).floatValue();
                if (Math.abs(x - px) <= profile.e / 2f && Math.abs(y - py) <= profile.e / 2f)
                    return new E1.I1(page, list, new E1.j2(index, edit.g.containsKey(id) ? 2 : 0), true);
            }
            return new E1.I1(page, list, new E1.j2(hole >= 0 ? hole : list.size(), hole >= 0 ? 0 : 4), true);
        } catch (Exception ex) { return null; }
    }
    /** Spring's native delete-badge hit test, using the same sparse cells as rendering. */
    public static String deleteHit(x1.i1 spring, float x, float y) {
        if (!enabled() || spring == null) return null;
        try {
            int page = spring.h1();
            List<c> original = page == 0 ? spring.L1 : (List<c>)spring.S1.get(page - 1);
            float scale = spring.e.b / 320f;
            for (c entry : entries(original, spring.e, page)) {
                if (!x1.i1.d0(entry.a.a)) continue;
                M1.b point = E1.d4.w(spring.e, entry.b, entry.c);
                if (x1.i1.J(x, y, ((Number)point.h).floatValue() / scale, ((Number)point.w).floatValue() / scale)) return entry.a.a;
            }
        } catch (RuntimeException ex) { android.util.Log.e("WinterXFreeMe", "Could not hit-test delete badge", ex); }
        return null;
    }
    public static synchronized void begin(O1 edit, int page, int index) {
        if (edit.m != null) return;
        snapshots.remove(edit);
        if (!enabled() || (page < 0 && page != -1) || edit.J != null) return;
        try {
            List<String> list = (List<String>)edit.s(page);
            String id = list.get(index);
            if (id == null || id.startsWith("\u0000")) return;
            snapshots.put(edit, new Snapshot(edit, page, index, id));
        } catch (RuntimeException ex) { android.util.Log.e("WinterXFreeMe", "Could not begin grid drag", ex); }
    }
    /** Mark the snapshot before Spring dispatches ACTION_CANCEL to its native controller. */
    public static synchronized void cancel(O1 edit) {
        Snapshot saved = snapshots.get(edit);
        if (saved != null) saved.cancelled = true;
    }
    private static void restore(O1 edit, Snapshot saved, int page, int index, ArrayList<ArrayList<String>> pages) {
        restore(edit, saved, page, index, pages, saved.dock);
    }
    private static void restore(O1 edit, Snapshot saved, int page, int index, ArrayList<ArrayList<String>> pages, List<String> dock) {
        edit.e.clear();
        for (ArrayList<String> list : pages) edit.e.add(new ArrayList<>(list));
        edit.f.clear(); edit.f.addAll(dock);
        ((List<String>)edit.s(page)).set(index, HOLE);
        edit.n = page; edit.o = index; edit.D = null; edit.P++;
    }
    private static java.util.Set<String> members(List<?> pages, List<?> dock) {
        java.util.Set<String> ids = new java.util.HashSet<>();
        for (Object id : dock) if (id instanceof String && !((String)id).startsWith("\u0000")) ids.add((String)id);
        for (Object page : pages) for (Object id : (List<?>)page)
            if (id instanceof String && !((String)id).startsWith("\u0000")) ids.add((String)id);
        return ids;
    }
    /** Returns true only for a handled home drop; dock and folder transfers retain native behavior. */
    public static synchronized boolean beforeDrop(O1 edit, i6 profile) {
        Snapshot saved = snapshots.remove(edit);
        if (saved == null) return false;
        if (edit.m == null || profile == null || !saved.id.equals(edit.m.a)) return false;
        // Spring can refresh app availability while a pointer is held. Never restore an old
        // snapshot over its additions/removals; let the current native controller settle.
        java.util.Set<String> current = members(edit.e, edit.f);
        current.add(edit.m.a);
        if (!current.equals(members(saved.pages, saved.dock))) {
            edit.D = null;
            android.util.Log.w("WinterXFreeMe", "App membership changed during drag; retained live native lists");
            return true;
        }
        if (saved.cancelled || !enabled()) { restore(edit, saved, saved.page, saved.index, saved.pages); return true; }
        float scale = profile.b / 320.0f;
        float x = (edit.m.f - edit.m.c - (E1.t.j ? 30f : 29.5f)) * scale;
        float y = (edit.m.g - edit.m.d - 37f) * scale;
        float dockTop = profile.c - (E1.t.j ? 96f : 89f) * scale;
        // Entered/open folders, hovered existing folders, and the dock stay native.
        if (edit.J != null || edit.n < 0 || y >= dockTop || (edit.D != null && edit.g.containsKey(edit.D))) return true;
        int page = edit.w;
        if (page < 0 || page > saved.pages.size() || page > 100 || !Float.isFinite(x) || !Float.isFinite(y) ||
            x < -profile.e / 2f || x > profile.b - profile.e / 2f || y < 0 || y >= dockTop) {
            restore(edit, saved, saved.page, saved.index, saved.pages); return true;
        }
        try {
            // Use Spring's actual profile grid; no fractional pixel-coordinate migration.
            int nearest = -1; double distance = Double.POSITIVE_INFINITY;
            for (int slot = 0; slot < edit.a; slot++) {
                M1.b point = E1.d4.w(profile, slot / edit.b, slot % edit.b);
                float px = ((Number)point.h).floatValue(), py = ((Number)point.w).floatValue();
                if (py + profile.e > dockTop) continue;
                double d = (x - px) * (x - px) + (y - py) * (y - py);
                if (d < distance) { nearest = slot; distance = d; }
            }
            if (nearest < 0) throw new IllegalArgumentException("No home grid cells");
            GridSlots grid = GridSlots.load(file());
            ArrayList<ArrayList<String>> updated = new ArrayList<>();
            for (ArrayList<String> list : saved.pages) updated.add(new ArrayList<>(list));
            ArrayList<String> dock = new ArrayList<>(saved.dock);
            if (page == updated.size()) updated.add(new ArrayList<String>());
            Map<String, Integer> source = saved.page < 0 ? new LinkedHashMap<String, Integer>() : grid.resolve(saved.page, saved.pages.get(saved.page), edit.a);
            Map<String, Integer> target = page == saved.page ? source : grid.resolve(page, updated.get(page), edit.a);
            for (Map.Entry<String, Integer> entry : target.entrySet())
                if (!entry.getKey().equals(saved.id) && entry.getValue() == nearest) {
                    restore(edit, saved, saved.page, saved.index, saved.pages); return true;
                }
            int index = saved.index;
            if (page != saved.page) {
                if (updated.get(page).size() >= edit.a) {
                    restore(edit, saved, saved.page, saved.index, saved.pages); return true;
                }
                if (saved.page == -1) dock.remove(saved.index);
                else updated.get(saved.page).remove(saved.index);
                index = updated.get(page).size(); updated.get(page).add(saved.id);
                source.remove(saved.id);
            }
            target.put(saved.id, nearest);
            if (saved.page >= 0) grid.replace(saved.page, source);
            if (page != saved.page) grid.replace(page, target);
            // Persist first: on failure the original native lists/positions remain intact.
            grid.save(file());
            restore(edit, saved, page, index, updated, dock);
            android.util.Log.i("WinterXFreeMe", "Grid drag saved on page " + page + ", cell " + nearest);
        } catch (Exception ex) {
            restore(edit, saved, saved.page, saved.index, saved.pages);
            android.util.Log.e("WinterXFreeMe", "Grid drag failed; restored original lists", ex);
        }
        return true;
    }
}
