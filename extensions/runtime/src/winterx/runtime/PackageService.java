package winterx.runtime;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Ruby's package manager inside the running core: scan, install and remove .springys/3 packages without the host
 * bridge. Same checks, registry, journal and on-disk layout as tools/ruby_packages.py and springys_registry.py.
 * Repository downloads stay with the bridge. Package code is never executed here; it loads at the next WinterX start.
 */
public final class PackageService implements Runnable {
    public static final String ABI = "winterx-pm-v1";
    static final String APP = "sapps-data/com.ruby.manager/files";
    static final Pattern REQUEST = Pattern.compile("([0-9]{1,30}-[0-9]{1,30})\\.json");
    static final Pattern REPO_FILE = Pattern.compile("repo-([0-9a-f]{64})\\.springys");
    static final Pattern STAGE = Pattern.compile("tweaks/[0-9a-f]{64}");
    static final Set<String> ACTIONS = new HashSet<>(Arrays.asList("scan_packages", "install_package", "remove_package"));
    static final int MAX_NATIVE = 16;
    private static final AtomicBoolean STARTED = new AtomicBoolean();

    final File files, app, registry, tweaks, inbox;
    private final Set<String> completed = new HashSet<>();
    private List<String> log = new ArrayList<>();
    private int writes;

    PackageService(File files, File inbox) throws IOException {
        this.files = files.getCanonicalFile(); this.inbox = inbox;
        app = new File(this.files, APP); registry = new File(app, "package-registry"); tweaks = new File(this.files, "winterx-tweaks");
    }

    /** Started once per process with Spring's launcher; polls Ruby's request folder on a low-priority thread. */
    public static void start(android.content.Context context) {
        if (context == null || !STARTED.compareAndSet(false, true)) return;
        try {
            Thread thread = new Thread(new PackageService(context.getFilesDir(), context.getExternalFilesDir("sapps-inbox")), "winterx-packages");
            thread.setDaemon(true); thread.setPriority(Thread.MIN_PRIORITY); thread.start();
        } catch (Exception | LinkageError unavailable) { STARTED.set(false); }
    }

    @Override public void run() {
        while (true) {
            try { poll(); } catch (Throwable ignored) { /* A bad request or storage error must never stop the launcher. */ }
            try { Thread.sleep(400); } catch (InterruptedException stop) { return; }
        }
    }

    void poll() throws IOException {
        File requests = new File(app, "requests");
        String[] names = requests.list();
        if (names == null || !safe(requests)) return;
        Arrays.sort(names);
        for (String name : names) {
            Matcher match = REQUEST.matcher(name);
            if (!match.matches() || completed.contains(name)) continue;
            File result = new File(app, "results/" + match.group(1) + ".json");
            if (result.exists()) { completed.add(name); continue; }
            File source = new File(requests, name);
            if (!safe(source) || !source.isFile() || source.length() > 65536) { completed.add(name); continue; }
            JSONObject request;
            try { request = PackageArchive.StrictJson.object(read(source, 65536)); }
            catch (IOException incomplete) { continue; }  // Ruby may still be writing it
            if (!match.group(1).equals(request.optString("id")) || !ACTIONS.contains(request.optString("action"))) { completed.add(name); continue; }
            write(result, PackageArchive.canonical(handle(request)));
            completed.add(name);
        }
    }

    /** One Ruby request → its result object (with the real steps taken in "log"). */
    JSONObject handle(JSONObject request) {
        String action = request.optString("action");
        log = new ArrayList<>(); writes = 0;
        log.add("WinterX's core is handling this request directly");
        JSONObject reply = new JSONObject();
        try {
            if ("install_package".equals(action)) install(request.optString("filename"));
            else if ("remove_package".equals(action)) uninstall(request.optString("packageId"));
            write(new File(app, "packages.json"), PackageArchive.canonical(scan()));
            boolean restart = "install_package".equals(action);
            log.add("Wrote " + writes + " package-manager files; none of your own files changed");
            reply.put("ok", true).put("action", action).put("restartRequired", restart).put("log", new JSONArray(log))
                .put("message", restart ? "Code package installed. Reopen Spring through WinterX to load it." : "Ruby package operation completed.");
        } catch (Exception failure) {
            String message = failure.getMessage() == null ? failure.getClass().getSimpleName() : failure.getMessage();
            try {
                reply.put("ok", false).put("action", action).put("message", message.length() > 250 ? message.substring(0, 250) : message)
                    .put("log", new JSONArray(log.size() > 20 ? log.subList(0, 20) : log));
            } catch (JSONException impossible) { /* unreachable for these values */ }
        }
        return reply;
    }

    // ----- registry (springys_registry.Registry) -----

    JSONObject index() throws IOException {
        File index = new File(registry, "installed.json");
        if (!index.exists()) return new JSONObject();
        try { return new JSONObject(new String(read(index, 4 * 1024 * 1024), StandardCharsets.UTF_8)); }
        catch (JSONException bad) { throw new IOException("Installed package registry is invalid"); }
    }

    void recover() throws IOException {
        File journal = new File(registry, "operation.json");
        if (!journal.exists()) return;
        try {
            JSONObject pending = new JSONObject(new String(read(journal, 8 * 1024 * 1024), StandardCharsets.UTF_8));
            JSONObject old = pending.getJSONObject("before"), next = pending.getJSONObject("after");
            if (Arrays.equals(PackageArchive.canonical(index()), PackageArchive.canonical(next))) reconcile(next);
            else { reconcile(old); write(new File(registry, "installed.json"), PackageArchive.canonical(old)); }
        } catch (JSONException bad) { throw new IOException("A previous package operation needs recovery"); }
        if (!journal.delete()) throw new IOException("Could not finish package recovery");
    }

    static void dependencies(JSONObject entries) throws IOException {
        Set<String> visiting = new HashSet<>(), visited = new HashSet<>();
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            String id = it.next();
            if ("java".equals(entries.optJSONObject(id) == null ? null : entries.optJSONObject(id).optString("runtime"))) visit(entries, id, visiting, visited);
        }
    }
    private static void visit(JSONObject entries, String id, Set<String> visiting, Set<String> visited) throws IOException {
        if (visited.contains(id)) return;
        if (visiting.contains(id)) throw new IOException("Native package dependency cycle");
        JSONObject entry = entries.optJSONObject(id);
        if (entry == null || !"java".equals(entry.optString("runtime")))
            throw new IOException("Install the native package dependencies first; remove dependents before a dependency");
        visiting.add(id);
        JSONArray requires = entry.optJSONArray("requires");
        if (requires != null) for (int i = 0; i < requires.length(); i++) visit(entries, requires.optString(i), visiting, visited);
        visiting.remove(id); visited.add(id);
    }

    void change(JSONObject before, JSONObject after) throws IOException {
        dependencies(after);
        File journal = new File(registry, "operation.json"), index = new File(registry, "installed.json");
        try { write(journal, PackageArchive.canonical(new JSONObject().put("after", after).put("before", before))); }
        catch (JSONException impossible) { throw new IOException(impossible.getMessage()); }
        try {
            reconcile(after);
            write(index, PackageArchive.canonical(after));
        } catch (IOException | RuntimeException failure) {
            try { reconcile(before); write(index, PackageArchive.canonical(before)); journal.delete(); }
            catch (IOException | RuntimeException rollback) { throw new IOException("Package operation failed and recovery is required: " + rollback.getMessage()); }
            throw failure;
        }
        if (!journal.delete()) throw new IOException("Could not finish the package operation");
    }

    static Set<String> tweakIds(JSONObject entries) {
        Set<String> ids = new TreeSet<>();
        if (entries == null) return ids;
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            String id = it.next(); JSONObject entry = entries.optJSONObject(id);
            if (entry != null && "tweak".equals(entry.optString("type"))) ids.add(id);
        }
        return ids;
    }

    /** ruby_packages.Packages._reconcile: enable desired revisions, disable the rest; never delete user state/data. */
    void reconcile(JSONObject desired) throws IOException {
        Set<String> managed = tweakIds(desired);
        File journal = new File(registry, "operation.json");
        if (journal.exists()) {
            try {
                JSONObject record = new JSONObject(new String(read(journal, 8 * 1024 * 1024), StandardCharsets.UTF_8));
                managed.addAll(tweakIds(record.optJSONObject("before"))); managed.addAll(tweakIds(record.optJSONObject("after")));
            } catch (JSONException bad) { throw new IOException("Invalid package journal"); }
        }
        Set<String> wanted = tweakIds(desired);
        for (String id : managed) {
            if (!PackageArchive.ID.matcher(id).matches()) continue;
            File target = new File(tweaks, id);
            if (Files.isSymbolicLink(target.toPath())) throw new IOException("Tweak storage must not contain symlinks");
            if (!wanted.contains(id)) { new File(target, "enabled").delete(); continue; }
            JSONObject entry = desired.optJSONObject(id);
            String stage = entry.optString("tweak_stage");
            if (!STAGE.matcher(stage).matches()) throw new IOException("Invalid tweak revision path");
            File source = new File(registry, stage);
            if (!sameStage(source, entry.optString("code_sha256"))) throw new IOException("Installed tweak code failed integrity check for " + id);
            syncTree(source, target);
        }
    }

    static boolean sameStage(File source, String expected) {
        try { return new String(read(new File(source, "sha256"), 128), StandardCharsets.UTF_8).trim().equals(expected) && sameTree(source, expected); }
        catch (IOException bad) { return false; }
    }

    /** springys_registry._same_tree: an immutable revision still matches its pinned manifest and code. */
    static boolean sameTree(File base, String digest) {
        try {
            for (String name : new String[]{"", "code", "code/main.js", "manifest.json", "sha256", "manifest.sha256"})
                if (Files.isSymbolicLink(new File(base, name).toPath())) return false;
            String record = new String(read(new File(base, "sha256"), 128), StandardCharsets.UTF_8).trim();
            String manifestSha = new String(read(new File(base, "manifest.sha256"), 128), StandardCharsets.UTF_8).trim();
            byte[] rawManifest = read(new File(base, "manifest.json"), 1024 * 1024);
            if (!record.equals(digest) || !PackageArchive.sha256(rawManifest).equals(manifestSha)) return false;
            JSONObject manifest = new JSONObject(new String(rawManifest, StandardCharsets.UTF_8));
            if (PackageArchive.FORMAT.equals(manifest.optString("format"))) {
                JSONObject pinned = manifest.optJSONObject("files");
                if (pinned == null || !digest.equals(pinned.optString(PackageArchive.DEX)) || !pinned.has(PackageArchive.JAR) || pinned.length() > PackageArchive.MAX_FILES) return false;
                for (Iterator<String> it = pinned.keys(); it.hasNext();) {
                    String name = it.next(); File path = new File(base, name);
                    if (!PackageArchive.safePath(name) || !safe(path) || !path.isFile() || path.length() > PackageArchive.MAX_PAYLOAD) return false;
                    if (!PackageArchive.sha256(read(path, PackageArchive.MAX_PAYLOAD)).equals(pinned.optString(name))) return false;
                }
                return true;
            }
            return PackageArchive.sha256(read(new File(base, "code/main.js"), 1024 * 1024)).equals(digest);
        } catch (IOException | JSONException bad) { return false; }
    }

    /** ruby_packages._sync_tree: replace only runtime-owned files and keep state.json/data/. */
    void syncTree(File source, File target) throws IOException {
        if (Files.isSymbolicLink(target.toPath()) || target.exists() && !safe(target)) throw new IOException("Tweak storage must not contain symlinks");
        JSONObject manifest;
        try { manifest = new JSONObject(new String(read(new File(source, "manifest.json"), 1024 * 1024), StandardCharsets.UTF_8)); }
        catch (JSONException bad) { throw new IOException("Invalid staged manifest"); }
        List<String> names = new ArrayList<>();
        if (PackageArchive.FORMAT.equals(manifest.optString("format")) && manifest.optJSONObject("files") != null) {
            for (Iterator<String> it = manifest.optJSONObject("files").keys(); it.hasNext();) names.add(it.next());
        } else names.add("code/main.js");
        names.addAll(Arrays.asList("manifest.json", "sha256", "manifest.sha256"));
        List<Object[]> changes = new ArrayList<>();
        for (String relative : names) {
            File destination = new File(target, relative);
            if (Files.isSymbolicLink(destination.toPath()) || destination.exists() && !safe(destination)) throw new IOException("Tweak storage must not contain symlinks");
            byte[] payload = read(new File(source, relative), PackageArchive.MAX_PAYLOAD);
            if (destination.isFile() && Arrays.equals(read(destination, PackageArchive.MAX_PAYLOAD + 1), payload)) continue;
            changes.add(new Object[]{destination, payload});
        }
        File enabled = new File(target, "enabled");
        // Unchanged packages keep their marker so a live context never mistakes an unrelated install for removal.
        if (!changes.isEmpty()) {
            enabled.delete();
            for (Object[] change : changes) write((File)change[0], (byte[])change[1]);
        }
        if (!enabled.isFile()) write(enabled, "enabled\n".getBytes(StandardCharsets.UTF_8));
    }

    // ----- package operations (ruby_packages.Packages) -----

    File importFile(String name) throws IOException {
        if (name == null || name.isEmpty() || name.contains("/") || name.contains("\\") || ".".equals(name) || "..".equals(name)
                || !name.toLowerCase(Locale.ROOT).endsWith(".springys")) throw new IOException("Invalid package filename");
        File directory = new File(app, "imports").getCanonicalFile(), path = new File(directory, name);
        if (Files.isSymbolicLink(path.toPath()) || !path.isFile() || !path.getCanonicalFile().getParentFile().equals(directory))
            throw new IOException("Package must be a regular file in Ruby imports");
        return path;
    }

    JSONObject install(String filename) throws IOException, JSONException {
        File path = importFile(filename);
        recover();
        Matcher repo = REPO_FILE.matcher(filename);
        PackageArchive.Inspected inspected = PackageArchive.inspect(read(path, PackageArchive.MAX_ZIP + 1), repo.matches() ? repo.group(1) : null, true);
        JSONObject metadata = inspected.metadata;
        String id = metadata.getString("id"), sha = metadata.getString("sha256");
        log.add("Verified " + metadata.optString("name", id) + " " + metadata.optString("version") + " (" + id + ")");
        log.add("Checksum " + sha.substring(0, 16) + "… matches");
        JSONObject before = index(), previous = before.optJSONObject(id);
        int peers = 0;
        for (Iterator<String> it = before.keys(); it.hasNext();) {
            String other = it.next(); JSONObject entry = before.optJSONObject(other);
            if (entry != null && "tweak".equals(entry.optString("type")) && "java".equals(entry.optString("runtime")) && !other.equals(id)) peers++;
        }
        if ((previous == null || !"java".equals(previous.optString("runtime"))) && peers >= MAX_NATIVE)
            throw new IOException("At most " + MAX_NATIVE + " native tweaks can be installed in this engine");
        JSONArray requires = metadata.optJSONArray("requires");
        if (requires != null) for (int i = 0; i < requires.length(); i++) {
            JSONObject dependency = before.optJSONObject(requires.optString(i));
            if (dependency == null || !"java".equals(dependency.optString("runtime"))) throw new IOException("Install the native package dependencies first");
        }
        if (previous != null && sha.equals(previous.optString("sha256"))) { log.add("This exact package is already installed"); return previous; }
        JSONObject planned = new JSONObject(before.toString()); planned.put(id, metadata); dependencies(planned);

        String stage = "tweaks/" + sha;
        File staging = new File(registry, stage);
        String code = metadata.getString("code_sha256");
        if (staging.exists() && !sameTree(staging, code)) throw new IOException("Staging directory for tweak code failed integrity check");
        if (!staging.exists()) {
            File parent = staging.getParentFile();
            if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Package registry is unavailable");
            File temporary = Files.createTempDirectory(parent.toPath(), ".tweak-stage-").toFile();
            try {
                File revision = new File(temporary, "revision");
                for (Map.Entry<String, byte[]> payload : inspected.payloads.entrySet()) write(new File(revision, payload.getKey()), payload.getValue());
                JSONObject manifest = new JSONObject(metadata.toString()); manifest.remove("sha256");
                byte[] manifestBytes = PackageArchive.canonical(manifest);
                write(new File(revision, "manifest.json"), manifestBytes);
                write(new File(revision, "manifest.sha256"), (PackageArchive.sha256(manifestBytes) + "\n").getBytes(StandardCharsets.US_ASCII));
                write(new File(revision, "sha256"), (code + "\n").getBytes(StandardCharsets.UTF_8));
                Files.move(revision.toPath(), staging.toPath(), StandardCopyOption.ATOMIC_MOVE);
            } finally { deleteTree(temporary); }
        }
        log.add("Unpacked Java/Dex code into its own folder");
        JSONObject art = new JSONObject();
        for (Map.Entry<String, byte[]> image : inspected.media.entrySet()) {
            String name = PackageArchive.sha256(image.getValue()) + suffix(image.getKey());
            File target = new File(registry, "art/" + name);
            if (target.exists() && !PackageArchive.sha256(read(target, PackageArchive.MAX_ART)).equals(PackageArchive.sha256(image.getValue())))
                throw new IOException("Stored artwork failed integrity check");
            if (!target.exists()) write(target, image.getValue());
            art.put(image.getKey(), "art/" + name);
        }
        JSONObject record = new JSONObject(metadata.toString());
        record.put("tweak_stage", stage);
        String icon = metadata.isNull("icon") ? null : metadata.optString("icon", null);
        record.put("icon", icon == null || !art.has(icon) ? JSONObject.NULL : art.getString(icon));
        JSONArray previews = new JSONArray(), sourcePreviews = metadata.optJSONArray("previews");
        if (sourcePreviews != null) for (int i = 0; i < sourcePreviews.length(); i++) previews.put(art.getString(sourcePreviews.getString(i)));
        record.put("previews", previews);
        JSONObject after = new JSONObject(before.toString()); after.put(id, record);
        change(before, after);
        apps(previous, record, inspected.payloads);
        return record;
    }

    JSONObject uninstall(String id) throws IOException, JSONException {
        if (id == null || !PackageArchive.ID.matcher(id).matches()) throw new IOException("Invalid package ID");
        recover();
        JSONObject before = index();
        if (!before.has(id)) throw new IOException("Package is not installed");
        JSONObject after = new JSONObject(before.toString());
        JSONObject removed = (JSONObject)after.remove(id);
        change(before, after);
        log.add("Removed " + removed.optString("name", id) + " " + removed.optString("version") + "; its saved preferences were kept");
        apps(removed, null, null);
        return removed;
    }

    // ----- bundled Spring apps -----

    /** Queue a package's new apps for Spring's own installer; schedule apps it no longer bundles for removal at next boot. */
    void apps(JSONObject previous, JSONObject current, Map<String, byte[]> payloads) throws IOException, JSONException {
        Set<String> keep = new HashSet<>();
        JSONObject installed = index();
        for (Iterator<String> it = installed.keys(); it.hasNext();) {
            JSONArray bundled = installed.optJSONObject(it.next()).optJSONArray("bundled_apps");
            if (bundled != null) for (int i = 0; i < bundled.length(); i++) keep.add(bundled.getJSONObject(i).getString("id"));
        }
        Set<String> removals = removals(files);
        removals.removeAll(keep);
        JSONArray bundled = current == null ? null : current.optJSONArray("bundled_apps");
        if (bundled != null) for (int i = 0; i < bundled.length(); i++) {
            JSONObject app = bundled.getJSONObject(i);
            String appId = app.getString("id"), name = app.optString("name", appId);
            if (new File(files, "sapps/" + appId + "/" + app.getInt("build") + "/app.json").isFile()) { log.add(name + " app is already installed"); continue; }
            if (inbox == null) { log.add("Spring's app inbox is unavailable, so " + name + " wasn't installed"); continue; }
            File queued = new File(inbox, appId + ".sapp"), temporary = new File(inbox, "." + appId + ".sapp.pending");
            write(temporary, payloads.get(app.getString("path")));
            Files.move(temporary.toPath(), queued.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            log.add("Queued the " + name + " app for Spring's installer");
        }
        JSONArray old = previous == null ? null : previous.optJSONArray("bundled_apps");
        if (old != null) for (int i = 0; i < old.length(); i++) {
            String appId = old.getJSONObject(i).getString("id");
            if (keep.contains(appId) || PackageArchive.RESERVED_APPS.contains(appId)) continue;
            removals.add(appId);
            log.add("The " + old.getJSONObject(i).optString("name", appId) + " app will be removed next time Spring opens through WinterX (its data is kept)");
        }
        File list = new File(files, APP + "/package-registry/app-removals.json");
        if (removals.isEmpty()) list.delete();
        else write(list, PackageArchive.canonical(new JSONArray(removals)));
    }

    static Set<String> removals(File files) {
        Set<String> ids = new TreeSet<>();
        try {
            File list = new File(files, APP + "/package-registry/app-removals.json");
            if (!list.isFile()) return ids;
            JSONArray values = new JSONArray(new String(read(list, 65536), StandardCharsets.UTF_8));
            for (int i = 0; i < values.length() && i < 64; i++) {
                String id = values.optString(i);
                if (PackageArchive.ID.matcher(id).matches() && !PackageArchive.RESERVED_APPS.contains(id)) ids.add(id);
            }
        } catch (IOException | JSONException ignored) {}
        return ids;
    }

    /** Called at boot before Spring lists its apps: set aside apps whose package was removed. App data stays. */
    public static void boot(File suppliedFiles) {
        try {
            File files = suppliedFiles.getCanonicalFile();
            Set<String> ids = removals(files);
            if (ids.isEmpty()) return;
            File aside = new File(files, "winterx-removed-apps");
            for (String id : ids) {
                File dir = new File(files, "sapps/" + id);
                if (Files.isSymbolicLink(dir.toPath()) || !dir.exists()) continue;
                if (!aside.isDirectory() && !aside.mkdirs()) return;
                Files.move(dir.toPath(), new File(aside, id + "-" + System.currentTimeMillis()).toPath(), StandardCopyOption.ATOMIC_MOVE);
            }
            new File(files, APP + "/package-registry/app-removals.json").delete();
        } catch (Exception | LinkageError ignored) { /* App removal must never prevent boot. */ }
    }

    // ----- scan (ruby_packages.Packages.scan) -----

    JSONObject scan() throws IOException, JSONException {
        recover();
        JSONObject installed = index();
        JSONArray available = new JSONArray();
        File imports = new File(app, "imports");
        if (!imports.isDirectory() && !imports.mkdirs()) throw new IOException("Ruby imports are unavailable");
        String[] names = imports.list(); if (names == null) names = new String[0];
        Arrays.sort(names);
        for (String name : names) {
            if (!name.endsWith(".springys")) continue;
            try {
                PackageArchive.Inspected inspected = PackageArchive.inspect(read(importFile(name), PackageArchive.MAX_ZIP + 1), null, false);
                JSONObject metadata = inspected.metadata, entry = installed.optJSONObject(metadata.getString("id"));
                metadata.put("filename", name);
                metadata.put("installedVersion", entry == null ? JSONObject.NULL : entry.opt("version"));
                metadata.put("installedSha256", entry == null ? JSONObject.NULL : entry.opt("sha256"));
                JSONObject art = new JSONObject();
                for (Map.Entry<String, byte[]> image : inspected.media.entrySet()) {
                    String target = "package-art/" + PackageArchive.sha256(image.getValue()) + suffix(image.getKey());
                    File file = new File(app, target);
                    if (!file.isFile()) write(file, image.getValue());
                    art.put(image.getKey(), target);
                }
                String icon = metadata.isNull("icon") ? null : metadata.optString("icon", null);
                String thumb = icon == null ? null : thumbnail(app, inspected.media.get(icon), "package-art");
                metadata.put("icon", thumb == null ? JSONObject.NULL : thumb);
                JSONArray previews = new JSONArray(), sourcePreviews = metadata.optJSONArray("previews");
                if (sourcePreviews != null) for (int i = 0; i < sourcePreviews.length(); i++) previews.put(art.getString(sourcePreviews.getString(i)));
                metadata.put("previews", previews);
                available.put(metadata);
            } catch (IOException | JSONException | RuntimeException skipped) { /* Not a package this core can install; Ruby lists it elsewhere. */ }
        }
        JSONArray display = new JSONArray();
        for (Iterator<String> it = installed.keys(); it.hasNext();) {
            JSONObject entry = new JSONObject(installed.getJSONObject(it.next()).toString());
            String icon = entry.isNull("icon") ? null : entry.optString("icon", null);
            String thumb = null;
            if (icon != null) {
                try {
                    File root = registry.getCanonicalFile(), file = new File(root, icon).getCanonicalFile();
                    if (file.getPath().startsWith(root.getPath() + File.separator) && file.isFile()) thumb = thumbnail(root, read(file, PackageArchive.MAX_ART), "art");
                } catch (IOException ignored) {}
            }
            entry.put("icon", thumb == null ? JSONObject.NULL : thumb);
            display.put(entry);
        }
        return new JSONObject().put("available", available).put("installed", display);
    }

    /** A 64×64 PNG for Spring's 44-point rows, never enlarged (PIL thumbnail semantics). */
    String thumbnail(File root, byte[] payload, String directory) {
        if (payload == null) return null;
        String relative = directory + "/icon-64-" + PackageArchive.sha256(payload) + ".png";
        try {
            File target = new File(root, relative);
            if (target.isFile()) return relative;
            Bitmap source = BitmapFactory.decodeByteArray(payload, 0, payload.length);
            if (source == null) return null;
            float scale = Math.min(1f, Math.min(64f / source.getWidth(), 64f / source.getHeight()));
            int width = Math.max(1, Math.round(source.getWidth() * scale)), height = Math.max(1, Math.round(source.getHeight() * scale));
            Bitmap output = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888);
            new Canvas(output).drawBitmap(source, null, new Rect((64 - width) / 2, (64 - height) / 2, (64 - width) / 2 + width, (64 - height) / 2 + height),
                new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG));
            ByteArrayOutputStream png = new ByteArrayOutputStream();
            if (!output.compress(Bitmap.CompressFormat.PNG, 100, png)) return null;
            write(target, png.toByteArray());
            return relative;
        } catch (Exception | LinkageError unavailable) { return null; }
    }

    // ----- files -----

    static String suffix(String name) { int dot = name.lastIndexOf('.'); return dot < 0 ? "" : name.substring(dot).toLowerCase(Locale.ROOT); }

    static boolean safe(File file) throws IOException {
        return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile());
    }

    static byte[] read(File file, long limit) throws IOException {
        if (Files.isSymbolicLink(file.toPath())) throw new IOException("Refusing a linked file: " + file.getName());
        try (InputStream input = new FileInputStream(file)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buffer = new byte[65536];
            for (int n; (n = input.read(buffer)) > 0;) {
                if (out.size() + n > limit) throw new IOException("File exceeds its size limit: " + file.getName());
                out.write(buffer, 0, n);
            }
            return out.toByteArray();
        }
    }

    /** Atomic replace with fsync, refusing links on the way (the ruby _atomic contract). */
    void write(File target, byte[] data) throws IOException {
        File parent = target.getParentFile();
        if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create " + parent.getName());
        if (Files.isSymbolicLink(target.toPath()) || Files.isSymbolicLink(parent.toPath())) throw new IOException("Refusing a linked path");
        File temporary = File.createTempFile(".winterx-", ".tmp", parent);
        try {
            try (FileOutputStream output = new FileOutputStream(temporary)) { output.write(data); output.getFD().sync(); }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            writes++;
        } finally { if (temporary.exists()) temporary.delete(); }
    }

    static void deleteTree(File file) {
        if (file == null || !file.exists()) return;
        if (!Files.isSymbolicLink(file.toPath())) {
            File[] children = file.listFiles();
            if (children != null) for (File child : children) deleteTree(child);
        }
        file.delete();
    }

    /** Test entry point for disposable application roots. */
    public static JSONObject handleForTest(File files, File inbox, JSONObject request) throws IOException {
        return new PackageService(files, inbox).handle(request);
    }
}
