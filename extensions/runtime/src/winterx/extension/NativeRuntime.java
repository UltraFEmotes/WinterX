package winterx.extension;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONObject;

/** Generic, source-backed native extension loader. No built-in tweak implementation is linked here. */
public final class NativeRuntime {
    public static final String ABI = "winterx-native-hooks-v1";
    private static final int MAX_PACKAGES = 16, MAX_MANIFEST = 128 * 1024, MAX_CODE = 16 * 1024 * 1024;
    private static final Map<String, Package> PACKAGES = new LinkedHashMap<>();
    private static final java.util.WeakHashMap<Object, List<Package>> TRANSACTIONS = new java.util.WeakHashMap<>();
    private static volatile File filesRoot;
    private static boolean initialized;
    private static final ScheduledExecutorService WATCHER = Executors.newSingleThreadScheduledExecutor(run -> {
        Thread thread = new Thread(run, "WinterX-native-package-watch"); thread.setDaemon(true); return thread;
    });
    private NativeRuntime() {}
    static final class Lease {
        final Package owner;
        final Object value;
        Lease(Package owner, Object value) { this.owner = owner; this.value = value; }
    }
    private static final class Package {
        final String id, revision;
        final File root;
        final JSONObject manifest;
        final List<String> exports, dependencies;
        final NativeTweak implementation;
        final ClassLoader loader;
        volatile boolean active = true;
        Package(String id, String revision, File root, JSONObject manifest, List<String> exports, List<String> dependencies, NativeTweak implementation, ClassLoader loader) {
            this.id = id; this.revision = revision; this.root = root; this.manifest = manifest; this.exports = exports;
            this.dependencies = dependencies;
            this.implementation = implementation; this.loader = loader;
        }
    }
    private static boolean safe(File file) throws IOException {
        return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile());
    }
    public static boolean safeMode() {
        File root = filesRoot;
        return root == null || Files.exists(new File(root, "ruby/safe-mode.enabled").toPath(), LinkOption.NOFOLLOW_LINKS);
    }
    public static File files() { return filesRoot; }
    private static String text(File file, int limit) throws IOException {
        if (!safe(file) || !file.isFile() || file.length() > limit) throw new IOException("Invalid bounded extension file");
        byte[] bytes = new byte[(int)file.length()];
        try (FileInputStream input = new FileInputStream(file)) {
            int offset = 0;
            while (offset < bytes.length) { int read = input.read(bytes, offset, bytes.length - offset); if (read < 0) throw new IOException("Truncated extension file"); offset += read; }
            if (input.read() != -1) throw new IOException("Extension file changed while reading");
        }
        return new String(bytes, StandardCharsets.UTF_8);
    }
    private static String digest(File file, int limit) throws Exception {
        if (!safe(file) || !file.isFile() || file.length() > limit) throw new IOException("Invalid extension code path");
        MessageDigest hash = MessageDigest.getInstance("SHA-256"); byte[] buffer = new byte[65536]; long total = 0;
        try (FileInputStream input = new FileInputStream(file)) {
            for (int read; (read = input.read(buffer)) >= 0;) { total += read; if (total > limit) throw new IOException("Extension exceeds its bound"); hash.update(buffer, 0, read); }
        }
        StringBuilder value = new StringBuilder(); for (byte b : hash.digest()) value.append(String.format(java.util.Locale.ROOT, "%02x", b & 255)); return value.toString();
    }
    public static synchronized void initialize(File suppliedFiles) {
        if (initialized) return;
        try {
            filesRoot = suppliedFiles.getCanonicalFile();
            initialized = true;
            File root = new File(filesRoot, "winterx-tweaks");
            if (!safe(root) || !root.isDirectory() || safeMode()) return;
            File[] children = root.listFiles(); if (children == null) return; Arrays.sort(children);
            Map<String, File> roots = new LinkedHashMap<>();
            Map<String, JSONObject> pending = new LinkedHashMap<>();
            for (File child : children) {
                if (pending.size() >= MAX_PACKAGES) break;
                if (child.getName().length() > 120 || !child.getName().matches("[a-z0-9]+(?:[.-][a-z0-9]+)+") || !safe(child) || !child.isDirectory()) continue;
                try {
                    File enabled = new File(child, "enabled");
                    if (!safe(enabled) || !enabled.isFile()) continue;
                    JSONObject manifest = new JSONObject(text(new File(child, "manifest.json"), MAX_MANIFEST));
                    if (!"winterx.springys/3".equals(manifest.optString("format"))) continue;
                    roots.put(child.getName(), child); pending.put(child.getName(), manifest);
                } catch (Throwable failure) { error(child, failure); }
            }
            while (!pending.isEmpty()) {
                boolean progressed = false;
                for (String id : new ArrayList<>(pending.keySet())) {
                    try {
                        List<String> dependencies = dependencies(pending.get(id), id);
                        boolean waiting = false;
                        for (String dependency : dependencies) {
                            if (pending.containsKey(dependency)) waiting = true;
                            else if (!enabled(dependency)) throw new IOException("Native dependency is missing or inactive: " + dependency);
                        }
                        if (waiting) continue;
                        load(roots.get(id), pending.get(id), dependencies);
                    } catch (Throwable failure) { error(roots.get(id), failure); }
                    pending.remove(id); progressed = true;
                }
                if (!progressed) {
                    for (String id : pending.keySet()) error(roots.get(id), new IOException("Native dependency cycle"));
                    break;
                }
            }
            WATCHER.scheduleWithFixedDelay(NativeRuntime::watch, 250, 250, TimeUnit.MILLISECONDS);
            try { SappInjection.install(); } catch (Throwable unavailable) { /* Apps still run without injected scripts. */ }
        } catch (Throwable unavailable) { /* Recovery/stock drawing must remain possible. */ }
    }
    private static List<String> dependencies(JSONObject manifest, String id) throws Exception {
        JSONArray requested = manifest.has("requires") ? manifest.getJSONArray("requires") : new JSONArray();
        if (requested.length() > MAX_PACKAGES) throw new IOException("Too many native dependencies");
        List<String> result = new ArrayList<>();
        for (int i = 0; i < requested.length(); i++) {
            String dependency = requested.getString(i);
            if (dependency.length() > 120 || !dependency.matches("[a-z0-9]+(?:[.-][a-z0-9]+)+") || dependency.equals(id) || result.contains(dependency))
                throw new IOException("Invalid native dependency");
            result.add(dependency);
        }
        return Collections.unmodifiableList(result);
    }
    private static void load(File root, JSONObject manifest, List<String> dependencies) throws Exception {
        String id = root.getName(); File marker = new File(root, "enabled");
        if (!safe(marker) || !marker.isFile() || safeMode()) return;
        if (!id.equals(manifest.optString("id")) || !"tweak".equals(manifest.optString("type")) ||
            !"java".equals(manifest.optString("runtime")) || !"winterx.native/1".equals(manifest.optString("api"))) throw new IOException("Unsupported native package ABI");
        String revision = text(new File(root, "manifest.sha256"), 80).trim();
        if (!revision.matches("[0-9a-f]{64}") || !revision.equals(digest(new File(root, "manifest.json"), MAX_MANIFEST))) throw new IOException("Extension manifest checksum mismatch");
        JSONArray requested = manifest.getJSONArray("exports");
        if (requested.length() < 1 || requested.length() > 128) throw new IOException("Invalid extension exports");
        List<String> exports = new ArrayList<>();
        for (int i = 0; i < requested.length(); i++) {
            String point = requested.getString(i);
            if (!point.matches("[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+") || exports.contains(point)) throw new IOException("Invalid extension export");
            exports.add(point);
        }
        String entry = manifest.getString("entry");
        if (!entry.matches("[A-Za-z_$][\\w$]*(?:\\.[A-Za-z_$][\\w$]*)+") || entry.startsWith("winterx.extension.")) throw new IOException("Invalid extension entry class");
        JSONObject payloads = manifest.getJSONObject("files");
        boolean android = "Dalvik".equals(System.getProperty("java.vm.name")) || "ART".equals(System.getProperty("java.vm.name"));
        String relative = android ? "code/classes.dex" : "code/classes.jar", expected = payloads.getString(relative);
        if (!expected.matches("[0-9a-f]{64}")) throw new IOException("Invalid code checksum");
        File source = new File(root, relative);
        if (!expected.equals(digest(source, MAX_CODE))) throw new IOException("Extension code checksum mismatch");
        File cache = new File(filesRoot, "ruby/native-cache");
        if (!safe(cache) || !cache.isDirectory() && !cache.mkdirs() || !safe(cache)) throw new IOException("Extension cache unavailable");
        File immutable = new File(cache, expected + (android ? ".dex" : ".jar"));
        if (immutable.exists()) {
            if (!expected.equals(digest(immutable, MAX_CODE))) throw new IOException("Existing code cache failed integrity check");
        } else {
            File temporary = File.createTempFile(".native-code-", ".tmp", cache);
            try {
                try (FileInputStream input = new FileInputStream(source); FileOutputStream output = new FileOutputStream(temporary)) {
                    byte[] bytes = new byte[65536]; long copied = 0;
                    for (int n; (n = input.read(bytes)) >= 0;) { copied += n; if (copied > MAX_CODE) throw new IOException("Extension grew while copying"); output.write(bytes, 0, n); }
                    output.getFD().sync();
                }
                if (!expected.equals(digest(temporary, MAX_CODE)) || !temporary.setReadOnly() || !temporary.renameTo(immutable)) throw new IOException("Could not freeze extension code");
            } finally { if (temporary.exists()) temporary.delete(); }
        }
        ClassLoader parent = NativeRuntime.class.getClassLoader(), loader;
        if (android) {
            loader = (ClassLoader)Class.forName("dalvik.system.DexClassLoader").getConstructor(String.class, String.class, String.class, ClassLoader.class)
                .newInstance(immutable.getPath(), cache.getPath(), null, parent);
        } else loader = new URLClassLoader(new URL[]{immutable.toURI().toURL()}, parent);
        Class<?> type = Class.forName(entry, true, loader);
        if (type.getClassLoader() != loader || !NativeTweak.class.isAssignableFrom(type)) throw new IOException("Extension entry did not implement the public ABI");
        NativeTweak implementation = (NativeTweak)type.getDeclaredConstructor().newInstance();
        Package pkg = new Package(id, revision, root, manifest, Collections.unmodifiableList(exports), dependencies, implementation, loader);
        PACKAGES.put(id, pkg);
        try {
            implementation.start(new TweakContext(id, filesRoot));
            File previousError = new File(root, "last-error.txt");
            if (safe(previousError) && previousError.isFile()) previousError.delete();
        }
        catch (Throwable failure) { disable(pkg, failure); }
    }
    private static boolean current(Package pkg) {
        try {
            File enabled = new File(pkg.root, "enabled");
            if (!pkg.active || safeMode() || !safe(pkg.root) || !safe(enabled) || !enabled.isFile() ||
                !pkg.revision.equals(text(new File(pkg.root, "manifest.sha256"), 80).trim())) return false;
            for (String dependency : pkg.dependencies) {
                Package required = PACKAGES.get(dependency);
                if (required == null || !current(required)) return false;
            }
            return true;
        } catch (Exception unavailable) { return false; }
    }
    private static final Map<String, long[]> LIVE = new java.util.concurrent.ConcurrentHashMap<>();
    /** enabled(id) for hot paths: the on-disk state is rechecked at most once a second. */
    static boolean live(String id) {
        long now = android.os.SystemClock.uptimeMillis();
        long[] cached = LIVE.get(id);
        if (cached != null && now - cached[0] < 1000) return cached[1] != 0;
        boolean value = enabled(id);
        LIVE.put(id, new long[]{now, value ? 1 : 0});
        return value;
    }
    public static synchronized boolean enabled(String id) { Package pkg = PACKAGES.get(id); return pkg != null && current(pkg); }
    public static synchronized boolean supports(String point) { for (Package pkg : PACKAGES.values()) if (current(pkg) && pkg.exports.contains(point)) return true; return false; }
    public static synchronized JSONObject manifest(String id) { Package pkg = PACKAGES.get(id); return pkg != null && current(pkg) ? pkg.manifest : null; }
    public static synchronized List<JSONObject> manifests() { List<JSONObject> result = new ArrayList<>(); for (Package pkg : PACKAGES.values()) if (current(pkg)) result.add(pkg.manifest); return result; }
    public static synchronized List<String> features() {
        List<String> result = new ArrayList<>();
        for (Package pkg : PACKAGES.values()) if (current(pkg)) {
            JSONArray values = pkg.manifest.optJSONArray("features");
            if (values != null) for (int i = 0; i < Math.min(values.length(), 32); i++) {
                String value = values.optString(i); if (!result.contains(value)) result.add(value);
            }
        }
        return result;
    }
    public static Object settingsPage(String pageId) {
        if (pageId == null || !pageId.startsWith("winterx-tw-p/")) return null;
        String[] parts = pageId.substring("winterx-tw-p/".length()).split("/", 2);
        Package pkg;
        synchronized (NativeRuntime.class) { pkg = PACKAGES.get(parts[0]); }
        if (pkg == null || !current(pkg) || !pkg.exports.contains("settings.page")) return null;
        try { return pkg.implementation.call("settings.page", new Object[]{parts.length == 1 ? pkg.manifest.optString("settings_entry", "main") : parts[1]}); }
        catch (Throwable failure) { disable(pkg, failure); return null; }
    }
    public static boolean settingsTap(String rowId) {
        if (rowId == null || !rowId.startsWith("winterx-tw-r/")) return false;
        String[] parts = rowId.substring("winterx-tw-r/".length()).split("/", -1);
        if (parts.length != 3) return false;
        Package pkg;
        synchronized (NativeRuntime.class) { pkg = PACKAGES.get(parts[0]); }
        if (pkg == null || !current(pkg) || !pkg.exports.contains("settings.tap")) return false;
        try { pkg.implementation.call("settings.tap", new Object[]{parts[1], parts[2]}); }
        catch (Throwable failure) { disable(pkg, failure); }
        return true;
    }
    public static Object dispatch(String point, Object[] arguments, Object fallback, String policy, boolean cleanup, Class<?> expected) {
        List<Package> selected;
        synchronized (NativeRuntime.class) { selected = new ArrayList<>(PACKAGES.values()); }
        Object result = fallback;
        for (Package pkg : selected) {
            if (!pkg.exports.contains(point) || !cleanup && !current(pkg)) continue;
            try {
                Object value = pkg.implementation.call(point, arguments);
                if (value != null && expected != null && !expected.isInstance(value)) throw new IOException("Extension returned the wrong hook type");
                if ("all".equals(policy)) continue;
                if ("and".equals(policy)) { if (Boolean.FALSE.equals(value)) return false; continue; }
                if ("or".equals(policy)) { if (Boolean.TRUE.equals(value)) return true; continue; }
                if (value != null) return value;
            } catch (Throwable failure) { disable(pkg, failure); }
        }
        return result;
    }
    static Lease open(String point, Object[] arguments, Class<?> expected) {
        List<Package> selected;
        synchronized (NativeRuntime.class) { selected = new ArrayList<>(PACKAGES.values()); }
        for (Package pkg : selected) {
            if (!pkg.exports.contains(point) || !current(pkg)) continue;
            try {
                Object value = pkg.implementation.call(point, arguments);
                if (value == null) continue;
                if (expected != null && !expected.isInstance(value)) throw new IOException("Invalid native drawing scope type");
                return new Lease(pkg, value);
            } catch (Throwable failure) { disable(pkg, failure); return null; }
        }
        return null;
    }
    /** Stacked scopes: each exporting package opens its own lease. A rejected or failed one is disabled and the canvas reset to before it. */
    static List<Lease> openAll(String point, Object[] arguments, Class<?> expected, java.util.function.Predicate<Lease> valid, Runnable reset) {
        List<Package> selected;
        synchronized (NativeRuntime.class) { selected = new ArrayList<>(PACKAGES.values()); }
        List<Lease> leases = new ArrayList<>();
        for (Package pkg : selected) {
            if (!pkg.exports.contains(point) || !current(pkg)) continue;
            try {
                Object value = pkg.implementation.call(point, arguments);
                if (value == null) continue;
                if (expected != null && !expected.isInstance(value)) throw new IOException("Invalid native drawing scope type");
                Lease lease = new Lease(pkg, value);
                if (!valid.test(lease)) throw new IllegalStateException("Invalid native icon save count");
                leases.add(lease);
            } catch (Throwable failure) {
                disable(pkg, failure);
                // Undo every transform so far; earlier leases keep their paired end call.
                reset.run();
            }
        }
        return leases;
    }
    static void release(Lease lease, String point, Object[] arguments) {
        if (lease == null || !lease.owner.exports.contains(point)) return;
        try { lease.owner.implementation.call(point, arguments); }
        catch (Throwable failure) { disable(lease.owner, failure); }
    }
    static void reject(Lease lease, Throwable failure) { if (lease != null) disable(lease.owner, failure); }
    public static void begin(String point, Object[] arguments) {
        if (arguments.length == 0 || arguments[0] == null) return;
        List<Package> owners = new ArrayList<>();
        synchronized (NativeRuntime.class) {
            for (Package pkg : PACKAGES.values()) if (current(pkg) && pkg.exports.contains(point)) owners.add(pkg);
            TRANSACTIONS.put(arguments[0], owners);
        }
        for (Package pkg : owners) try { pkg.implementation.call(point, arguments); } catch (Throwable failure) { disable(pkg, failure); }
    }
    public static void finish(String point, Object[] arguments) {
        if (arguments.length == 0 || arguments[0] == null) return;
        List<Package> owners;
        synchronized (NativeRuntime.class) { owners = TRANSACTIONS.remove(arguments[0]); }
        if (owners == null) return;
        // Complete only transactions that this exact code revision began. This
        // lets its own cancellation path restore temporary state after removal.
        for (Package pkg : owners) if (pkg.exports.contains(point))
            try { pkg.implementation.call(point, arguments); } catch (Throwable failure) { disable(pkg, failure); }
    }
    private static void watch() {
        List<Package> packages;
        synchronized (NativeRuntime.class) { packages = new ArrayList<>(PACKAGES.values()); }
        for (Package pkg : packages) if (pkg.active && !current(pkg)) disable(pkg, null);
    }
    /** A package's method hook failed: switch that package off like any other provider failure. */
    static void fail(String id, Throwable failure) {
        Package pkg;
        synchronized (NativeRuntime.class) { pkg = PACKAGES.get(id); }
        if (pkg != null) disable(pkg, failure);
    }
    private static void disable(Package pkg, Throwable failure) {
        synchronized (pkg) {
            if (!pkg.active) return; pkg.active = false;
            MethodHooks.unregister(pkg.id);
            try { pkg.implementation.stop(); } catch (Throwable ignored) {}
            if (failure != null) error(pkg.root, failure);
        }
    }
    private static void error(File root, Throwable failure) {
        try {
            File target = new File(root, "last-error.txt");
            if (!safe(target)) return;
            String message = String.valueOf(failure); if (message.length() > 4000) message = message.substring(0, 4000);
            try (FileOutputStream output = new FileOutputStream(target)) { output.write((message + "\n").getBytes(StandardCharsets.UTF_8)); }
        } catch (Exception ignored) {}
    }
}
