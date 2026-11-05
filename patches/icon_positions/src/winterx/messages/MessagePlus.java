package winterx.messages;

import android.app.ActivityThread;
import android.app.Application;
import com.guille.spring.LauncherActivity;
import E1.N0;
import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.ref.WeakReference;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Opt-in Messages-only UI/photo hook. Does not invent video/reaction wire protocols. */
public final class MessagePlus {
    public static final String ABI = "messageplus-settings-photo-v1";
    private static final String PAGE = "winterx-layout-p/messageplus/", ACTION = "winterx-layout-a/messageplus/";
    private static final float WIDTH = 68f;
    private static final int[] QUALITY = {65, 85, 95};
    private static final String[] LABELS = {"Smaller photos (65)", "Stock photos (85)", "Higher quality (95)"};
    private static final String TRANSPORT = "Photo JPEG quality is configurable. Video sending and reactions are unavailable: Spring 0.8.1 Messages has no verified transport handling for them. No unsupported messages are sent.";
    private static WeakReference<x1.i1> pressed = new WeakReference<>(null);
    private static boolean armed;
    private MessagePlus() {}
    private static File root() {
        try {
            Application app = ActivityThread.currentApplication();
            // Android/Mac.APK owns this root; aliases above it are legitimate. Links
            // beneath the canonical root remain refused by safe(), including ruby/.
            return app == null ? null : app.getFilesDir().getCanonicalFile();
        } catch (Exception failure) { return null; }
    }
    private static boolean safe(File file) {
        try { return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile()); }
        catch (Exception failure) { return false; }
    }
    public static boolean enabled() {
        File root = root(); if (root == null) return false;
        File marker = new File(root, "ruby/messageplus.enabled");
        return safe(marker) && marker.isFile() && !new File(root, "ruby/safe-mode.enabled").exists();
    }
    /** Retain every stock flag; only the main-list left Edit model is passed here. */
    public static N0 button(N0 stock) {
        if (!enabled() || stock == null || !"Edit".equals(stock.a)) return stock;
        return new N0("Settings", null, stock.c, stock.d, Float.valueOf(WIDTH), stock.f, stock.g, stock.h);
    }
    public static int photoQuality(int stock) {
        if (!enabled()) return stock;
        try {
            File file = new File(root(), "ruby/messageplus/photo-quality");
            if (!safe(file) || !file.isFile() || file.length() > 16) return stock;
            byte[] value = Files.readAllBytes(file.toPath()); if (value.length > 16) return stock;
            String text = new String(value, StandardCharsets.UTF_8).trim();
            for (int quality : QUALITY) if (String.valueOf(quality).equals(text)) return quality;
        } catch (Exception ignored) {}
        return stock;
    }
    public static boolean action(String id) {
        if (!enabled() || id == null) return false;
        int quality = -1;
        for (int value : QUALITY) if ((ACTION + "photo/" + value).equals(id)) quality = value;
        if (quality < 0) return false;
        File dir = new File(root(), "ruby/messageplus"), temp = null;
        try {
            File target = new File(dir, "photo-quality");
            if (!safe(dir) || !safe(target) || (!dir.isDirectory() && !dir.mkdirs())) return false;
            temp = File.createTempFile(".quality-", ".tmp", dir);
            try (FileOutputStream out = new FileOutputStream(temp)) {
                out.write((quality + "\n").getBytes(StandardCharsets.UTF_8)); out.getFD().sync();
            }
            if (!enabled()) return false;
            try { Files.move(temp.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
            catch (java.nio.file.AtomicMoveNotSupportedException failure) { Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING); }
            return true;
        } catch (Exception failure) { android.util.Log.e("WinterXMessagePlus", "Photo preference unchanged", failure); return false; }
        finally { if (temp != null) temp.delete(); }
    }
    private static V6 row(String id, String title) { return Z3.g(Z3.a, id, title, null, null, null, 0x18); }
    public static void rows(List<V6> rows) { if (enabled()) rows.add(row(PAGE + "main", "Message+")); }
    public static T6 page(String id) {
        if (!enabled()) return null;
        List<V6> rows = new ArrayList<>();
        if ((PAGE + "main").equals(id)) {
            int selected = photoQuality(85);
            for (int i = 0; i < QUALITY.length; i++) rows.add(row(ACTION + "photo/" + QUALITY[i], (selected == QUALITY[i] ? "✓ " : "") + LABELS[i]));
            return new T6(id, "Message+", Collections.singletonList(new W6("MESSAGES PHOTO QUALITY", null, TRANSPORT + " Existing photo size limits and original photos are preserved. Disabled in Safe Mode.", null, rows)));
        }
        return null;
    }
    private static boolean main(x1.i1 spring) {
        return enabled() && spring != null && spring.a2() && spring.c2 == null && spring.H2 == null &&
            spring.d2 == null && spring.r2 == null && spring.p2 == null && spring.B == null && spring.u2 == null;
    }
    private static boolean hit(x1.i1 spring, float x, float y) {
        if (!main(spring) || !Float.isFinite(x) || !Float.isFinite(y)) return false;
        float scale = spring.R0();
        return Float.isFinite(scale) && scale > 0 && E1.B5.d(x / scale, y / scale, WIDTH, true);
    }
    /** Consume only our Settings gesture; all other presses retain Spring's native routing. */
    public static synchronized boolean press(x1.i1 spring, float x, float y) {
        pressed.clear(); armed = false;
        if (!hit(spring, x, y)) return false;
        pressed = new WeakReference<>(spring); armed = true; return true;
    }
    public static synchronized boolean move(x1.i1 spring, float x, float y) {
        if (pressed.get() != spring || spring == null) return false;
        armed &= hit(spring, x, y); return true;
    }
    public static synchronized boolean release(x1.i1 spring, float x, float y) {
        if (pressed.get() != spring || spring == null) return false;
        boolean open = armed && hit(spring, x, y); pressed.clear(); armed = false;
        if (open) show(spring.a);
        return true;
    }
    public static synchronized void cancel(LauncherActivity activity) { pressed.clear(); armed = false; }
    public static void show(final LauncherActivity activity) {
        if (!enabled() || activity == null) return;
        final x1.J alert;
        try { alert = (x1.J)LauncherActivity.class.getDeclaredMethod("access$alertView", LauncherActivity.class).invoke(null, activity); }
        catch (Exception failure) { android.util.Log.w("WinterXMessagePlus", "Native alert presenter unavailable"); return; }
        if (alert == null) return;
        int selected = photoQuality(85); String[] buttons = new String[4];
        for (int i = 0; i < QUALITY.length; i++) buttons[i] = (selected == QUALITY[i] ? "✓ " : "") + LABELS[i];
        buttons[3] = "Done";
        alert.n("Message+ Settings", TRANSPORT, buttons, 3, index -> {
            if (index instanceof Number) {
                int value = ((Number)index).intValue();
                if (value >= 0 && value < QUALITY.length && enabled()) {
                    boolean saved = action(ACTION + "photo/" + QUALITY[value]);
                    // Present next tick, after Spring dismisses the current alert.
                    alert.e.post(() -> {
                        if (!enabled()) return;
                        if (saved) show(activity);
                        else alert.n("Message+", "Photo preference was not saved; the previous setting is unchanged.", new String[]{"OK"}, 0, ignored -> M1.h.a);
                    });
                }
            }
            return M1.h.a;
        });
    }
}
