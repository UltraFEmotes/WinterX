package winterx.runtime;

/** The Spring version this core was built for ("0.8.1" unless a version build generated SpringVersionData). */
public final class SpringVersion {
    public static final String DEFAULT = "0.8.1";
    private static final String CURRENT = find();
    private SpringVersion() {}

    public static String current() { return CURRENT; }

    /** Where a package keeps its code for this version: code/ for 0.8.1, code/<version>/ for others. */
    public static String codeDirectory() { return DEFAULT.equals(CURRENT) ? "code/" : "code/" + CURRENT + "/"; }

    private static String find() {
        try { return (String)Class.forName("winterx.runtime.SpringVersionData").getField("VALUE").get(null); }
        catch (ReflectiveOperationException | RuntimeException | LinkageError absent) { return DEFAULT; }
    }
}
