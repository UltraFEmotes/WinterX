package winterx.layout;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import E1.O1;
import E1.i6;
import android.graphics.Canvas;

/** Experimental count-aware dock hooks; not yet advertised as an installable ABI. */
public final class DockIn {
    public static final int MIN = 4, MAX = 7;
    private DockIn() {}
    public static boolean installed() {
        File dir = FreeMe.folder();
        return dir != null && !new File(dir, "safe-mode.enabled").isFile() && new File(dir, "dockin.enabled").isFile();
    }
    public static int capacity() {
        if (!installed()) return MIN;
        try {
            File file = new File(FreeMe.folder(), "dockin.capacity");
            if (!file.isFile() || Files.isSymbolicLink(file.toPath()) || file.length() > 16) return MIN;
            String value = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8).trim();
            if (!value.matches("[4-7]")) return MIN;
            return Integer.parseInt(value);
        } catch (Exception ex) { return MIN; }
    }
    /** Never shrink below the live icon count; the user must move excess icons home first. */
    public static boolean select(int value, int liveIcons) {
        if (!installed() || value < MIN || value > MAX || liveIcons < 0 || liveIcons > value) return false;
        return LayoutSettings.write("dockin.capacity", value + "\n");
    }
    /** Existing extra icons remain accessible after removal or Safe Mode. No new slots are granted. */
    public static boolean extended(int count) { return count > MIN && count <= MAX; }
    public static boolean geometry(x1.i1 spring) {
        return spring != null && spring.M1 != null && cell(spring.e, 0, spring.M1.size()) != null;
    }
    public static DockGeometry.Cell cell(i6 profile, int index, int count) {
        if (profile == null || profile.k == null || profile.l == null) return null;
        int margin = Math.max(profile.k.c, Math.round(profile.b * 16f / 320f));
        return DockGeometry.cell(profile.b, profile.e, profile.c - profile.l.c - profile.e, margin, count, index);
    }
    public static M1.b location(i6 profile, int index, int count) {
        DockGeometry.Cell cell = cell(profile, index, count);
        return cell == null ? null : new M1.b(cell.left, cell.top);
    }
    /** Uniformly scale only this icon, its label/shadow/badge; never alter shared bitmaps or the shelf. */
    public static int beginLegacy(Canvas canvas, E1.q6 frame, int index, int stockX, int stockY) {
        if (canvas == null || frame == null || frame.c == null) return -1;
        DockGeometry.Cell cell = cell(frame.a, index, frame.c.size());
        if (cell == null) return -1;
        int saved = canvas.save();
        float scale = cell.size / (float)frame.a.e;
        canvas.translate(cell.left - stockX * scale, cell.top - stockY * scale);
        canvas.scale(scale, scale);
        return saved;
    }
    public static int beginNative(Canvas canvas, E1.q6 frame, int index) {
        if (frame == null || frame.c == null || !extended(frame.c.size())) return -1;
        M1.b stock = I1.h0.j(frame.a, index, frame.c.size());
        return beginLegacy(canvas, frame, index, ((Number)stock.h).intValue(), ((Number)stock.w).intValue());
    }
    public static void endIcon(Canvas canvas, int saved) { if (saved >= 0) canvas.restoreToCount(saved); }
    public static E1.A0 hit(x1.i1 spring, float x, float y) {
        if (spring == null || spring.M1 == null) return null;
        for (int i = 0; i < spring.M1.size(); i++) {
            DockGeometry.Cell cell = cell(spring.e, i, spring.M1.size());
            if (cell != null && cell.contains(x, y)) return new E1.A0(E1.z0.w, i, 0);
        }
        return null;
    }
    public static String deleteHit(x1.i1 spring, float x, float y) {
        if (spring == null || spring.M1 == null || spring.e == null) return null;
        float scale = spring.e.b / 320f;
        for (int i = 0; i < spring.M1.size(); i++) {
            E1.a app = (E1.a)spring.M1.get(i);
            DockGeometry.Cell cell = cell(spring.e, i, spring.M1.size());
            if (cell == null || !x1.i1.d0(app.a)) continue;
            // The native badge hit box is transformed with the same icon scale.
            float iconScale = cell.size / (float)spring.e.e;
            float localX = (x * scale - cell.left) / (scale * iconScale);
            float localY = (y * scale - cell.top) / (scale * iconScale);
            if (x1.i1.J(localX, localY, 0f, 0f)) return app.a;
        }
        return null;
    }
    public static M1.b editLocation(O1 edit, int page, int index, i6 profile) {
        if (edit == null || page != -1) return null;
        M1.b point = location(profile, index, edit.f.size());
        if (point == null) return null;
        float scale = profile.b / 320f;
        return new M1.b(((Number)point.h).floatValue() / scale, ((Number)point.w).floatValue() / scale);
    }
    /** Slot admission is separate from recovery geometry: Safe Mode/removal never adds capacity. */
    public static int editCapacity(O1 edit) {
        return Math.max(capacity(), edit == null ? MIN : edit.f.size());
    }
    public static int normalizeCapacity(java.util.List<?> dock) {
        return Math.max(capacity(), dock == null ? MIN : dock.size());
    }
    public static int liveCount(x1.i1 spring) {
        if (spring == null || spring.M1 == null) return -1;
        if (spring.W1 != null && spring.W1.m != null) return -1;
        return spring.W1 == null ? spring.M1.size() : spring.W1.f.size();
    }
    /** Delegate the stock folder/insertion classifier in a virtual four-icon coordinate space. */
    public static E1.I1 hover(O1 edit, float x, float y, int page, i6 profile) {
        if (edit == null || edit.m == null || edit.J != null || profile == null ||
            !Float.isFinite(x) || !Float.isFinite(y)) return null;
        float screenScale = profile.b / 320f;
        float threshold = E1.t.f - (E1.t.j ? 112f : 109f);
        if (y <= threshold || (!installed() && !extended(edit.f.size()))) return null;
        int count = edit.f.size();
        int cap = capacity();
        int hole = edit.f.indexOf("\u0000hole");
        boolean folder = Boolean.TRUE.equals(edit.h.a(edit.m.a));
        // As in stock Spring, a full dock can still accept an app into an existing folder.
        boolean allowed = !folder && (hole >= 0 || count < cap);
        int index;
        float virtualX;
        java.util.List<String> classified = edit.f;
        if (extended(count)) {
            double pitch = (profile.b - 2.0 * Math.max(profile.k.c, Math.round(profile.b * 16f / 320f))) / count;
            int margin = Math.max(profile.k.c, Math.round(profile.b * 16f / 320f));
            index = Math.max(0, Math.min(count - 1, (int)Math.floor((x * screenScale - margin) / pitch)));
            DockGeometry.Cell cell = cell(profile, index, count);
            if (cell == null) return null;
            float localX = (x * screenScale - cell.left) / cell.size;
            // Classify the actual target with Spring's native folder/side insertion rules.
            classified = java.util.Collections.singletonList((String)edit.f.get(index));
            virtualX = E1.t.j(0) + localX * (E1.t.j ? 60f : 59f) + E1.t.q(1);
        } else {
            virtualX = x;
            index = -1;
        }
        E1.j2 nativeTarget = E1.t.G(virtualX, 0f, classified, true, 4, edit.i, folder, edit.h, false);
        if (index >= 0) {
            nativeTarget = new E1.j2(index, nativeTarget.b);
        }
        return new E1.I1(-1, edit.f, nativeTarget, allowed);
    }
}
