package android.view;
public class ViewGroup extends View implements ViewParent {
    public boolean removed;
    public void removeView(View view) { removed = true; view.parent = null; }
    public static class LayoutParams {
        public LayoutParams(int width, int height) {
            if (width != -1 || height != -1) throw new AssertionError("Not fullscreen");
        }
    }
}
