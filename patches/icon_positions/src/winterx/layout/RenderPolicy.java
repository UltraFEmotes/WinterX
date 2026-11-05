package winterx.layout;

/** Native cache keys omit tweak appearance/sparse cells. Reject reuse, never clear retained contents. */
public final class RenderPolicy {
    private RenderPolicy() {}
    public static boolean tilesAllowed() {
        return !winterx.snowy.SnowyHome.enabled() && !winterx.animaper.Animaper.barrelEnabled();
    }
    public static A.o tiles(A.o original) { return tilesAllowed() ? original : null; }
    public static boolean folderLayersAllowed() {
        return !FreeMe.enabled() && !winterx.snowy.SnowyHome.enabled();
    }
}
