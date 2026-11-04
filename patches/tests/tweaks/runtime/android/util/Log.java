package android.util;
/** Keep isolated JVM tests independent of Mac.APK's native logging library. */
public final class Log {
    public static int i(String tag, String message) { return 0; }
    public static int w(String tag, String message, Throwable failure) { return 0; }
}
