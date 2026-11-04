package android.graphics;

/** Software bitmap test double. Production uses Android/Mac.APK's real bitmap. */
public final class Bitmap {
    public enum Config { ARGB_8888 }
    private final int width, height;
    private final int[] pixels;
    private boolean recycled;
    private Bitmap(int width, int height) { this.width = width; this.height = height; pixels = new int[width * height]; }
    public static Bitmap createBitmap(int width, int height, Config config) { return new Bitmap(width, height); }
    public int getWidth() { return width; }
    public int getHeight() { return height; }
    public boolean isRecycled() { return recycled; }
    public void recycle() { recycled = true; }
    public void getPixels(int[] output, int offset, int stride, int x, int y, int w, int h) {
        for (int row = 0; row < h; row++) System.arraycopy(pixels, (y + row) * width + x, output, offset + row * stride, w);
    }
    public void setPixels(int[] input, int offset, int stride, int x, int y, int w, int h) {
        for (int row = 0; row < h; row++) System.arraycopy(input, offset + row * stride, pixels, (y + row) * width + x, w);
    }
}
