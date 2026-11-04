package android.graphics;
public class Paint {
  public enum Cap { ROUND }
  public enum Align { CENTER }
  public int color;
  public Paint(int flags) {}
  public void setColor(int color) { this.color=color; }
  public void setStrokeCap(Cap cap) {}
  public void setStrokeWidth(float width) {}
  public Typeface setTypeface(Typeface face) { return face; }
  public void setTextAlign(Align align) {}
  public void setTextSize(float size) {}
}
