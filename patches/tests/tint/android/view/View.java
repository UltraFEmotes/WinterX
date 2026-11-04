package android.view;
public class View {
    public int color;
    public boolean clickable = true, focusable = true;
    public View(android.content.Context context) { }
    public void setBackgroundColor(int color) { this.color = color; }
    public void setClickable(boolean value) { clickable = value; }
    public void setFocusable(boolean value) { focusable = value; }
}
