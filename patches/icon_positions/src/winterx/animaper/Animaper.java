package winterx.animaper;

import android.app.ActivityThread;
import android.app.Application;
import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;

/** Spring 0.8.1 rendering adapter for Animaper. */
public final class Animaper {
    private static String cachedMode = "wave";
    private static long lastRead;
    private Animaper() {}
    private static synchronized String mode() {
        try {
            Application app = ActivityThread.currentApplication();
            if (app == null) return null;
            File dir = new File(app.getFilesDir(), "ruby");
            if (new File(dir,"safe-mode.enabled").isFile() || !new File(dir,"animaper.enabled").isFile()) return null;
            long now = android.os.SystemClock.elapsedRealtime();
            if (now - lastRead >= 500 || now < lastRead) {
                File config = new File(dir,"animaper.mode");
                String value = "wave";
                if (config.isFile() && config.length() <= 64) {
                    try (FileInputStream input = new FileInputStream(config)) {
                        byte[] bytes = new byte[64];
                        int count = input.read(bytes);
                        if (count > 0) value = new String(bytes, 0, count, StandardCharsets.UTF_8).trim();
                    }
                }
                cachedMode = value;
                lastRead = now;
            }
            return cachedMode;
        } catch (Exception ignored) { return null; }
    }
    public static M1.b location(E1.i6 profile, E1.c entry, int page, int pageOffset) {
        M1.b point = winterx.layout.SpringHooks.location(profile, entry, page);
        String mode = mode();
        if (mode == null || profile.b <= 0 || pageOffset == 0) return point;
        int[] delta = Effects.offset(mode, (float)pageOffset / profile.b, entry.b, entry.c, profile.b, profile.e);
        return new M1.b(Integer.valueOf(((Number)point.h).intValue() + delta[0]),
                        Integer.valueOf(((Number)point.w).intValue() + delta[1]));
    }
}
