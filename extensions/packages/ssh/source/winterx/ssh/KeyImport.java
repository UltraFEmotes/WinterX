package winterx.ssh;

import android.app.Activity;
import android.app.ActivityThread;
import android.app.Application;
import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import winterx.extension.TweakContext;

/**
 * Pick an authorized_keys file with the system file picker and copy it into ruby/ssh, so SSH works without anyone
 * reaching into Spring's private folder (a rootless install has no other way in).
 */
public final class KeyImport {
    static final String LOOP = "Lcom/guille/spring/LauncherActivity;->startAnimationLoop()V";
    static final String RESULT = "Lcom/guille/spring/LauncherActivity;->onActivityResult(IILandroid/content/Intent;)V";
    static final int REQUEST = 0x5348;                       // "SH"; Spring's own request codes are small numbers
    private static volatile Activity activity;
    static volatile String note;
    private KeyImport() {}

    public static void install(TweakContext context) {
        context.hook(LOOP, call -> { activity = (Activity)call.self; return call.proceed(); });
        context.hook(RESULT, call -> {
            if (((Number)call.args[0]).intValue() != REQUEST) return call.proceed();
            Intent data = (Intent)call.args[2];
            if (((Number)call.args[1]).intValue() == Activity.RESULT_OK && data != null && data.getData() != null) {
                Uri file = data.getData();
                new Thread(() -> note = copy(file), "ssh-key-import").start();
            }
            return null;                                     // ours alone; Spring never sees this request
        });
    }

    static void open() {
        Activity current = activity;
        if (current == null) { note = "Go to the Home screen once, then try again"; return; }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*");
        new Handler(Looper.getMainLooper()).post(() -> {
            try { current.startActivityForResult(intent, REQUEST); }
            catch (RuntimeException noPicker) { note = "This device has no file picker"; }
        });
    }

    /** Only public keys, one per line; a private key or anything else is refused. */
    static String validate(String text) {
        int keys = 0;
        for (String line : text.split("\n")) {
            String key = line.trim();
            if (key.isEmpty() || key.startsWith("#")) continue;
            if (key.contains("PRIVATE KEY")) return "That's a private key: import the public one (.pub)";
            if (!key.matches("^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)|sk-ssh-ed25519@openssh\\.com|sk-ecdsa-sha2-nistp256@openssh\\.com) [A-Za-z0-9+/=]+( .*)?$"))
                return "Not an SSH public key: " + (key.length() > 32 ? key.substring(0, 32) + "…" : key);
            keys++;
        }
        return keys == 0 ? "No public keys in that file" : null;
    }

    private static String copy(Uri uri) {
        Application app = ActivityThread.currentApplication();
        File root = SshService.files();
        if (app == null || root == null) return "Couldn't import the key";
        byte[] data;
        try (InputStream in = app.getContentResolver().openInputStream(uri)) {
            if (in == null) return "Couldn't open that file";
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            for (int n; (n = in.read(buffer)) > 0;) { out.write(buffer, 0, n); if (out.size() > 16384) return "That file is too big for authorized_keys"; }
            data = out.toByteArray();
        } catch (Exception failure) { return "Couldn't read the file"; }
        String text = new String(data, StandardCharsets.UTF_8).replace("\r\n", "\n");
        String problem = validate(text);
        if (problem != null) return problem;
        File dir = new File(root, "ruby/ssh"), target = new File(dir, "authorized_keys"), temporary = new File(dir, ".authorized_keys.tmp");
        try {
            dir.mkdirs();
            if (Files.isSymbolicLink(dir.toPath()) || Files.isSymbolicLink(target.toPath())) return "Couldn't save the key";
            try (FileOutputStream out = new FileOutputStream(temporary)) { out.write(text.getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception failure) { temporary.delete(); return "Couldn't save the key"; }
        SshService.request(false);                            // a key change stops the service, as before
        return "✓ Key imported. Start SSH to use it.";
    }
}
