import java.io.File;
import java.nio.file.Files;
import org.json.JSONObject;
import winterx.runtime.PackageService;

/** Drives the core's in-process package manager in a disposable application root. */
public final class PackageServiceCheck {
    static int next;
    static JSONObject request(File root, File inbox, String action, String key, String value) throws Exception {
        JSONObject request = new JSONObject().put("id", "1-" + (++next)).put("action", action);
        if (key != null) request.put(key, value);
        return PackageService.handleForTest(root, inbox, request);
    }
    static void require(boolean condition, String message) { if (!condition) throw new AssertionError(message); }

    public static void main(String[] args) throws Exception {
        File root = new File(args[0]), inbox = new File(args[1]);
        String mode = args[2];
        if ("install".equals(mode)) {
            for (int i = 3; i < args.length; i++) {
                JSONObject result = request(root, inbox, "install_package", "filename", args[i]);
                require(result.optBoolean("ok"), "install " + args[i] + ": " + result);
                require(result.optBoolean("restartRequired"), "install must ask for a reopen");
            }
            JSONObject scan = request(root, inbox, "scan_packages", null, null);
            require(scan.optBoolean("ok"), "scan: " + scan);
            System.out.println("Java installs completed: " + (args.length - 3));
        } else if ("lifecycle".equals(mode)) {
            String id = args[3], filename = args[4];
            File data = new File(root, "winterx-tweaks/" + id + "/data/kept.txt");
            data.getParentFile().mkdirs(); Files.write(data.toPath(), "user data".getBytes("UTF-8"));
            JSONObject removed = request(root, inbox, "remove_package", "packageId", id);
            require(removed.optBoolean("ok"), "remove: " + removed);
            require(!new File(root, "winterx-tweaks/" + id + "/enabled").exists(), "removed package still enabled");
            require(data.isFile(), "removal deleted package data");
            require(!request(root, inbox, "remove_package", "packageId", id).optBoolean("ok"), "second removal should fail");
            require(request(root, inbox, "install_package", "filename", filename).optBoolean("ok"), "reinstall failed");
            require(new File(root, "winterx-tweaks/" + id + "/enabled").isFile() && data.isFile(), "reinstall lost marker or data");
            // Tamper with an installed revision: the next operation must refuse and leave the registry unchanged.
            File registry = new File(root, "sapps-data/com.ruby.manager/files/package-registry");
            byte[] before = Files.readAllBytes(new File(registry, "installed.json").toPath());
            File stage = new File(registry, new JSONObject(new String(before, "UTF-8")).getJSONObject(id).getString("tweak_stage"));
            File dex = new File(stage, "code/classes.dex"); byte[] original = Files.readAllBytes(dex.toPath());
            byte[] changed = original.clone(); changed[changed.length - 1] ^= 1; Files.write(dex.toPath(), changed);
            JSONObject refused = request(root, inbox, "remove_package", "packageId", args[5]);
            require(!refused.optBoolean("ok") && refused.optString("message").contains("integrity"), "tampered revision accepted: " + refused);
            require(java.util.Arrays.equals(before, Files.readAllBytes(new File(registry, "installed.json").toPath())), "failed operation changed the registry");
            // Rolling back onto a tampered revision can't verify either, so the journal is kept for recovery.
            require(new File(registry, "operation.json").exists(), "unrecoverable failure dropped its journal");
            Files.write(dex.toPath(), original);
            require(request(root, inbox, "remove_package", "packageId", args[5]).optBoolean("ok"), "restored revision was not recovered");
            require(!new File(registry, "operation.json").exists(), "recovery left a journal");
            System.out.println("Java lifecycle passed: remove keeps data, reinstall, tamper refused, journal recovery");
        } else if ("apps".equals(mode)) {
            String filename = args[3], appId = args[4], packageId = args[5];
            JSONObject installed = request(root, inbox, "install_package", "filename", filename);
            require(installed.optBoolean("ok"), "app package install: " + installed);
            require(new File(inbox, appId + ".sapp").isFile(), "bundled app was not queued for Spring's installer");
            require(installed.getJSONArray("log").toString().contains("Queued the"), "log does not mention the queued app");
            File app = new File(root, "sapps/" + appId + "/1");
            app.mkdirs(); Files.write(new File(app, "app.json").toPath(), "{}".getBytes("UTF-8"));
            File appData = new File(root, "sapps-data/" + appId + "/files/kept.txt");
            appData.getParentFile().mkdirs(); Files.write(appData.toPath(), "app data".getBytes("UTF-8"));
            require(request(root, inbox, "remove_package", "packageId", packageId).optBoolean("ok"), "app package removal failed");
            PackageService.boot(root);
            require(!new File(root, "sapps/" + appId).exists(), "bundled app was not removed at boot");
            require(appData.isFile(), "app removal deleted the app's data");
            System.out.println("Java bundled app passed: queued on install, removed at next boot, data kept");
        }
    }
}
