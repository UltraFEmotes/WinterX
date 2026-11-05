package winterx.extension;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Tweak JavaScript that runs inside chosen Spring apps, after Spring's UIKit and before the app's own main.js, in
 * the app's JavaScript context. Two core-owned method hooks: Spring reading an app's main.js names the app, then
 * evaluating that main.js runs the matching tweaks' scripts first.
 */
final class SappInjection {
    static final String READ = "Lcom/guille/spring/sapp/a;->g(Ljava/io/File;)Ljava/lang/String;";
    static final String EVAL = "Lcom/guille/spring/sapp/QuickJs;->u(Ljava/lang/String;Ljava/lang/String;)V";
    /** WinterX's own apps keep exactly their pinned code. */
    static final Set<String> RESERVED = new HashSet<>(Arrays.asList("com.ruby.manager", "com.ruby.jailbreak", "com.winterx.iexplored"));
    private static final ThreadLocal<String> APP = new ThreadLocal<>();
    private static boolean installed;

    private SappInjection() {}

    /** Called once after packages load; does nothing unless some running tweak declares "inject". */
    static synchronized void install() {
        if (installed) return;
        boolean wanted = false;
        for (JSONObject manifest : NativeRuntime.manifests()) wanted |= manifest.optJSONArray("inject") != null;
        if (!wanted || !MethodHooks.hookable(READ) || !MethodHooks.hookable(EVAL)) return;
        installed = true;
        MethodHooks.register(null, READ, call -> {
            Object file = call.args[0];
            if (file instanceof File) APP.set(appId((File)file));
            return call.proceed();
        });
        MethodHooks.register(null, EVAL, call -> {
            String id = "main.js".equals(call.args[1]) ? APP.get() : null;
            APP.remove();
            if (id != null) run(call, id);
            return call.proceed();
        });
    }

    /** sapps/<app id>/<build>/main.js → app id, or null for anything else. */
    static String appId(File file) {
        File build = file.getParentFile(), app = build == null ? null : build.getParentFile(), sapps = app == null ? null : app.getParentFile();
        if (!"main.js".equals(file.getName()) || sapps == null || !"sapps".equals(sapps.getName()) || !build.getName().matches("[0-9]{1,9}")) return null;
        return app.getName().matches("[a-z0-9]+(?:[.-][a-z0-9]+)+") ? app.getName() : null;
    }

    private static void run(MethodHooks.Call call, String appId) {
        if (RESERVED.contains(appId)) return;
        List<JSONObject> manifests = NativeRuntime.manifests();
        for (JSONObject manifest : manifests) {
            String packageId = manifest.optString("id");
            JSONArray inject = manifest.optJSONArray("inject");
            if (inject == null || !NativeRuntime.live(packageId)) continue;
            for (int i = 0; i < inject.length(); i++) {
                JSONObject entry = inject.optJSONObject(i);
                if (entry == null || !targets(entry.optJSONArray("apps"), appId)) continue;
                String script = entry.optString("script");
                try {
                    String source = verified(packageId, manifest, script);
                    call.original(source, "winterx/" + packageId + "/" + script);
                } catch (Throwable failure) {
                    // A broken script switches its tweak off; the app still starts normally.
                    NativeRuntime.fail(packageId, failure instanceof MethodHooks.OriginalFailure ? failure.getCause() : failure);
                    break;
                }
            }
        }
    }

    static boolean targets(JSONArray apps, String appId) {
        if (apps == null) return false;
        for (int i = 0; i < apps.length(); i++) if ("*".equals(apps.optString(i)) || appId.equals(apps.optString(i))) return true;
        return false;
    }

    /** The installed script, read only if it still matches the hash pinned in the package manifest. */
    static String verified(String packageId, JSONObject manifest, String script) throws Exception {
        JSONObject files = manifest.optJSONObject("files");
        String expected = files == null ? null : files.optString(script, null);
        if (expected == null || !script.matches("inject/[A-Za-z0-9][A-Za-z0-9._-]{0,80}\\.js")) throw new IOException("Undeclared injected script " + script);
        File file = new File(NativeRuntime.files(), "winterx-tweaks/" + packageId + "/" + script);
        if (Files.isSymbolicLink(file.toPath()) || !file.isFile() || file.length() > 256 * 1024) throw new IOException("Injected script unavailable: " + script);
        byte[] raw;
        try (FileInputStream input = new FileInputStream(file)) { raw = new byte[(int)file.length()]; int at = 0; for (int n; at < raw.length && (n = input.read(raw, at, raw.length - at)) > 0;) at += n; }
        StringBuilder hex = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(raw)) hex.append(String.format("%02x", b & 255));
        if (!hex.toString().equals(expected)) throw new IOException("Injected script failed its integrity check: " + script);
        return new String(raw, StandardCharsets.UTF_8);
    }
}
