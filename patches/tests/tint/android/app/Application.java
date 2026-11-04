package android.app;
public class Application extends android.content.Context {
    public java.io.File getFilesDir() { return new java.io.File(System.getProperty("ruby.test.dir")); }
}
