package android.app;
public class Application extends android.content.ContextWrapper {
    public Application() { super(null); }
    @Override public java.io.File getFilesDir() { return new java.io.File(System.getProperty("ruby.test.dir")); }
}
