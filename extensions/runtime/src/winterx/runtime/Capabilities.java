package winterx.runtime;

import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import org.json.JSONObject;

/** Runtime-owned capability receipt, not a preference, app action, listener or code installer. */
public final class Capabilities {
    public static final String ABI = "winterx-capabilities-v1";
    private Capabilities() {}
    private static boolean safe(File file) throws Exception {
        return !Files.isSymbolicLink(file.toPath()) && file.getCanonicalFile().equals(file.getAbsoluteFile());
    }
    public static void publish(File suppliedRoot) {
        File temporary = null;
        try {
            File ruby = new File(suppliedRoot.getCanonicalFile(), "ruby"), destination = new File(ruby, "capabilities-v1.json");
            if (!safe(ruby) || !ruby.isDirectory() || !safe(destination) || destination.exists() && !destination.isFile()) return;
            byte[] payload = new JSONObject().put("abi", ABI).put("nativePackages", true).put("nativeApi", winterx.extension.NativeRuntime.ABI)
                .put("packageManager", PackageService.ABI)
                .put("features", new org.json.JSONArray(winterx.extension.NativeRuntime.features()))
                .toString().getBytes(StandardCharsets.UTF_8);
            temporary = File.createTempFile(".capabilities-", ".tmp", ruby);
            try (FileOutputStream output = new FileOutputStream(temporary)) { output.write(payload); output.getFD().sync(); }
            if (!safe(destination) || !safe(ruby)) return;
            Files.move(temporary.toPath(), destination.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception | LinkageError unavailable) { /* A capability receipt must never prevent boot. */ }
        finally { if (temporary != null && temporary.exists()) temporary.delete(); }
    }
}
