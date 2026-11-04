package winterx.layout;

import E1.G1;
import E1.O1;
import E1.i6;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;

/** Per-controller sizing, separate from Spring's native position/rotation animations. */
public final class DockMotion {
    private static final WeakHashMap<O1, Map<String, Change>> controllers = new WeakHashMap<>();
    // G1/a are mutable Kotlin value objects. Their hash/equality must never key animation state.
    // Retain only one frame, keyed by identity, rather than accumulating renderer entries.
    private static final IdentityHashMap<G1, Float> frames = new IdentityHashMap<>();
    private static final class Change {
        float from, to;
        long at;
        Change(float value) { from = to = value; }
        float value(long now) {
            float t = Math.max(0f, Math.min(1f, (now - at) / 150f));
            t = t * t * (3f - 2f * t);
            return from + (to - from) * t;
        }
        void target(float value, long now) {
            if (to == value) return;
            from = value(now); to = value; at = now;
        }
    }
    private DockMotion() {}
    private static float dock(i6 profile, int count) {
        DockGeometry.Cell cell = DockIn.cell(profile, 0, count);
        return cell == null ? 1f : cell.size / (float)profile.e;
    }
    public static synchronized void begin(O1 edit, i6 profile) {
        if (edit == null || edit.m != null || edit.z != null || profile == null) return;
        Map<String, Change> sizes = new HashMap<>();
        float scale = dock(profile, edit.f.size());
        for (Object id : edit.f) sizes.put((String)id, new Change(scale));
        controllers.put(edit, sizes);
    }
    public static synchronized void frame(x1.i1 host, List<G1> entries, long now) {
        frames.clear();
        if (host == null || host.W1 == null || entries == null || host.e == null) return;
        O1 edit = host.W1;
        Map<String, Change> sizes = controllers.get(edit);
        if (sizes == null) { sizes = new HashMap<>(); controllers.put(edit, sizes); }
        float dock = dock(host.e, edit.f.size());
        for (G1 entry : entries) {
            String id = entry.a.a;
            boolean inDock = entry.b == -1 || edit.f.contains(id) ||
                (edit.m != null && id.equals(edit.m.a) && edit.n == -1);
            float target = inDock ? dock : 1f;
            Change change = sizes.get(id);
            if (change == null) { change = new Change(target); sizes.put(id, change); }
            change.target(target, now);
            frames.put(entry, change.value(now));
        }
        // Include off-screen native members; switching pages must not reset their size motion.
        java.util.HashSet<String> live = new java.util.HashSet<>();
        for (Object id : edit.f) live.add((String)id);
        for (Object page : edit.e) for (Object id : (List<?>)page) live.add((String)id);
        if (edit.m != null) live.add(edit.m.a);
        for (G1 entry : entries) live.add(entry.a.a);
        sizes.keySet().retainAll(live);
    }
    public static synchronized float scale(E1.q6 frame, G1 entry) {
        Float saved = frames.get(entry);
        if (saved != null) return saved;
        return frame != null && frame.c != null && entry != null && entry.b == -1
            ? dock(frame.a, frame.c.size()) : 1f;
    }
}
