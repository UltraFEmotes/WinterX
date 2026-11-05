package android.app;

/** Public, minimal metadata objects; no platform UI, files, native code or network. */
public final class ActivityThread {
    public static Application application = new Application();
    public static Application currentApplication() { return application; }
    public static final class Application {
        public final Resources resources = new Resources();
        public String getPackageName() { return "com.guille.spring"; }
        public PackageManager getPackageManager() { return new PackageManager(); }
        public Resources getResources() { return resources; }
    }
    public static final class PackageManager {
        public PackageInfo getPackageInfo(String name, int flags) { return new PackageInfo(); }
    }
    public static final class PackageInfo { public String versionName = "0.8.1"; }
    public static final class Resources {
        public final Metrics metrics = new Metrics();
        public Metrics getDisplayMetrics() { return metrics; }
    }
    public static final class Metrics { public int widthPixels = 640, heightPixels = 960, densityDpi = 320; }
}
