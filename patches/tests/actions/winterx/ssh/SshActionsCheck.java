package winterx.ssh;

import android.os.Handler;
import com.guille.spring.LauncherActivity;
import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.AbstractExecutorService;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import sun.misc.Unsafe;
import org.json.JSONObject;

/** Actual helper with non-acting native/session/thread-boundary spies and disposable archives. */
public final class SshActionsCheck {
    private static final String ID = "sapp:me.example.fixture", OTHER = "sapp:me.example.other";
    private static final Unsafe UNSAFE;
    static { try { Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true); UNSAFE = (Unsafe)field.get(null); } catch (Exception failure) { throw new ExceptionInInitializerError(failure); } }
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
    static <T> T allocate(Class<T> type) throws Exception { return type.cast(UNSAFE.allocateInstance(type)); }
    static void set(Object target, String name, Object value) throws Exception { Field field = target.getClass().getDeclaredField(name); field.setAccessible(true); field.set(target, value); }
    private static final class NativeQueue extends AbstractExecutorService {
        final BlockingQueue<Runnable> queue = new LinkedBlockingQueue<>(); boolean stopped;
        public void shutdown() { stopped = true; }
        public List<Runnable> shutdownNow() { stopped = true; List<Runnable> pending = new ArrayList<>(); queue.drainTo(pending); return pending; }
        public boolean isShutdown() { return stopped; }
        public boolean isTerminated() { return stopped && queue.isEmpty(); }
        public boolean awaitTermination(long time, TimeUnit unit) { return isTerminated(); }
        public void execute(Runnable run) { if (stopped) throw new java.util.concurrent.RejectedExecutionException(); queue.add(run); }
        void next() throws Exception {
            Runnable run = queue.poll(5, TimeUnit.SECONDS); check(run != null, "fixture native worker did not queue");
            final Throwable[] failure = new Throwable[1];
            Thread thread = new Thread(() -> { android.os.Looper.worker(); try { run.run(); } catch (Throwable problem) { failure[0] = problem; } }, "fixture-native-installer");
            thread.start(); thread.join(10000); check(!thread.isAlive() && failure[0] == null, "fixture native worker failed: " + failure[0]);
        }
    }
    private static String[] done(CompletableFuture<String[]> future, int code) throws Exception {
        String[] result = future.get(10, TimeUnit.SECONDS); check(result.length == 2 && result[0].equals(String.valueOf(code)), "wrong native result: " + Arrays.toString(result)); return result;
    }
    private static CompletableFuture<String[]> request(String verb, String target) { return SshActions.submit(verb, target, "", new AtomicBoolean()); }
    private static JSONObject manifest(String id) throws Exception { return new JSONObject().put("id", id).put("name", "Fixture").put("version", "1.0").put("build", 1).put("minSpring", 8); }
    private static File archive(File inbox, String name, JSONObject json, String extra) throws Exception {
        File file = new File(inbox, name);
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(file.toPath()))) {
            zip.putNextEntry(new ZipEntry("app.json")); zip.write(json.toString().getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
            zip.putNextEntry(new ZipEntry("main.js")); zip.write("// fixture; never executed\n".getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
            if (extra != null) { zip.putNextEntry(new ZipEntry(extra)); zip.write(new byte[]{1, 2, 3}); zip.closeEntry(); }
        }
        return file;
    }
    private static String hash(File file) throws Exception { StringBuilder hex = new StringBuilder(); for (byte value : MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(file.toPath()))) hex.append(String.format("%02x", value & 255)); return hex.toString(); }
    private static void clean(File root) throws Exception {
        File prepared = new File(root, "ruby/ssh/prepared"); File[] files = prepared.listFiles();
        check(files == null || files.length == 0, "private validation snapshot leaked");
    }
    private static void rejectedInstall(File root, File input, LauncherActivity activity, int code) throws Exception {
        CompletableFuture<String[]> future = SshActions.submit("install", input.getName(), hash(input), new AtomicBoolean());
        Handler.next();
        if (!future.isDone()) Handler.next();
        done(future, code); clean(root); check(activity.manager.accepted.size() == 1, "refused archive reached native installer");
    }
    public static void main(String[] args) throws Exception {
        File files = new File(System.getProperty("ruby.test.dir")), inbox = new File(files, "ruby/ssh/inbox"); inbox.mkdirs();
        Map<File, byte[]> protectedFiles = new LinkedHashMap<>();
        for (String name : List.of("ios4_pages.json", "ios6_pages.json", "ruby/freeme-slots-v1.json", "ruby/icon-positions-v1.json", "ruby/animaper.mode", "ruby/ssh/authorized_keys", "ruby/ssh/host-key.ser")) {
            File file = new File(files, name); Files.writeString(file.toPath(), "protected " + name); protectedFiles.put(file, Files.readAllBytes(file.toPath()));
        }
        LauncherActivity activity = new LauncherActivity(); activity.controller = new x1.i1(); activity.manager = new J1.y();
        NativeQueue nativeQueue = new NativeQueue(); activity.manager.i = nativeQueue; activity.manager.g = new J1.P(files);
        activity.controller.C3 = activity.manager; activity.controller.e = allocate(E1.i6.class);
        activity.controller.V1 = allocate(E1.i2.class); set(activity.controller.V1, "c", new LinkedHashMap<String, List<String>>());
        winterx.tweaks.TweakHost.current = activity;
        for (String name : List.of(ID, OTHER)) {
            E1.a app = allocate(E1.a.class); set(app, "a", name); set(app, "b", "Fixture");
            activity.controller.apps.put(name, app); activity.controller.L1.add(new E1.c(app, 1, 2));
            ((Map<String, Object>)activity.manager.k).put(name, new Object()); H1.k.metadata.put(name, new H1.m0(name.substring(5)));
        }
        check(SshActions.available(), "action capability not detected in fixture native boundary");
        SshService.revision = null; done(request("open", ID), 3); check(Handler.queue.isEmpty() && activity.controller.opens.isEmpty(), "unstarted listener dispatched an app");
        SshService.revision = "fixture-session-a";
        done(SshActions.submit("open", "android:com.android.settings", "", new AtomicBoolean()), 2);
        CompletableFuture<String[]> list = request("list", ""); Handler.next(); check(done(list, 0)[1].contains(ID), "registered .sapp list missing");
        CompletableFuture<String[]> open = request("open", ID); check(activity.controller.opens.isEmpty(), "open ran before main-thread dispatch"); Handler.next(); done(open, 0);
        check(activity.controller.opens.equals(List.of(ID)) && activity.controller.actionThread == Thread.currentThread(), "open used wrong native API/thread/target");
        int calls = activity.controller.opens.size(); AtomicBoolean cancel = new AtomicBoolean(); CompletableFuture<String[]> cancelled = SshActions.submit("open", OTHER, "", cancel);
        cancel.set(true); Handler.next(); done(cancelled, 3); check(activity.controller.opens.size() == calls, "cancelled open acted");
        CompletableFuture<String[]> changed = request("open", OTHER); SshService.revision = "fixture-session-b"; Handler.next(); done(changed, 3); check(activity.controller.opens.size() == calls, "changed keys/session acted");
        activity.controller.W1 = allocate(E1.O1.class); CompletableFuture<String[]> editing = request("open", ID); Handler.next(); done(editing, 3); activity.controller.W1 = null;
        activity.controller.k = E1.P6.h; CompletableFuture<String[]> locked = request("open", ID); Handler.next(); done(locked, 3); activity.controller.k = E1.P6.w;
        CompletableFuture<String[]> noActivity = request("open", ID); activity.destroyed = true; Handler.next(); done(noActivity, 3); activity.destroyed = false;
        CompletableFuture<String[]> unknown = request("open", "sapp:me.example.missing"); Handler.next(); done(unknown, 3);
        activity.manager.l.put(ID, new Object()); activity.manager.l.put(OTHER, new Object()); activity.controller.D3.put(ID, new Object());
        CompletableFuture<String[]> close = request("close", ID); Handler.next(); done(close, 0);
        check(activity.controller.closes.equals(List.of(ID)) && activity.manager.destroyed.equals(List.of(ID)) && activity.manager.l.containsKey(OTHER), "close was only Home or affected an unrelated app");
        activity.manager.l.put(ID, new Object()); activity.controller.D3.put(ID, new Object()); activity.controller.k = E1.P6.y; activity.controller.E = ID;
        activity.controller.closeMotion = allocate(E1.H6.class); cancel = new AtomicBoolean();
        CompletableFuture<String[]> foreground = SshActions.submit("close", ID, "", cancel); Handler.next();
        check(activity.controller.transitions.equals(List.of(ID)) && !foreground.isDone() && activity.manager.destroyed.size() == 1, "foreground close did not wait for native transition");
        cancel.set(true); Handler.next(); done(foreground, 3); check(activity.manager.destroyed.size() == 1, "cancelled delayed close destroyed runtime");
        activity.controller.B = null; activity.controller.k = E1.P6.w; activity.controller.closeMotion = null;
        activity.controller.k = E1.P6.y; activity.controller.E = ID; activity.controller.closeMotion = allocate(E1.H6.class);
        CompletableFuture<String[]> foregroundDone = request("close", ID); Handler.next();
        check(!foregroundDone.isDone() && activity.manager.destroyed.size() == 1, "foreground close reported completion before runtime cleanup");
        activity.controller.k = E1.P6.w; activity.controller.E = null; activity.controller.B = null; Handler.next(); done(foregroundDone, 0);
        check(activity.manager.destroyed.size() == 2 && !activity.manager.l.containsKey(ID) && activity.manager.l.containsKey(OTHER), "completed foreground close skipped cleanup or closed another app");
        activity.controller.closeMotion = null;
        // Native V1.c stores P1 records, not raw member lists. Match that real shape.
        List<E1.c> originalPage = new ArrayList<>(activity.controller.L1); activity.controller.L1.remove(0);
        E1.a folder = allocate(E1.a.class); set(folder, "a", "folder:fixture"); activity.controller.L1.add(new E1.c(folder, 0, 3));
        E1.P1 members = allocate(E1.P1.class); set(members, "b", List.of(ID));
        set(activity.controller.V1, "c", new LinkedHashMap<>(Map.of("folder:fixture", members)));
        CompletableFuture<String[]> folderOpen = request("open", ID); Handler.next(); done(folderOpen, 0);
        check(activity.controller.opens.size() == 2, "native P1 folder membership could not open an installed app");
        set(members, "b", List.of(ID, "folder:fixture")); activity.controller.L1.remove(activity.controller.L1.size() - 1);
        CompletableFuture<String[]> cycle = request("open", ID); Handler.next(); done(cycle, 3);
        check(activity.controller.opens.size() == 2, "cyclic folder dispatched a native recursive lookup");
        activity.controller.L1.clear(); activity.controller.L1.addAll(originalPage); set(activity.controller.V1, "c", new LinkedHashMap<>());
        File good = archive(inbox, "Example.sapp", manifest("me.example.newfixture"), null); byte[] source = Files.readAllBytes(good.toPath());
        CompletableFuture<String[]> install = SshActions.submit("install", good.getName(), hash(good), new AtomicBoolean()); Handler.next(); Handler.next();
        check(activity.manager.accepted.isEmpty(), "install ran on main thread or during validation"); nativeQueue.next(); done(install, 0);
        check(activity.manager.accepted.equals(List.of("me.example.newfixture")) && activity.manager.installThread != Thread.currentThread() && Arrays.equals(source, Files.readAllBytes(good.toPath())), "single-archive native dispatch changed source or used wrong thread"); clean(files);
        File existing = archive(inbox, "Existing.sapp", manifest(ID.substring(5)), null); rejectedInstall(files, existing, activity, 3);
        File escape = archive(inbox, "Escape.sapp", manifest("me.example.escape"), "../outside");
        CompletableFuture<String[]> badZip = SshActions.submit("install", escape.getName(), hash(escape), new AtomicBoolean()); Handler.next(); done(badZip, 3); clean(files);
        CompletableFuture<String[]> wrongHash = SshActions.submit("install", good.getName(), "0".repeat(64), new AtomicBoolean()); Handler.next(); done(wrongHash, 3); clean(files);
        File linked = new File(inbox, "Linked.sapp"); Files.createSymbolicLink(linked.toPath(), good.toPath().toAbsolutePath());
        CompletableFuture<String[]> linkedZip = SshActions.submit("install", linked.getName(), hash(good), new AtomicBoolean()); Handler.next(); done(linkedZip, 3); clean(files);
        activity.controller.developer = false; CompletableFuture<String[]> developerOff = SshActions.submit("install", good.getName(), hash(good), new AtomicBoolean()); Handler.next(); done(developerOff, 3); activity.controller.developer = true;
        File protectedDestination = new File(files, "sapps/me.example.newfixture"); protectedDestination.mkdirs(); Files.writeString(new File(protectedDestination, "current").toPath(), "protected native code");
        rejectedInstall(files, good, activity, 3);
        Files.delete(new File(protectedDestination, "current").toPath()); Files.delete(protectedDestination.toPath());
        File existingData = new File(files, "sapps-data/me.example.newfixture"); existingData.mkdirs();
        File userData = new File(existingData, "saved-state"); Files.writeString(userData.toPath(), "preserve removed-app data");
        rejectedInstall(files, good, activity, 3); check(Files.readString(userData.toPath()).equals("preserve removed-app data"), "new install replaced leftover app data");
        Files.delete(userData.toPath()); Files.delete(existingData.toPath());
        CompletableFuture<String[]> changedBeforeCommit = SshActions.submit("install", good.getName(), hash(good), new AtomicBoolean()); Handler.next(); Handler.next();
        SshService.revision = "fixture-session-c"; nativeQueue.next(); done(changedBeforeCommit, 3); clean(files);
        check(activity.manager.accepted.size() == 1, "session-changed native-queued install committed");
        cancel = new AtomicBoolean(); CompletableFuture<String[]> queuedInstall = SshActions.submit("install", good.getName(), hash(good), cancel); Handler.next(); Handler.next();
        queuedInstall.cancel(false); nativeQueue.next(); clean(files); check(activity.manager.accepted.size() == 1, "cancelled native-queued archive installed");
        Handler.reject = true; done(request("open", ID), 3); Handler.reject = false;
        for (Map.Entry<File, byte[]> entry : protectedFiles.entrySet()) check(Arrays.equals(entry.getValue(), Files.readAllBytes(entry.getKey().toPath())), "action changed saved layout/mode/keys: " + entry.getKey().getName());
        check(activity.controller.L1.size() == 2 && activity.controller.L1.get(0).b == 1 && activity.controller.L1.get(0).c == 2 && activity.controller.M1.isEmpty(), "action rewrote saved/native cells or dock");
        check(activity.controller.opens.size() == 2 && activity.manager.destroyed.size() == 2 && activity.manager.accepted.size() == 1 && Handler.queue.isEmpty(), "unexpected native spy action/dispatch");
        nativeQueue.shutdownNow();
        System.out.println("Guarded .sapp helper: main-thread open/close, genuine runtime cleanup, delayed/cancelled close, explicit pinned new-app install, native worker, state/key/session/edit/lock/link/hash/traversal guards and saved layouts/keys/source preservation passed (non-acting native spies)");
    }
}
