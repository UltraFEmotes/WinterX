package winterx.runtime;

import java.io.File;
import java.io.FileInputStream;
import java.security.MessageDigest;

/** Limited WinterX file access for an explicitly verified built-in app. */
public final class TrustedFiles {
    private static final String EXPLORER = "com.winterx.iexplored";
    private static final String RUBY = "com.ruby.manager";
    private static final String EXPLORER_SHA = "e1bbc1b62a20c539898c0bd7faf0fde269fdf13f749d9e1387ff26ec4977c441";
    private static final String EXPLORER_4_SHA = "f0da6ab1c751d5417c9c181e0dca7a9f73c03916b1f09c149816afdc83a6521d";
    private static final String RUBY_17_SHA = "c7f2312c26f8b3c0e4faedbbff11652515f7e9822d0af7dc699e96fb59efed32";
    private static final String RUBY_16_SHA = "dcdf9f9d5d94b680783caf8e0d72cfe97b7608de704c0f8f87e0715226703ea5";
    private static final String RUBY_15_SHA = "6ecbac9191f2aecc59f6baa9a97c829a3aad9a551db210c5e5a5dd0fdb6c7995";
    private static final String RUBY_SHA = "86bd461097c1c8b73e96635322b4580a911570e5d63d62a7474c7369a3e4f1ac";
    private TrustedFiles() {}
    private static String digest(File file) throws Exception {
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        try (FileInputStream in = new FileInputStream(file)) {
            byte[] buffer = new byte[8192]; int n;
            while ((n = in.read(buffer)) >= 0) hash.update(buffer, 0, n);
        }
        byte[] bytes = hash.digest();
        char[] digits = "0123456789abcdef".toCharArray();
        char[] hex = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            int value = bytes[i] & 255;
            hex[i * 2] = digits[value >>> 4];
            hex[i * 2 + 1] = digits[value & 15];
        }
        return new String(hex);
    }
    public static File resolve(File sandbox, String path) {
        try {
            if (sandbox == null || path == null || !path.startsWith("winterx/") || path.length() > 1024 || path.indexOf('\\') >= 0 || path.indexOf('\0') >= 0) return null;
            String relative = path.substring("winterx/".length());
            for (String part : relative.split("/", -1)) if (part.equals(".") || part.equals("..")) return null;
            File own = sandbox.getCanonicalFile();
            File app = own.getParentFile(), sandboxes = app == null ? null : app.getParentFile();
            File root = sandboxes == null ? null : sandboxes.getParentFile();
            if (!"files".equals(own.getName()) || app == null || sandboxes == null ||
                !"sapps-data".equals(sandboxes.getName()) || root == null) return null;
            String id = app.getName();
            // WinterX itself only needs to ask whether the patched runtime is active.
            // This does not grant it the broader file access of the approved apps.
            if ("com.ruby.jailbreak".equals(id) && "status".equals(relative)) {
                return new File(root.getCanonicalFile(), "ruby/boot-ok-v1");
            }
            if (!EXPLORER.equals(id) && !RUBY.equals(id)) return null;
            File installed = new File(root, "sapps/" + id);
            int latest = -1;
            if (installed.isDirectory()) for (String name : installed.list()) {
                try { latest = Math.max(latest, Integer.parseInt(name)); }
                catch (NumberFormatException ignored) { }
            }
            String expected = EXPLORER.equals(id) && latest == 3 ? EXPLORER_SHA :
                              EXPLORER.equals(id) && latest == 4 ? EXPLORER_4_SHA :
                              RUBY.equals(id) && latest == 14 ? RUBY_SHA :
                              RUBY.equals(id) && latest == 15 ? RUBY_15_SHA :
                              RUBY.equals(id) && latest == 16 ? RUBY_16_SHA :
                              RUBY.equals(id) && latest == 17 ? RUBY_17_SHA : null;
            if (expected == null) return null;
            File script = new File(installed, latest + "/main.js");
            if (!script.isFile() || !expected.equals(digest(script))) return null;
            File canonicalRoot = root.getCanonicalFile();
            File result = new File(canonicalRoot, relative).getCanonicalFile();
            String rootPath = canonicalRoot.getPath();
            if (!result.equals(canonicalRoot) && !result.getPath().startsWith(rootPath + File.separator)) return null;
            return result;
        } catch (Exception ignored) { return null; }
    }
    public static boolean protectedRoot(File sandbox, File path) {
        File root = resolve(sandbox, "winterx/");
        return root != null && root.equals(path);
    }
}
