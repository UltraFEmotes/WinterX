package android.app;
public class Activity extends android.content.Context {
    public android.view.View last;
    public android.view.ViewGroup root = new android.view.ViewGroup();
    public void addContentView(android.view.View view, android.view.ViewGroup.LayoutParams params) {
        last = view; view.parent = root;
    }
    public java.io.File getFilesDir() { return new java.io.File(System.getProperty("ruby.test.dir")); }
}
