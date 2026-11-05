package android.os;

/** Fixed metadata for the isolated SSH info checks, never a live device probe. */
public final class Build {
    public static String MANUFACTURER = "Fixture", MODEL = "Spring Phone";
    public static final String SERIAL = "private-serial-never-print", HOST = "private-host-never-print";
    public static final class VERSION { public static String RELEASE = "15"; public static int SDK_INT = 35; }
}
