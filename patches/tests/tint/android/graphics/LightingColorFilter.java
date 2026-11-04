package android.graphics;
public class LightingColorFilter extends ColorFilter {
    public final int multiply, add;
    public LightingColorFilter(int multiply, int add) { this.multiply = multiply; this.add = add; }
}
