package winterx.layout;

import android.app.ActivityThread;
import android.app.Application;
import java.io.File;

/** Runtime-facing adapter for Spring hooks; currently not installed in the APK. */
public final class IconRuntime {
    private static File cachedFile;
    private static IconPositions cached;
    private IconRuntime() {}

    private static File stateFolder() {
        Application app = ActivityThread.currentApplication();
        return app == null ? null : new File(app.getFilesDir(), "ruby");
    }
    private static File enabledFolder() {
        File folder = stateFolder();
        if (folder == null || new File(folder, "safe-mode.enabled").isFile() || !new File(folder, "free-icons.enabled").isFile()) return null;
        return folder;
    }
    public static boolean enabled() { return enabledFolder() != null; }
    private static IconPositions read(File folder) throws Exception {
        File file = new File(folder, "icon-positions-v1.json");
        if (cached == null || !file.equals(cachedFile)) {
            cached = IconPositions.load(file);
            cachedFile = file;
        }
        return cached;
    }
    private static double fraction(float coordinate, int extent, int iconExtent) {
        if (!Float.isFinite(coordinate) || extent <= 0 || iconExtent <= 0 || iconExtent >= extent)
            throw new IllegalArgumentException("Invalid screen geometry");
        return Math.max(0, Math.min(1, coordinate / (extent - iconExtent)));
    }
    /** Record a drop relative to the top-left of a page, excluding the dock. */
    public static synchronized boolean record(int page, String id, float x, float y, int width, int height, int iconWidth, int iconHeight) {
        File folder = enabledFolder();
        if (folder == null) return false;
        try {
            File file = new File(folder, "icon-positions-v1.json");
            IconPositions updated = IconPositions.load(file);
            updated.put(page, id, fraction(x, width, iconWidth), fraction(y, height, iconHeight));
            updated.save(file);
            cached = updated;
            cachedFile = file;
            return true;
        } catch (Exception ex) {
            android.util.Log.e("WinterX", "Could not save icon position", ex);
            return false;
        }
    }
    public static synchronized boolean forget(int page, String id) {
        File folder = enabledFolder();
        if (folder == null) return false;
        try {
            File file = new File(folder, "icon-positions-v1.json");
            IconPositions updated = IconPositions.load(file);
            if (updated.remove(page, id)) updated.save(file);
            cached = updated;
            cachedFile = file;
            return true;
        } catch (Exception ex) {
            android.util.Log.e("WinterX", "Could not clear icon position", ex);
            return false;
        }
    }
    /** Return a pixel position, or null to retain Spring's own grid position. */
    public static synchronized int[] position(int page, String id, int width, int height, int iconWidth, int iconHeight) {
        File folder = enabledFolder();
        if (folder == null || width <= iconWidth || height <= iconHeight || iconWidth <= 0 || iconHeight <= 0) return null;
        try {
            IconPositions.Placement p = read(folder).get(page, id);
            if (p == null) return null;
            return new int[] {(int)Math.round(p.x * (width - iconWidth)), (int)Math.round(p.y * (height - iconHeight))};
        } catch (Exception ex) {
            android.util.Log.e("WinterX", "Could not load icon positions", ex);
            return null;
        }
    }
    /** Map a point on the screen to the frontmost stored icon on this page. */
    public static synchronized String hit(int page, float x, float y, int width, int height, int iconWidth, int iconHeight) {
        File folder = enabledFolder();
        if (folder == null || width <= iconWidth || height <= iconHeight || iconWidth <= 0 || iconHeight <= 0 || !Float.isFinite(x) || !Float.isFinite(y)) return null;
        try {
            IconPositions.Placement p = read(folder).hit(page, x / (width - iconWidth), y / (height - iconHeight),
                (double)iconWidth / (width - iconWidth), (double)iconHeight / (height - iconHeight));
            return p == null ? null : p.id;
        } catch (Exception ex) {
            android.util.Log.e("WinterX", "Could not hit-test icon positions", ex);
            return null;
        }
    }
}
