package android.app;
public class Activity extends android.content.ContextWrapper {
    public Activity() { super(null); }
    @Override public java.io.File getFilesDir() { return new java.io.File(System.getProperty("ruby.test.dir")); }
}
