package android.graphics;
import java.util.ArrayList;
import java.util.List;
public class Canvas {
  public int background, lines;
  public int getWidth() { return 640; }
  public List<String> text = new ArrayList<>();
  public List<Integer> colors = new ArrayList<>();
  public void drawColor(int color) { background=color; }
  public void drawLine(float x1,float y1,float x2,float y2,Paint paint) { lines++; }
  public void drawText(String value,float x,float y,Paint paint) { text.add(value); colors.add(paint.color); }
}
