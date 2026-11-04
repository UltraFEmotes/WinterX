package winterx.tweaks;

import android.app.ActivityThread;
import android.app.Application;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import com.guille.spring.LauncherActivity;
import com.guille.spring.sapp.QuickJs;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.lang.ref.WeakReference;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.json.JSONArray;
import org.json.JSONObject;

/** Opt-in, per-package JavaScript contexts. No package code executes on the UI thread. */
public final class TweakHost {
    private static final String TAG = "WinterX";
    public static final String FOLDER = "winterx-tweaks";
    private static final int MAX_BYTES = 256 * 1024;
    private static final int MAX_TWEAKS = 8;
    private static final long TURN_MS = 1000;
    private static final String[] NAMES = {
        "winterxLog", "winterxStateRead", "winterxStateWrite",
        "winterxDataRead", "winterxDataWrite", "winterxAlert", "winterxHome"
    };
    private static final Map<String, Instance> LOADED = new HashMap<>();
    private static final AtomicInteger ALERT_ID = new AtomicInteger();
    private static volatile WeakReference<LauncherActivity> launcher = new WeakReference<>(null);
    private static boolean started;

    private TweakHost() {}

    /** Called after unlock, once Spring's UI/controller have been initialized. */
    public static synchronized void start(LauncherActivity activity) {
        launcher = new WeakReference<>(activity);
        if (started || safeMode()) return;
        started = true;
        Thread discovery = new Thread(new Runnable() {
            public void run() {
                try {
                    File base = root();
                    File[] dirs = base == null ? null : base.listFiles();
                    if (dirs == null) return;
                    Arrays.sort(dirs);
                    int count = 0;
                    for (File dir : dirs) {
                        if (count >= MAX_TWEAKS || safeMode()) break;
                        if (!validId(dir.getName()) || manifestOf(dir.getName()) == null) continue;
                        final Instance instance = new Instance(dir.getName());
                        synchronized (LOADED) { LOADED.put(instance.id, instance); }
                        instance.worker.execute(new Runnable() {
                            public void run() { instance.load(); }
                        });
                        count++;
                    }
                } catch (Throwable failure) {
                    Log.w(TAG, "Tweak discovery failed", failure);
                }
            }
        }, "WinterX-tweak-discovery");
        discovery.setDaemon(true);
        discovery.start();
    }

    static File root() {
        Application app = ActivityThread.currentApplication();
        return app == null ? null : new File(app.getFilesDir(), FOLDER);
    }

    static boolean safeMode() {
        Application app = ActivityThread.currentApplication();
        return app == null || new File(app.getFilesDir(), "ruby/safe-mode.enabled").isFile();
    }

    static boolean validId(String id) {
        return id != null && id.length() <= 120 && id.matches("[a-z0-9]+(?:[.-][a-z0-9]+)+");
    }

    /** Reject redirects through symlinks, including a symlinked tweak directory. */
    static File file(String id, String relative) throws IOException {
        File base = root();
        if (base == null || !validId(id)) throw new IOException("Tweak storage unavailable");
        File canonicalBase = base.getCanonicalFile();
        File expected = new File(canonicalBase, id + "/" + relative).getAbsoluteFile();
        // getCanonicalFile() alone does not reliably resolve dangling links.
        for (File part = expected; part != null && !part.equals(canonicalBase); part = part.getParentFile()) {
            if (java.nio.file.Files.isSymbolicLink(part.toPath())) throw new IOException("Tweak symlink refused");
        }
        if (!expected.equals(expected.getCanonicalFile())) throw new IOException("Tweak symlink refused");
        return expected;
    }

    static JSONObject manifestOf(String id) {
        try {
            if (safeMode() || !file(id, "enabled").isFile()) return null;
            String text = readText(file(id, "manifest.json"));
            if (text == null) return null;
            String expected = readText(file(id, "manifest.sha256"));
            if (expected == null || !expected.trim().equals(digestOf(file(id, "manifest.json")))) return null;
            JSONObject manifest = new JSONObject(text);
            return "winterx.springys/2".equals(manifest.optString("format"))
                && "tweak".equals(manifest.optString("type"))
                && id.equals(manifest.optString("id"))
                && "tweak/main.js".equals(manifest.optString("entry")) ? manifest : null;
        } catch (Throwable failure) { return null; }
    }

    static synchronized boolean setting(String id, String key, String fallback) {
        try {
            String text = readText(file(id, "state.json"));
            JSONObject state = new JSONObject(text == null ? "{}" : text);
            JSONObject settings = state.optJSONObject("settings");
            return "on".equals(settings == null ? fallback : settings.optString(key, fallback));
        } catch (Throwable failure) { return "on".equals(fallback); }
    }

    static synchronized boolean setSetting(String id, String key, boolean on) {
        try {
            String text = readText(file(id, "state.json"));
            JSONObject state = new JSONObject(text == null ? "{}" : text);
            JSONObject settings = state.optJSONObject("settings");
            if (settings == null) { settings = new JSONObject(); state.put("settings", settings); }
            settings.put(key, on ? "on" : "off");
            return writeText(file(id, "state.json"), state.toString());
        } catch (Throwable failure) { return false; }
    }

    static String readText(File path) {
        if (!path.isFile() || path.length() > MAX_BYTES) return null;
        try (FileInputStream in = new FileInputStream(path)) {
            byte[] bytes = new byte[(int) path.length()];
            int at = 0;
            while (at < bytes.length) {
                int n = in.read(bytes, at, bytes.length - at);
                if (n < 0) return null;
                at += n;
            }
            return new String(bytes, StandardCharsets.UTF_8);
        } catch (IOException failure) { return null; }
    }

    static boolean writeText(File path, String text) {
        File temp = null;
        try {
            byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
            if (bytes.length > MAX_BYTES) throw new IOException("Tweak data exceeds 256 KB");
            path.getParentFile().mkdirs();
            temp = File.createTempFile(".winterx-", ".tmp", path.getParentFile());
            try (FileOutputStream out = new FileOutputStream(temp)) {
                out.write(bytes);
                out.getFD().sync();
            }
            if (!temp.renameTo(path)) throw new IOException("Tweak data rename failed");
            return true;
        } catch (IOException failure) {
            Log.w(TAG, "Tweak write failed", failure);
            return false;
        } finally { if (temp != null) temp.delete(); }
    }

    static String digestOf(File path) throws Exception {
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        try (FileInputStream in = new FileInputStream(path)) {
            byte[] block = new byte[8192];
            for (int n; (n = in.read(block)) != -1;) hash.update(block, 0, n);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : hash.digest()) hex.append(String.format("%02x", b & 255));
        return hex.toString();
    }

    public static boolean loaded(String id) {
        synchronized (LOADED) {
            Instance instance = LOADED.get(id);
            return instance != null && instance.ready && instance.currentRevision();
        }
    }

    public static void tapped(String rowId) {
        if (safeMode() || rowId == null || !rowId.startsWith(TweakSettings.ROW_PREFIX)) return;
        String[] parts = rowId.split("/", -1);
        if (parts.length != 4 || manifestOf(parts[1]) == null) return;
        final Instance instance;
        synchronized (LOADED) { instance = LOADED.get(parts[1]); }
        if (instance != null) instance.event("settingsTap", parts[2], parts[3]);
    }

    /** All native context calls, including close and promise jobs, stay on this worker. */
    private static final class Instance {
        final String id;
        final ScheduledThreadPoolExecutor worker;
        final AtomicInteger pending = new AtomicInteger();
        final Map<Integer, Boolean> alerts = new HashMap<>();
        final AtomicInteger homePending = new AtomicInteger();
        QuickJs js;
        String codeRevision;
        String manifestRevision;
        volatile boolean ready;
        volatile boolean failed;

        Instance(final String id) {
            this.id = id;
            worker = new ScheduledThreadPoolExecutor(1, new ThreadFactory() {
                public Thread newThread(Runnable run) {
                    Thread thread = new Thread(run, "WinterX-tweak-" + id);
                    thread.setDaemon(true);
                    return thread;
                }
            });
            worker.setRemoveOnCancelPolicy(true);
            worker.setExecuteExistingDelayedTasksAfterShutdownPolicy(false);
        }

        void load() {
            try {
                JSONObject manifest = manifestOf(id);
                if (manifest == null) throw new IOException("Disabled or invalid tweak manifest");
                File code = file(id, "code/main.js");
                String expected = readText(file(id, "sha256"));
                String script = readText(code);
                if (script == null || script.trim().isEmpty() || expected == null
                    || !expected.trim().matches("[0-9a-f]{64}")
                    || !expected.trim().equals(digestOf(code))) throw new IOException("Tweak code integrity check failed");
                codeRevision = expected.trim();
                manifestRevision = readText(file(id, "manifest.sha256")).trim();
                ArrayList<String> names = new ArrayList<>(Arrays.asList(NAMES));
                ArrayList<Z1.l> handlers = new ArrayList<>();
                for (int i = 0; i < NAMES.length; i++) {
                    final int op = i;
                    handlers.add(new Z1.l() {
                        public Object a(Object args) {
                            try { return call(op, (Object[]) args); }
                            catch (Exception failure) { throw new IllegalArgumentException("WinterX API: " + failure.getMessage(), failure); }
                        }
                    });
                }
                // This constructor is synthetic in Spring's converted JAR; javac hides it.
                C0.a host = (C0.a) C0.a.class.getConstructor(Object.class, int.class).newInstance(handlers, 5);
                js = (QuickJs) QuickJs.class.getMethod("winterxCreate", ArrayList.class, C0.a.class).invoke(null, names, host);
                js.t(TURN_MS); // Spring's t() accepts a duration in milliseconds (0 clears it).
                js.u(BOOTSTRAP, "winterx-bootstrap.js");
                js.u(script, id + "/main.js");
                js.v();
                js.t(0);
                ready = true;
                worker.scheduleWithFixedDelay(new Runnable() {
                    public void run() { if (!currentRevision()) stop(); }
                }, 250, 250, TimeUnit.MILLISECONDS);
                file(id, "last-error.txt").delete();
                Log.i(TAG, "Loaded tweak " + id);
            } catch (Throwable failure) { fail(failure); }
        }

        void event(final String name, final Object... args) {
            if (failed || worker.isShutdown()) return;
            if (pending.incrementAndGet() > 64) { pending.decrementAndGet(); return; }
            try {
                worker.execute(new Runnable() {
                    public void run() {
                        try {
                            if (failed || !ready || !currentRevision()) return;
                            js.t(TURN_MS);
                            js.j(name, args); // invokes __spring[name](...args), NOT __spring(name, ...args).
                            js.v();
                        } catch (Throwable failure) { fail(failure); }
                        finally {
                            pending.decrementAndGet();
                            if (js != null) {
                                try { js.t(0); } catch (Throwable failure) { fail(failure); }
                            }
                        }
                    }
                });
            } catch (java.util.concurrent.RejectedExecutionException ignored) { pending.decrementAndGet(); }
        }

        void fail(Throwable failure) {
            try { writeText(file(id, "last-error.txt"), bounded(String.valueOf(failure), 4000) + "\n"); }
            catch (IOException ignored) {}
            stop();
            Log.w(TAG, "Tweak disabled for this session: " + id, failure);
        }

        void stop() {
            ready = false;
            failed = true;
            synchronized (LOADED) { if (LOADED.get(id) == this) LOADED.remove(id); }
            synchronized (alerts) { alerts.clear(); }
            if (js != null) {
                try { js.close(); } catch (Throwable ignored) {}
                js = null;
            }
            worker.shutdownNow();
        }

        Object call(int op, Object[] args) throws Exception {
            if (!currentRevision()) throw new IOException("Tweak is disabled or updated; reopen Spring to load the new revision");
            String text = args.length == 0 ? "" : String.valueOf(args[0]);
            switch (op) {
                case 0: Log.i(TAG, "[" + id + "] " + bounded(text, 4000)); return null;
                case 1: {
                    synchronized (TweakHost.class) {
                        String state = readText(file(id, "state.json"));
                        return state == null ? "{}" : state;
                    }
                }
                case 2: {
                    JSONObject state = new JSONObject(text);
                    synchronized (TweakHost.class) {
                        if (!writeText(file(id, "state.json"), state.toString())) throw new IOException("State write failed");
                    }
                    return null;
                }
                case 3: return readText(dataFile(text));
                case 4:
                    if (args.length != 2) throw new IOException("Data write needs a name and value");
                    File target = dataFile(text);
                    File[] saved = target.getParentFile().listFiles();
                    long used = 0;
                    if (saved != null) for (File value : saved) if (!value.equals(target)) used += value.length();
                    byte[] payload = String.valueOf(args[1]).getBytes(StandardCharsets.UTF_8);
                    if ((saved != null && saved.length >= 64 && !target.exists()) || used + payload.length > 8 * 1024 * 1024
                        || !writeText(target, String.valueOf(args[1]))) throw new IOException("Data write failed or exceeded tweak storage quota");
                    return null;
                case 5: return alert(text);
                case 6: return home(text);
                default: throw new IllegalArgumentException("Unknown WinterX operation");
            }
        }

        File dataFile(String name) throws IOException {
            if (!name.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,79}") || name.contains("..")) throw new IOException("Invalid data filename");
            return file(id, "data/" + name);
        }

        Integer home(String text) throws Exception {
            if (text.length() > 4096) throw new IOException("Home request exceeds limit");
            final JSONObject request = new JSONObject(text); String operation = request.getString("op");
            if (!operation.equals("snapshot") && !operation.equals("move")) throw new IOException("Unknown home operation");
            JSONObject manifest = manifestOf(id); JSONArray permissions = manifest == null ? null : manifest.optJSONArray("capabilities");
            String needed = operation.equals("snapshot") ? "home.read" : "home.grid"; boolean granted = false;
            if (permissions != null) for (int i = 0; i < permissions.length(); i++) if (needed.equals(permissions.optString(i))) granted = true;
            if (!granted) throw new IOException("Manifest must declare " + needed);
            if (homePending.incrementAndGet() > 8) { homePending.decrementAndGet(); throw new IOException("Too many pending home requests"); }
            final int ticket = ALERT_ID.incrementAndGet();
            boolean posted = new Handler(Looper.getMainLooper()).post(new Runnable() {
                public void run() {
                    JSONObject reply = new JSONObject();
                    try {
                        if (failed || !ready || !currentRevision()) throw new IOException("Tweak disabled, failed or updated");
                        LauncherActivity activity = launcher.get();
                        if (activity == null) throw new IOException("Launcher unavailable");
                        x1.i1 spring = (x1.i1)LauncherActivity.class.getDeclaredMethod("access$getController$p", LauncherActivity.class).invoke(null, activity);
                        JSONObject value = request.getString("op").equals("snapshot") ? HomeApi.snapshot(spring) : HomeApi.move(spring, request);
                        reply.put("ok", true).put("value", value);
                    } catch (Exception failure) {
                        try { reply.put("ok", false).put("error", bounded(String.valueOf(failure.getMessage()), 300)); } catch (Exception ignored) {}
                    } finally { homePending.decrementAndGet(); }
                    event("home", ticket, reply.toString());
                }
            });
            if (!posted) { homePending.decrementAndGet(); throw new IOException("UI dispatcher unavailable"); }
            return ticket;
        }

        boolean currentRevision() {
            try {
                return manifestOf(id) != null
                    && codeRevision.equals(readText(file(id, "sha256")).trim())
                    && manifestRevision.equals(readText(file(id, "manifest.sha256")).trim());
            } catch (Throwable failure) { return false; }
        }

        Integer alert(String config) throws Exception {
            JSONObject options = new JSONObject(config);
            final String title = bounded(options.optString("title", "Alert"), 80);
            final String message = bounded(options.optString("message", ""), 500);
            JSONArray requested = options.optJSONArray("buttons");
            final String[] labels = new String[requested == null || requested.length() == 0 ? 1 : Math.min(requested.length(), 5)];
            for (int i = 0; i < labels.length; i++) labels[i] = requested == null ? "OK" : bounded(requested.optString(i, "OK"), 40);
            final int request = ALERT_ID.incrementAndGet();
            synchronized (alerts) {
                if (alerts.size() >= 8) throw new IOException("Too many pending alerts");
                alerts.put(request, true);
            }
            new Handler(Looper.getMainLooper()).post(new Runnable() {
                public void run() {
                    try {
                        LauncherActivity activity = launcher.get();
                        if (activity == null || failed || !currentRevision()) { done(request, -1); return; }
                        x1.J view = (x1.J) LauncherActivity.class.getDeclaredMethod("access$alertView", LauncherActivity.class).invoke(null, activity);
                        if (view == null) { done(request, -1); return; }
                        view.n(title, message, labels, 0, new Z1.l() {
                            public Object a(Object choice) {
                                done(request, choice instanceof Number ? ((Number) choice).intValue() : -1);
                                return null;
                            }
                        });
                    } catch (Throwable failure) { done(request, -1); Log.w(TAG, "Tweak alert failed", failure); }
                }
            });
            return request;
        }

        void done(int request, int choice) {
            synchronized (alerts) { if (alerts.remove(request) == null) return; }
            event("alert", request, choice);
        }
    }

    private static String bounded(String value, int max) {
        return value.length() > max ? value.substring(0, max) : value;
    }

    /** Spring registers native functions on __host and calls methods on __spring. */
    static final String BOOTSTRAP =
        "(function(host){'use strict';\n"
        + "var listeners=Object.create(null),requests=Object.create(null),homeRequests=Object.create(null);\n"
        + "function emit(name,a,b){var list=(listeners[name]||[]).slice();for(var i=0;i<list.length;i++)list[i](a,b);}\n"
        + "globalThis.__spring={settingsTap:function(page,row){emit('settingsTap',page,row);},\n"
        + " alert:function(id,index){var resolve=requests[id];delete requests[id];if(resolve)resolve(index);},\n"
        + " home:function(id,text){var pending=homeRequests[id];delete homeRequests[id];if(pending){var reply=JSON.parse(text);if(reply.ok)pending[0](reply.value);else pending[1](new Error(reply.error));}}};\n"
        + "function homeCall(opts){return new Promise(function(resolve,reject){var id=host.winterxHome(JSON.stringify(opts));homeRequests[id]=[resolve,reject];});}\n"
        + "globalThis.WinterX={version:1,\n"
        + " on:function(name,fn){if(typeof name!=='string'||typeof fn!=='function')throw new TypeError('WinterX.on(name, fn)');(listeners[name]=listeners[name]||[]).push(fn);},\n"
        + " log:function(){host.winterxLog(Array.prototype.map.call(arguments,String).join(' '));},\n"
        + " home:{snapshot:function(){return homeCall({op:'snapshot'});},\n"
        + "  move:function(opts){if(!opts||typeof opts!=='object')throw new TypeError('Home move needs id, page, slot and revision');return homeCall({op:'move',id:opts.id,page:opts.page,slot:opts.slot,revision:opts.revision});}},\n"
        + " alert:function(opts){opts=opts||{};return new Promise(function(resolve){\n"
        + "  var id=host.winterxAlert(JSON.stringify({title:opts.title||'',message:opts.message||'',buttons:opts.buttons||['OK']}));requests[id]=resolve;});},\n"
        + " state:{get:function(){return JSON.parse(host.winterxStateRead()||'{}');},\n"
        + "  set:function(value){if(!value||typeof value!=='object'||Array.isArray(value))throw new TypeError('State must be an object');host.winterxStateWrite(JSON.stringify(value));},\n"
        + "  read:function(key){return WinterX.state.get()[key];},\n"
        + "  write:function(key,value){var state=WinterX.state.get();state[key]=value;WinterX.state.set(state);}},\n"
        + " data:{read:function(name){return host.winterxDataRead(String(name));},\n"
        + "  write:function(name,value){host.winterxDataWrite(String(name),String(value));}}};\n"
        + "})(__host);\n";
}
