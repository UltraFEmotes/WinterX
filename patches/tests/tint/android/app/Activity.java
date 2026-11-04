package android.app;
public class Activity extends Application {
    public android.view.View overlay;
    public void addContentView(android.view.View view, android.view.ViewGroup.LayoutParams params) { overlay = view; }
}
