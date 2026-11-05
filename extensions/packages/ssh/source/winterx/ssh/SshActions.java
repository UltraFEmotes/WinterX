package winterx.ssh;

import android.app.ActivityThread;
import android.os.Handler;
import android.os.Looper;
import com.guille.spring.LauncherActivity;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import org.json.JSONObject;
import winterx.tweaks.TweakHost;

/** Optional authenticated .sapp adapter. No JavaScript globals, shell, root or Android app control. */
public final class SshActions {
    public static final String ABI = "winterx-spring-app-actions-v1";
    private static final long MAX_ARCHIVE = 40L * 1024 * 1024, MAX_ENTRY = 16L * 1024 * 1024, MAX_EXPANDED = 80L * 1024 * 1024;
    private static final AtomicBoolean installing = new AtomicBoolean();
    private static final ThreadPoolExecutor preparation = new ThreadPoolExecutor(0, 1, 30, TimeUnit.SECONDS,
        new ArrayBlockingQueue<Runnable>(2), run -> { Thread thread = new Thread(run, "WinterX-SSH-archive-check"); thread.setDaemon(true); return thread; },
        new ThreadPoolExecutor.AbortPolicy());
    private SshActions() {}
    private static final class Refused extends IOException { Refused(String reason) { super(reason); } }
    private static String[] result(int code, String text) { return new String[]{String.valueOf(code), text + "\n"}; }
    private static boolean id(String value) { return value != null && value.length() <= 125 && value.matches("sapp:[a-z0-9]+(?:[.-][a-z0-9]+)+"); }
    private static boolean filename(String value) {
        return value != null && value.length() <= 64 && value.matches("[A-Za-z0-9][A-Za-z0-9._-]*\\.sapp") && !value.contains("..");
    }
    public static boolean available() {
        try {
            Class<?> engine = Class.forName("winterx.ssh.SshServerEngine", false, SshActions.class.getClassLoader());
            return "winterx-ssh-app-v1".equals(engine.getField("APP_ABI").get(null)) &&
                LauncherActivity.class.getDeclaredMethod("winterxSappManager").getReturnType() == J1.y.class &&
                J1.y.class.getDeclaredMethod("winterxInstallArchive", File.class).getReturnType() == String.class;
        } catch (Exception | LinkageError unavailable) { return false; }
    }
    private static File root() throws Exception {
        if (ActivityThread.currentApplication() == null) throw new Refused("Application storage unavailable.");
        return ActivityThread.currentApplication().getFilesDir().getCanonicalFile();
    }
    private static boolean safe(File file) throws IOException {
        return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile());
    }
    private static void allowed(String revision, AtomicBoolean cancelled) throws Exception {
        if (cancelled.get()) throw new Refused("Command cancelled before the next action boundary.");
        if (revision == null || !revision.equals(SshService.actionRevision())) throw new Refused("SSH session, keys or enabled state changed. Start explicitly again.");
    }
    private static final class Context {
        final LauncherActivity activity;
        final x1.i1 spring;
        final J1.y manager;
        final File files;
        Context() throws Exception {
            if (Looper.myLooper() != Looper.getMainLooper()) throw new Refused("Native actions require the main thread.");
            activity = TweakHost.launcher();
            if (activity == null || activity.isFinishing() || activity.isDestroyed()) throw new Refused("Unlock the active Spring session first.");
            spring = (x1.i1)LauncherActivity.class.getDeclaredMethod("access$getController$p", LauncherActivity.class).invoke(null, activity);
            manager = (J1.y)LauncherActivity.class.getDeclaredMethod("winterxSappManager").invoke(activity);
            files = root();
            if (spring == null || spring.e == null || manager == null || spring.C3 != manager || manager.i == null ||
                !activity.getFilesDir().getCanonicalFile().equals(files)) throw new Refused("Spring .sapp actions are unavailable in this session/profile.");
            if (spring.k == E1.P6.h || spring.W1 != null) throw new Refused("Unlock Spring and finish home editing first.");
        }
        void home() throws Exception {
            if (spring.k != E1.P6.w || spring.B != null) throw new Refused("Return to an idle Home screen first.");
        }
        void same(Context before) throws Exception {
            if (activity != before.activity || spring != before.spring || manager != before.manager || !files.equals(before.files))
                throw new Refused("The active Spring session changed.");
        }
        void newApp(String appId) throws Exception {
            if (!spring.K0()) throw new Refused("Enable Spring Developer Mode explicitly before installing .sapp apps.");
            if ("com.ruby.manager".equals(appId) || "com.winterx.iexplored".equals(appId)) throw new Refused("Built-in WinterX apps cannot be replaced through this command.");
            if (installed(manager, "sapp:" + appId)) throw new Refused("App already installed. This command never replaces an existing app/build/data.");
            if (manager.g == null) throw new Refused("Native installer storage unavailable.");
            File[] providedRoots = {manager.g.a, manager.g.b}; String[] nativeNames = {"sapps", "sapps-data"};
            for (int index = 0; index < providedRoots.length; index++) {
                File provided = providedRoots[index];
                File parent = nativeRoot(provided, activity.getFilesDir(), files);
                if (!parent.equals(new File(files, nativeNames[index]))) throw new Refused("Unexpected native app storage root.");
                File destination = new File(parent, appId);
                if (!safe(destination) || Files.exists(destination.toPath(), LinkOption.NOFOLLOW_LINKS))
                    throw new Refused("Existing or linked native app storage is protected.");
            }
        }
    }
    private static File nativeRoot(File provided, File platformAlias, File canonicalRoot) throws Exception {
        if (provided == null) throw new Refused("Native app storage unavailable.");
        Path raw = platformAlias.toPath().toAbsolutePath(), path = provided.toPath().toAbsolutePath();
        File normalized;
        if (path.startsWith(raw)) normalized = new File(canonicalRoot, raw.relativize(path).toString());
        else if (path.startsWith(canonicalRoot.toPath())) normalized = provided;
        else throw new Refused("Native app storage is outside the application files root.");
        if (!safe(normalized) || !provided.getCanonicalFile().equals(normalized.getAbsoluteFile())) throw new Refused("Native app storage links refused.");
        return normalized;
    }
    private static boolean installed(J1.y manager, String target) {
        return manager.k instanceof Map && ((Map<?, ?>)manager.k).containsKey(target) || manager.d().containsKey(target) || H1.k.b(target) != null;
    }
    private static boolean running(Context context, String target) {
        return context.manager.l.containsKey(target) || context.manager.m.containsKey(target) || context.manager.r.contains(target) || context.spring.D3.containsKey(target);
    }
    private static String listing(Context context) throws Exception {
        Set<String> names = new TreeSet<>();
        List<Map<?, ?>> maps = new ArrayList<>();
        if (context.manager.k instanceof Map) maps.add((Map<?, ?>)context.manager.k);
        maps.add(context.manager.d());
        for (Map<?, ?> map : maps) {
            if (map.size() > 512) throw new Refused("Installed-app inventory exceeds the bounded action limit.");
            for (Object name : map.keySet()) if (name instanceof String && id((String)name)) names.add((String)name);
        }
        if (names.size() > 96) throw new Refused("At most 96 .sapp apps can be listed in one bounded response.");
        StringBuilder out = new StringBuilder("Spring .sapp apps (not Android packages):\n");
        for (String name : names) out.append(name).append(running(context, name) ? "\trunning\n" : "\tstopped\n");
        if (names.isEmpty()) out.append("No registered .sapp apps.\n");
        return out.toString().trim();
    }
    private static boolean direct(x1.i1 spring, String target) throws Exception {
        if (spring.L1 == null || spring.S1 == null || spring.M1 == null || spring.L1.size() > 100 || spring.S1.size() > 100 || spring.M1.size() > 7)
            throw new Refused("Native launch model exceeds its bounded limits.");
        List<List<?>> pages = new ArrayList<>(); pages.add(spring.L1);
        for (Object page : spring.S1) {
            if (!(page instanceof List) || ((List<?>)page).size() > 100) throw new Refused("Invalid native launch page.");
            pages.add((List<?>)page);
        }
        for (List<?> page : pages) for (Object object : page)
            if (object instanceof E1.c && ((E1.c)object).a != null && target.equals(((E1.c)object).a.a)) return true;
        for (Object object : spring.M1) if (object instanceof E1.a && target.equals(((E1.a)object).a)) return true;
        return false;
    }
    private static boolean placed(x1.i1 spring, String target) throws Exception {
        String current = target; Set<String> visited = new HashSet<>();
        Map<?, ?> folders = spring.V1 == null ? java.util.Collections.emptyMap() : spring.V1.c;
        if (folders == null || folders.size() > 128) throw new Refused("Invalid bounded native folder model.");
        for (int depth = 0; depth < 16; depth++) {
            if (direct(spring, current)) return true;
            if (!visited.add(current)) throw new Refused("Cyclic native folder launch location refused.");
            String parent = null;
            for (Map.Entry<?, ?> folder : folders.entrySet()) {
                if (!(folder.getKey() instanceof String) || !(folder.getValue() instanceof E1.P1))
                    throw new Refused("Invalid native folder membership.");
                List<?> members = ((E1.P1)folder.getValue()).b;
                if (members == null || members.size() > 100) throw new Refused("Invalid native folder membership.");
                if (members.contains(current)) { parent = (String)folder.getKey(); break; }
            }
            if (parent == null) return false;
            current = parent;
        }
        throw new Refused("Native folder launch depth exceeds its limit.");
    }
    public static CompletableFuture<String[]> submit(String verb, String target, String sha256, AtomicBoolean cancelled) {
        CompletableFuture<String[]> future = new CompletableFuture<>();
        boolean valid = cancelled != null && verb != null && target != null && sha256 != null &&
            (verb.equals("list") && target.isEmpty() && sha256.isEmpty() ||
             (verb.equals("open") || verb.equals("close")) && id(target) && sha256.isEmpty() ||
             verb.equals("install") && filename(target) && sha256.matches("[0-9a-f]{64}"));
        if (!valid) { future.complete(result(2, "Invalid bounded Spring-app request.")); return future; }
        future.whenComplete((value, failure) -> { if (future.isCancelled()) cancelled.set(true); });
        if (!available()) { future.complete(result(3, "This engine does not contain the guarded Spring-app action hooks.")); return future; }
        String revision = SshService.actionRevision();
        try {
            allowed(revision, cancelled); Handler main = new Handler(Looper.getMainLooper());
            if (!main.post(() -> {
                try {
                    allowed(revision, cancelled); Context context = new Context();
                    if (verb.equals("list")) { future.complete(result(0, listing(context))); return; }
                    if (verb.equals("install")) { context.home(); install(context, main, revision, target, sha256, cancelled, future); return; }
                    if (!installed(context.manager, target)) throw new Refused("Unknown installed .sapp ID.");
                    if (context.spring.B != null) throw new Refused("Wait for the current native transition to finish.");
                    if (verb.equals("open")) {
                        context.home();
                        if (!placed(context.spring, target)) throw new Refused("App has no native Home/dock/folder launch location.");
                        E1.a app = context.spring.s2(target); E1.A0 location = context.spring.m4(target);
                        if (app == null || !target.equals(app.a) || location == null) throw new Refused("App has no native Home/dock/folder launch location.");
                        allowed(revision, cancelled); context.spring.R2(location, app);
                        future.complete(result(0, "Native open requested for " + target + "."));
                    } else if (!running(context, target)) future.complete(result(0, target + " is already stopped."));
                    else if (context.spring.k == E1.P6.y && target.equals(context.spring.E)) {
                        placed(context.spring, target); // Validate bounded folder traversal before native N/m4.
                        allowed(revision, cancelled);
                        if (!context.spring.N(target, false)) throw new Refused("Native close transition was refused.");
                        finishClose(context, main, revision, target, cancelled, future, 40);
                    } else { allowed(revision, cancelled); closeRuntime(context, target); future.complete(result(0, "Native runtime close requested for " + target + ".")); }
                } catch (Exception refused) { fail(future, refused); }
            })) throw new Refused("Native main-thread dispatch unavailable.");
        } catch (Exception refused) { fail(future, refused); }
        return future;
    }
    private static void closeRuntime(Context context, String target) {
        context.spring.Q3(target); context.manager.i(target); // Idempotent native cleanup; not Home, uninstall, or process kill.
    }
    private static void finishClose(Context before, Handler main, String revision, String target, AtomicBoolean cancelled, CompletableFuture<String[]> future, int remaining) {
        try {
            allowed(revision, cancelled); Context context = new Context(); context.same(before);
            if (context.spring.B == null && !(context.spring.k == E1.P6.y && target.equals(context.spring.E))) {
                closeRuntime(context, target); future.complete(result(0, "Native runtime close requested for " + target + ".")); return;
            }
            if (remaining == 0) throw new Refused("Close transition is still in progress; runtime was not destroyed. No automatic retry.");
            if (!main.postDelayed(() -> finishClose(before, main, revision, target, cancelled, future, remaining - 1), 100))
                throw new Refused("Native close completion dispatch unavailable.");
        } catch (Exception refused) { fail(future, refused); }
    }
    private static void fail(CompletableFuture<String[]> future, Exception failure) {
        future.complete(result(3, failure instanceof Refused ? failure.getMessage() : "Native app action or archive validation was refused."));
    }
    private static final class Prepared {
        final File file;
        final String appId;
        Prepared(File file, String appId) { this.file = file; this.appId = appId; }
    }
    private static final class Install {
        final AtomicInteger phase = new AtomicInteger(); // 0 reading, 1 queued, 2 native commit, 3 completed/cancelled
        final AtomicBoolean released = new AtomicBoolean();
        volatile Prepared prepared;
        void cleanup() {
            if (!released.compareAndSet(false, true)) return;
            if (prepared != null) try { if (safe(prepared.file)) Files.deleteIfExists(prepared.file.toPath()); } catch (IOException ignored) {}
            installing.set(false);
        }
        void cancelQueued() { if (phase.compareAndSet(1, 3)) cleanup(); }
    }
    private static void installReady(Context current, String appId, String revision, AtomicBoolean cancelled) throws Exception {
        allowed(revision, cancelled);
        if (TweakHost.launcher() != current.activity || current.activity.isFinishing() || current.activity.isDestroyed() || !root().equals(current.files) ||
            current.spring.W1 != null || current.spring.B != null || current.spring.k != E1.P6.w || !current.spring.K0())
            throw new Refused("Native session, Home or Developer Mode changed before install commit.");
        current.newApp(appId);
    }
    private static void install(Context before, Handler main, String revision, String filename, String sha256, AtomicBoolean cancelled, CompletableFuture<String[]> future) throws Exception {
        if (!before.spring.K0()) throw new Refused("Enable Spring Developer Mode explicitly before installing .sapp apps.");
        if (!installing.compareAndSet(false, true)) { future.complete(result(4, "An archive request is already pending. No automatic retry.")); return; }
        Install operation = new Install();
        future.whenComplete((value, failure) -> { if (future.isCancelled()) { cancelled.set(true); operation.cancelQueued(); } });
        try {
            preparation.execute(() -> {
                try {
                    allowed(revision, cancelled); operation.prepared = prepare(before.files, filename, sha256, revision, cancelled);
                    operation.phase.set(1);
                    if (cancelled.get() || future.isCancelled()) { operation.cancelQueued(); return; }
                    if (!main.post(() -> {
                        try {
                            allowed(revision, cancelled); Context current = new Context(); current.same(before); current.home(); current.newApp(operation.prepared.appId);
                            current.manager.i.execute(() -> {
                                String[] response = null;
                                try {
                                    allowed(revision, cancelled);
                                    if (!operation.phase.compareAndSet(1, 2)) return;
                                    installReady(current, operation.prepared.appId, revision, cancelled);
                                    if (!sha256.equals(hash(operation.prepared.file, revision, cancelled))) throw new Refused("Prepared archive checksum changed.");
                                    installReady(current, operation.prepared.appId, revision, cancelled);
                                    String installed = (String)J1.y.class.getDeclaredMethod("winterxInstallArchive", File.class).invoke(current.manager, operation.prepared.file);
                                    if (!operation.prepared.appId.equals(installed)) throw new Refused("Native installer returned an unexpected app ID.");
                                    response = result(0, "Native installer accepted sapp:" + installed + ". Availability refresh is pending; no app was opened.");
                                } catch (Exception refused) { response = result(3, refused instanceof Refused ? refused.getMessage() : "Native app action or archive validation was refused."); }
                                finally { operation.phase.set(3); operation.cleanup(); }
                                if (response != null) future.complete(response);
                            });
                        } catch (Exception refused) { operation.phase.set(3); operation.cleanup(); fail(future, refused); }
                    })) throw new Refused("Native install dispatch unavailable.");
                } catch (Exception refused) { operation.phase.set(3); operation.cleanup(); fail(future, refused); }
            });
        } catch (RuntimeException busy) { operation.cleanup(); throw new Refused("Archive validation queue unavailable."); }
    }
    private static Prepared prepare(File root, String filename, String expected, String revision, AtomicBoolean cancelled) throws Exception {
        File inbox = new File(root, "ruby/ssh/inbox"), source = new File(inbox, filename), dir = new File(root, "ruby/ssh/prepared");
        if (!safe(inbox) || !inbox.isDirectory() || !safe(source) || !source.isFile() || source.length() <= 0 || source.length() > MAX_ARCHIVE)
            throw new Refused("Supply one complete bounded .sapp in ruby/ssh/inbox; links are refused.");
        if (!safe(dir) || (dir.exists() && !dir.isDirectory()) || (!dir.isDirectory() && !dir.mkdir())) throw new Refused("Private archive validation storage unavailable.");
        BasicFileAttributes before = Files.readAttributes(source.toPath(), BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        File copy = File.createTempFile(".ssh-app-", ".sapp", dir); boolean retained = false;
        try {
            MessageDigest hash = MessageDigest.getInstance("SHA-256"); long count = 0; byte[] buffer = new byte[65536];
            try (InputStream input = Files.newInputStream(source.toPath(), LinkOption.NOFOLLOW_LINKS); FileOutputStream output = new FileOutputStream(copy)) {
                for (int read; (read = input.read(buffer)) != -1;) {
                    allowed(revision, cancelled); count += read; if (count > MAX_ARCHIVE) throw new Refused("Archive exceeds 40 MiB.");
                    hash.update(buffer, 0, read); output.write(buffer, 0, read);
                }
                output.getFD().sync();
            }
            BasicFileAttributes after = Files.readAttributes(source.toPath(), BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            if (!safe(source) || before.size() != count || after.size() != count || !before.lastModifiedTime().equals(after.lastModifiedTime()) ||
                !java.util.Objects.equals(before.fileKey(), after.fileKey()) || !expected.equals(hex(hash.digest()))) throw new Refused("Archive is incomplete, changed, or its explicit checksum does not match.");
            JSONObject manifest = validate(copy, revision, cancelled);
            String appId = manifest.getString("id");
            if (!appId.equals(H1.Q.h(copy).a)) throw new Refused("Native archive metadata disagrees with the validated app ID.");
            retained = true; return new Prepared(copy, appId);
        } finally { if (!retained && safe(copy)) Files.deleteIfExists(copy.toPath()); }
    }
    private static JSONObject validate(File archive, String revision, AtomicBoolean cancelled) throws Exception {
        Set<String> names = new HashSet<>(); byte[] manifest = null; long expanded = 0; boolean script = false;
        try (ZipFile zip = new ZipFile(archive)) {
            Enumeration<? extends ZipEntry> entries = zip.entries(); byte[] buffer = new byte[65536];
            while (entries.hasMoreElements()) {
                allowed(revision, cancelled); ZipEntry entry = entries.nextElement(); String name = entry.getName();
                String key = name.endsWith("/") ? name.substring(0, name.length() - 1) : name;
                if (names.size() >= 1024 || name.length() > 240 || key.isEmpty() || name.startsWith("/") || name.contains("\\") || !names.add(key))
                    throw new Refused("Duplicate, unsafe, or excessive archive paths.");
                for (String part : key.split("/", -1)) if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new Refused("Archive path traversal refused.");
                for (int i = 0; i < name.length(); i++) if (name.charAt(i) < 32 || name.charAt(i) > 126) throw new Refused("Archive path controls refused.");
                if (entry.isDirectory()) continue;
                if (entry.getSize() < 0 || entry.getSize() > MAX_ENTRY || (expanded += entry.getSize()) > MAX_EXPANDED) throw new Refused("Archive expansion exceeds its limit.");
                long size = 0; ByteArrayOutputStream capture = name.equals("app.json") ? new ByteArrayOutputStream() : null;
                byte[] png = name.equals("icon.png") ? new byte[24] : null; int pngCount = 0;
                java.util.zip.CRC32 crc = new java.util.zip.CRC32();
                try (InputStream input = zip.getInputStream(entry)) {
                    for (int read; (read = input.read(buffer)) != -1;) {
                        allowed(revision, cancelled); size += read;
                        crc.update(buffer, 0, read);
                        if (size > MAX_ENTRY || capture != null && size > 65536) throw new Refused("Archive entry or manifest exceeds its limit.");
                        if (capture != null) capture.write(buffer, 0, read);
                        if (png != null && pngCount < png.length) { int take = Math.min(read, png.length - pngCount); System.arraycopy(buffer, 0, png, pngCount, take); pngCount += take; }
                    }
                }
                if (size != entry.getSize() || crc.getValue() != entry.getCrc()) throw new Refused("Archive entry size/checksum changed.");
                if (capture != null) manifest = capture.toByteArray();
                if (name.equals("main.js")) script = true;
                if (png != null) {
                    byte[] magic = {(byte)137, 80, 78, 71, 13, 10, 26, 10};
                    int width = java.nio.ByteBuffer.wrap(png, 16, 4).getInt(), height = java.nio.ByteBuffer.wrap(png, 20, 4).getInt();
                    if (pngCount != 24 || !Arrays.equals(Arrays.copyOf(png, 8), magic) || java.nio.ByteBuffer.wrap(png, 8, 4).getInt() != 13 ||
                        png[12] != 'I' || png[13] != 'H' || png[14] != 'D' || png[15] != 'R' || width < 1 || height < 1 || width > 1024 || height > 1024)
                        throw new Refused("Native app icon must be a bounded PNG (up to 1024 x 1024).");
                }
            }
        }
        if (manifest == null || !script) throw new Refused("A JavaScript .sapp needs top-level app.json and main.js.");
        JSONObject json = new JSONObject(new String(manifest, StandardCharsets.UTF_8)); Object appId = json.get("id"), build = json.get("build");
        if (!(appId instanceof String) || !id("sapp:" + appId) || !(build instanceof Number) || ((Number)build).doubleValue() != ((Number)build).intValue() ||
            ((Number)build).intValue() < 1 || ((Number)build).intValue() > 1000000 || json.getString("name").length() > 120 || json.getString("version").length() > 32)
            throw new Refused("Invalid bounded native app metadata.");
        Object minimum = json.opt("minSpring");
        if (minimum != null && (!(minimum instanceof Number) || ((Number)minimum).doubleValue() != ((Number)minimum).intValue() ||
            ((Number)minimum).intValue() < 0 || ((Number)minimum).intValue() > 8)) throw new Refused("This archive requires a different Spring version; only 0.8.1 is supported.");
        return json;
    }
    private static String hash(File file, String revision, AtomicBoolean cancelled) throws Exception {
        if (!safe(file) || !file.isFile() || file.length() > MAX_ARCHIVE) throw new Refused("Prepared archive is no longer valid.");
        MessageDigest digest = MessageDigest.getInstance("SHA-256"); byte[] buffer = new byte[65536]; long total = 0;
        try (InputStream input = Files.newInputStream(file.toPath(), LinkOption.NOFOLLOW_LINKS)) {
            for (int count; (count = input.read(buffer)) != -1;) { allowed(revision, cancelled); total += count; if (total > MAX_ARCHIVE) throw new Refused("Prepared archive grew."); digest.update(buffer, 0, count); }
        }
        return hex(digest.digest());
    }
    private static String hex(byte[] bytes) { StringBuilder value = new StringBuilder(); for (byte b : bytes) value.append(String.format(java.util.Locale.US, "%02x", b & 255)); return value.toString(); }
}
