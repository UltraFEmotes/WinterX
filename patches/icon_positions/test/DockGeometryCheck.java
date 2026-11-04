import winterx.layout.DockGeometry;

public final class DockGeometryCheck {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    public static void main(String[] args) {
        for (int width : new int[]{320, 640, 1080}) for (int count = 5; count <= 7; count++) {
            int icon = Math.round(width * 57f / 320f), margin = Math.round(width * 17f / 320f);
            DockGeometry.Cell previous = null;
            for (int i = 0; i < count; i++) {
                DockGeometry.Cell cell = DockGeometry.cell(width, icon, width, margin, count, i);
                check(cell != null && cell.size > 0 && cell.size <= icon, "invalid icon size");
                check(cell.left >= margin && cell.left + cell.size <= width - margin, "icon outside dock");
                check(previous == null || previous.left + previous.size < cell.left, "overlapping icons");
                check(cell.contains(cell.left + cell.size / 2f, cell.top + cell.size / 2f), "center not tappable");
                check(!cell.contains(cell.left + cell.size, cell.top) && !cell.contains(Float.NaN, cell.top), "bounds/NaN hit");
                previous = cell;
            }
        }
        for (int count : new int[]{-1, 0, 4, 8, Integer.MAX_VALUE})
            check(DockGeometry.cell(640, 114, 800, 34, count, 0) == null, "invalid/stock count changed");
        check(DockGeometry.cell(640, 114, 800, Integer.MAX_VALUE, 7, 0) == null, "overflow margin accepted");
        check(DockGeometry.cell(1, 1, 0, 0, 7, 0) == null, "tiny geometry accepted");
        check(DockGeometry.cell(640, 114, -1, 34, 7, 0) == null, "negative top accepted");
        System.out.println("Dock geometry: 5–7 icons, scaled profiles, non-overlap, exact hit bounds and invalid-input fallback passed");
    }
}
