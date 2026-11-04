package winterx.runtime;

import java.io.File;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Detect complete .sapp copies and ask Spring's own installer to refresh. */
public final class InboxMonitor implements Runnable {
    private final J1.y manager;
    private Map<String, String> previous = new HashMap<>();
    private long lastRequest;
    private InboxMonitor(J1.y manager) { this.manager = manager; }
    public static void start(J1.y manager) {
        if (manager == null || manager.h == null || manager.a == null) return;
        manager.h.postDelayed(new InboxMonitor(manager), 1500);
    }
    @Override public void run() {
        try {
            if (manager.a.isFinishing() || manager.a.isDestroyed()) return;
            File inbox = manager.a.getExternalFilesDir("sapps-inbox");
            Map<String, String> current = new HashMap<>();
            boolean ready = false;
            File[] files = inbox == null ? null : inbox.listFiles();
            if (files != null) for (File file : files) {
                if (!file.isFile() || !file.getName().toLowerCase(Locale.ROOT).endsWith(".sapp")) continue;
                String fingerprint = file.length() + ":" + file.lastModified();
                current.put(file.getName(), fingerprint);
                if (file.length() > 0 && fingerprint.equals(previous.get(file.getName()))) ready = true;
            }
            previous = current;
            long now = android.os.SystemClock.elapsedRealtime();
            if (ready && (lastRequest == 0 || now - lastRequest >= 5000 || now < lastRequest)) {
                lastRequest = now;
                manager.h();
            }
        } catch (RuntimeException ignored) {
            // A transient storage error must not bring down the launcher.
        } finally {
            if (!manager.a.isFinishing() && !manager.a.isDestroyed()) manager.h.postDelayed(this, 1500);
        }
    }
}
