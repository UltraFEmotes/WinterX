package android.app;

/** Compile-only stub for Android's hidden ActivityThread; the real class is used on devices and in Mac.APK. */
public final class ActivityThread {
    private ActivityThread() {}
    public static Application currentApplication() { throw new UnsupportedOperationException("compile-time stub"); }
}
