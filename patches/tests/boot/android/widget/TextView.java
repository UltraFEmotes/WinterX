package android.widget;
public class TextView extends android.view.View {
    public String text;
    public int textColor, gravity;
    public float size;
    public TextView(android.content.Context context) {}
    public void setText(CharSequence value) { text = value.toString(); }
    public void setTextColor(int color) { textColor = color; }
    public void setGravity(int value) { gravity = value; }
    public void setTextSize(float value) { size = value; }
}
