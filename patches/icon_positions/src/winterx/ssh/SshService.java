package winterx.ssh;

import android.app.ActivityThread;
import java.io.File;
import java.nio.file.Files;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Optional library adapter. Starts only from native Settings, never on boot/install; loopback only. */
public final class SshService {
    private static final ScheduledExecutorService worker = Executors.newSingleThreadScheduledExecutor(run -> {
        Thread thread = new Thread(run, "WinterX-SSH"); thread.setDaemon(true); return thread;
    });
    private static final AtomicBoolean busy = new AtomicBoolean();
    private static final AtomicBoolean startAllowed = new AtomicBoolean();
    private static Object engine;
    private static String keyRevision;
    private static boolean watchStarted;
    private static volatile String status = "Stopped. No automatic start.";
    private SshService() {}
    public static boolean available() {
        try { Class.forName("winterx.ssh.SshServerEngine", false, SshService.class.getClassLoader()); return true; }
        catch (Throwable unavailable) { return false; }
    }
    private static File files() { return ActivityThread.currentApplication() == null ? null : ActivityThread.currentApplication().getFilesDir(); }
    private static boolean safe(File file) {
        try { return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile()); }
        catch (Exception failure) { return false; }
    }
    public static boolean installed() {
        File root = files(); if (root == null || !available()) return false;
        File marker = new File(root, "ruby/ssh.enabled");
        return safe(marker) && marker.isFile() && !new File(root, "ruby/safe-mode.enabled").exists();
    }
    public static String status() { return status; }
    private static String digest(File file) throws Exception {
        if (!safe(file) || !file.isFile() || file.length() > 16384) throw new java.io.IOException("Invalid bounded SSH keys");
        byte[] bytes = Files.readAllBytes(file.toPath());
        if (bytes.length > 16384) throw new java.io.IOException("SSH keys exceed limit");
        StringBuilder hex = new StringBuilder();
        for (byte b : java.security.MessageDigest.getInstance("SHA-256").digest(bytes)) hex.append(String.format(java.util.Locale.US, "%02x", b & 255));
        return hex.toString();
    }
    public static synchronized boolean request(final boolean start) {
        if (start && !installed()) return false;
        if (!start) startAllowed.set(false); // cancel an in-flight Start even while its worker is busy
        if (!busy.compareAndSet(false, true)) return !start;
        if (start) startAllowed.set(true);
        worker.execute(() -> {
            try {
                if (!start) { stop("Stopped by Settings."); return; }
                if (engine != null) return;
                File root = files(), dir = new File(root, "ruby/ssh"), keys = new File(dir, "authorized_keys");
                if (!safe(dir) || !safe(keys) || !installed() || !startAllowed.get()) throw new java.io.IOException("Private SSH key configuration unavailable or start cancelled");
                if (!keys.isFile() || keys.length() > 16384) throw new java.io.IOException("Copy authorized_keys into ruby/ssh first");
                keyRevision = digest(keys);
                Class<?> type = Class.forName("winterx.ssh.SshServerEngine");
                engine = type.getMethod("configure", java.nio.file.Path.class, java.nio.file.Path.class,
                    java.nio.file.Path.class, int.class, boolean.class).invoke(null, root.toPath(), keys.toPath(), new File(dir, "host-key.ser").toPath(), 2222, true);
                // Own the configured resource before any later check can fail, so catch/stop closes it.
                if (!installed() || !startAllowed.get() || !keyRevision.equals(digest(keys))) throw new java.io.IOException("SSH disabled, start cancelled or keys changed before start");
                type.getMethod("start").invoke(engine);
                if (!installed() || !startAllowed.get() || !keyRevision.equals(digest(keys))) throw new java.io.IOException("SSH disabled during start");
                status = "Listening on 127.0.0.1:2222 as winterx. Host key: " + type.getField("fingerprint").get(engine);
                if (!watchStarted) { worker.scheduleWithFixedDelay(() -> watch(), 500, 500, TimeUnit.MILLISECONDS); watchStarted = true; }
            } catch (Throwable failure) { stop("Not started: " + String.valueOf(failure.getCause() == null ? failure.getMessage() : failure.getCause().getMessage())); }
            finally { busy.set(false); }
        });
        return true;
    }
    private static void watch() {
        if (engine == null) return;
        try {
            File keys = new File(files(), "ruby/ssh/authorized_keys");
            if (!installed() || !startAllowed.get() || !safe(keys) || !keyRevision.equals(digest(keys)))
                stop("Stopped: Safe Mode, removal or authorized keys changed. Start explicitly again.");
        } catch (Throwable failure) { stop("Stopped: SSH configuration unavailable."); }
    }
    private static void stop(String message) {
        startAllowed.set(false);
        if (engine != null) {
            try { engine.getClass().getMethod("stop").invoke(engine); }
            catch (Throwable failure) { status = "SSH stop failed; close this Spring session. " + String.valueOf(failure.getMessage()); return; }
            engine = null;
        }
        status = message;
    }
}
