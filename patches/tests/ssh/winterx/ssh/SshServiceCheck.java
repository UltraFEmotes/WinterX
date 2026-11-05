package winterx.ssh;

import java.io.File;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Exercises actual service worker ownership/cancellation, using only an engine spy. */
public final class SshServiceCheck {
    static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
    static ScheduledExecutorService worker() throws Exception {
        Field field = SshService.class.getDeclaredField("worker"); field.setAccessible(true);
        return (ScheduledExecutorService)field.get(null);
    }
    static void drained() throws Exception { worker().submit(() -> {}).get(10, TimeUnit.SECONDS); }
    static void watch() throws Exception {
        Method watch = SshService.class.getDeclaredMethod("watch"); watch.setAccessible(true);
        worker().submit(() -> { try { watch.invoke(null); } catch (Exception failure) { throw new RuntimeException(failure); } }).get(10, TimeUnit.SECONDS);
    }
    static void entered() throws Exception { check(SshServerEngine.entered.await(10, TimeUnit.SECONDS), "worker did not reach spy"); }
    static AtomicBoolean flag(String name) throws Exception {
        Field field = SshService.class.getDeclaredField(name); field.setAccessible(true);
        return (AtomicBoolean)field.get(null);
    }
    static void blockedRequest(boolean start) throws Exception {
        CountDownLatch attempting = new CountDownLatch(1);
        AtomicBoolean accepted = new AtomicBoolean(); AtomicReference<Throwable> failure = new AtomicReference<>();
        Thread caller = new Thread(() -> {
            attempting.countDown();
            try { accepted.set(SshService.request(start)); } catch (Throwable thrown) { failure.set(thrown); }
        }, "SSH-request-lock-check");
        caller.setDaemon(true);
        // D8 lowers a synchronized method to monitor instructions, so reflection's
        // modifier is not evidence of missing locking. Exercise the boundary instead.
        synchronized (SshService.class) {
            boolean busy = flag("busy").get(), allowed = flag("startAllowed").get();
            caller.start(); check(attempting.await(10, TimeUnit.SECONDS), "request caller did not run");
            ThreadInfo info = null; long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
            while (caller.isAlive() && System.nanoTime() < deadline) {
                info = ManagementFactory.getThreadMXBean().getThreadInfo(caller.threadId());
                if (info != null && info.getThreadState() == Thread.State.BLOCKED) break;
                Thread.yield();
            }
            check(info != null && info.getThreadState() == Thread.State.BLOCKED && info.getLockInfo() != null &&
                info.getLockInfo().getIdentityHashCode() == System.identityHashCode(SshService.class),
                (start ? "Start" : "Stop") + " did not serialize before worker submission");
            check(flag("busy").get() == busy && flag("startAllowed").get() == allowed,
                "blocked request changed state outside its lock");
        }
        caller.join(10000);
        check(!caller.isAlive() && failure.get() == null && accepted.get(), "serialized request failed: " + failure.get());
    }
    static void beforeSubmission() throws Exception {
        CountDownLatch blocked = new CountDownLatch(1), proceed = new CountDownLatch(1);
        worker().execute(() -> {
            blocked.countDown();
            try { check(proceed.await(10, TimeUnit.SECONDS), "test did not release queued worker"); }
            catch (InterruptedException failure) { throw new RuntimeException(failure); }
        });
        check(blocked.await(10, TimeUnit.SECONDS), "worker did not block");
        SshServerEngine.reset(false, false, false);
        try {
            blockedRequest(true);
            check(flag("busy").get() && flag("startAllowed").get(), "Start was not queued");
            blockedRequest(false);
            check(flag("busy").get() && !flag("startAllowed").get(), "queued Start lost Stop cancellation");
        } finally { proceed.countDown(); }
        drained();
        check(SshServerEngine.configured == 0 && SshServerEngine.started == 0 && !flag("busy").get(),
            "pre-worker cancellation configured a resource or left requests busy");
    }
    public static void main(String[] args) throws Exception {
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby"), ssh = new File(ruby, "ssh"); ssh.mkdirs();
        File marker = new File(ruby, "ssh.enabled"), keys = new File(ssh, "authorized_keys"), safe = new File(ruby, "safe-mode.enabled");
        Files.writeString(keys.toPath(), "fixture keys A");
        SshServerEngine.reset(false, false, false);
        check(!SshService.request(true), "uninstalled SSH started");
        marker.createNewFile();
        check(SshService.installed(), "regular SSH marker under platform files root was refused");
        check(SshServerEngine.configured == 0, "install started a resource automatically");
        check(SshSettings.page("winterx-layout-p/ssh") != null, "SSH native Settings page missing");
        java.util.List<E1.T6> roots = new java.util.ArrayList<>(); roots.add(E1.Z3.c);
        for (Object value : E1.Z3.s) if ("root".equals(((E1.T6)value).a)) roots.add((E1.T6)value);
        check(roots.size() == 2, "native iOS 4/6 roots missing");
        for (E1.T6 root : roots) {
            E1.T6 decorated = winterx.tweaks.TweakSettings.decorate(root); int found = 0;
            for (Object section : decorated.c) for (Object row : ((E1.W6)section).c)
                if ("winterx-layout-p/ssh".equals(((E1.V6)row).a)) found++;
            check(found == 1, "SSH missing/duplicated in native root Settings");
        }
        beforeSubmission();
        SshServerEngine.reset(true, false, false);
        check(SshService.request(true), "start refused"); entered();
        check(SshService.request(false), "busy Stop did not cancel Start");
        SshServerEngine.proceed.countDown(); drained();
        check(SshServerEngine.configured == 1 && SshServerEngine.started == 0 && SshServerEngine.stopped == 1, "cancelled configured resource leaked or bound");
        SshServerEngine.reset(true, false, false);
        SshService.request(true); entered(); Files.writeString(keys.toPath(), "fixture keys B");
        SshServerEngine.proceed.countDown(); drained();
        check(SshServerEngine.started == 0 && SshServerEngine.stopped == 1, "changed keys leaked configured resource");
        SshServerEngine.reset(false, true, false);
        SshService.request(true); entered(); SshService.request(false); SshServerEngine.proceed.countDown(); drained();
        check(SshServerEngine.started == 1 && SshServerEngine.stopped == 1 && !SshService.status().startsWith("Listening"), "Stop during Start left listener active");
        SshServerEngine.reset(false, false, true);
        SshService.request(true); drained(); check(SshServerEngine.stopped == 1, "failed Start leaked resource");
        SshServerEngine.reset(false, false, false);
        SshService.request(true); drained(); check(SshService.status().startsWith("Listening"), "spy start did not complete");
        safe.mkdir(); watch(); check(SshServerEngine.stopped == 1 && !SshService.request(true), "Safe Mode did not stop/refuse service");
        safe.delete(); drained(); check(SshServerEngine.started == 1, "Safe Mode exit automatically restarted");
        SshServerEngine.reset(false, false, false);
        SshService.request(true); drained(); marker.delete(); watch();
        check(SshServerEngine.stopped == 1 && !SshService.request(true), "removal did not stop/refuse service");
        marker.createNewFile(); SshServerEngine.reset(false, false, false);
        SshService.request(true); drained(); Files.writeString(keys.toPath(), "fixture keys C"); watch();
        check(SshServerEngine.stopped == 1, "changed active keys did not stop service");
        check(Files.readString(keys.toPath()).equals("fixture keys C") && !new File(ssh, "host-key.ser").exists(), "service spy rewrote keys");
        SshService.request(false); drained(); SshServerEngine.reset(false, false, false);
        File preservedKeys = new File(ruby, "preserved-keys"); Files.move(keys.toPath(), preservedKeys.toPath());
        Files.createSymbolicLink(keys.toPath(), preservedKeys.toPath()); SshService.request(true); drained();
        check(SshServerEngine.configured == 0 && Files.readString(preservedKeys.toPath()).equals("fixture keys C"), "linked authorized keys configured service");
        Files.delete(keys.toPath()); Files.move(preservedKeys.toPath(), keys.toPath());
        File savedSsh = new File(ruby, "saved-ssh"); Files.move(ssh.toPath(), savedSsh.toPath());
        Files.createSymbolicLink(ssh.toPath(), savedSsh.toPath()); SshService.request(true); drained();
        check(SshServerEngine.configured == 0 && Files.readString(new File(savedSsh, "authorized_keys").toPath()).equals("fixture keys C"), "linked SSH directory configured service");
        Files.delete(ssh.toPath()); Files.move(savedSsh.toPath(), ssh.toPath());
        marker.delete(); Files.createSymbolicLink(marker.toPath(), keys.toPath());
        check(!SshService.installed() && !SshService.request(true), "linked SSH marker enabled service");
        Files.delete(marker.toPath()); Files.createSymbolicLink(marker.toPath(), new File(ruby, "missing-marker").toPath());
        check(!SshService.installed(), "dangling SSH marker enabled service"); Files.delete(marker.toPath()); marker.createNewFile();
        File savedRuby = new File(ruby.getParentFile(), "saved-ruby"); Files.move(ruby.toPath(), savedRuby.toPath());
        Files.createSymbolicLink(ruby.toPath(), savedRuby.toPath());
        check(!SshService.installed() && !SshService.request(true) && SshServerEngine.configured == 0, "linked ruby directory enabled SSH");
        worker().shutdownNow();
        System.out.println("SSH service: native iOS 4/6 rows, serialized Start/Stop, pre-worker/busy cancellation, resource cleanup, Safe Mode/removal/key-change stop and child-link refusal passed at " + ruby.getParentFile().getName() + " (engine spy; no port or shell)");
    }
}
