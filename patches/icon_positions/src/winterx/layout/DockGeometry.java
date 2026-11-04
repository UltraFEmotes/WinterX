package winterx.layout;

/** Pure, count-aware dock bounds. Four icons retain the native layout. */
public final class DockGeometry {
    private DockGeometry() {}
    public static final class Cell {
        public final int left, top, size;
        Cell(int left, int top, int size) { this.left = left; this.top = top; this.size = size; }
        public boolean contains(float x, float y) {
            return Float.isFinite(x) && Float.isFinite(y) &&
                x >= left && x < left + size && y >= top && y < top + size;
        }
    }
    /** Null means retain stock, including malformed/unsupported profiles. */
    public static Cell cell(int width, int icon, int stockTop, int margin, int count, int index) {
        if (count <= 4 || count > 7 || index < 0 || index >= count || width <= 0 ||
            icon <= 0 || icon > width || margin < 0 || 2L * margin >= width || stockTop < 0) return null;
        double pitch = (width - 2.0 * margin) / count;
        int size = (int)Math.floor(Math.min(icon, pitch - width * 8.0 / 320.0));
        if (size <= 0) return null;
        int left = (int)Math.round(margin + index * pitch + (pitch - size) / 2.0);
        int top = stockTop + (icon - size) / 2;
        return new Cell(left, top, size);
    }
}
