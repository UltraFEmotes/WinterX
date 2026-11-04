package android.view;
public class View {
    public static boolean acceptPost = true;
    public static Runnable pending;
    public int background;
    public ViewParent parent;
    public void setBackgroundColor(int color) { background = color; }
    public ViewParent getParent() { return parent; }
    public boolean postDelayed(Runnable runnable, long delay) {
        if (delay != 2500) throw new AssertionError("Wrong boot duration");
        pending = runnable; return acceptPost;
    }
}
