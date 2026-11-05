package android.os;
/** Main-thread boundary fixture; no desktop/UI event loop. */
public final class Looper {
    private static final Looper MAIN = new Looper();
    private static final ThreadLocal<Boolean> IS_MAIN = ThreadLocal.withInitial(() -> Boolean.TRUE);
    public static Looper getMainLooper() { return MAIN; }
    public static Looper myLooper() { return IS_MAIN.get() ? MAIN : null; }
    public static void worker() { IS_MAIN.set(false); }
}
