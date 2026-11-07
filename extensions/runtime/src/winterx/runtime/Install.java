package winterx.runtime;

/**
 * How this WinterX got into Spring: "rootless" (a renamed, re-signed Spring clone built by tools/rootless_launch.py),
 * "macapk" (Mac.APK's desktop runtime) or "rooted" (injected into the original Spring by tools/rooted_launch.py).
 * Tweaks that declare requires_root are refused and skipped on rootless installs.
 */
public final class Install {
    public static final String ORIGINAL = "com.guille.spring";
    private static volatile String kind;
    private Install() {}

    public static String kind() {
        String known = kind;
        if (known != null) return known;
        String vm = System.getProperty("java.vm.name", "");
        String result;
        if (!vm.contains("Dalvik") && !vm.contains("ART")) result = "macapk";
        else {
            String pkg = null;
            try { android.app.Application app = android.app.ActivityThread.currentApplication(); if (app != null) pkg = app.getPackageName(); }
            catch (RuntimeException | LinkageError unavailable) {}
            if (pkg == null) return "rooted";                   // too early to tell; don't cache
            result = ORIGINAL.equals(pkg) ? "rooted" : "rootless";
        }
        kind = result;
        return result;
    }

    public static boolean rootless() { return "rootless".equals(kind()); }
}
