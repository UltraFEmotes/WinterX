package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.snowy.SnowyHome;
import winterx.snowy.SnowySettings;

public final class SnowyHomeEntry implements NativeTweak {
    public Object call(String point, Object[] a) {
        switch (point) {
            case "render.custom-icons-enabled": return SnowyHome.enabled();
            case "render.hide-labels": return SnowyHome.hiddenLabels();
            case "render.icon-bitmap": return SnowyHome.icon((E1.a)a[0], (android.graphics.Bitmap)a[1]);
            case "render.badge-artwork": return SnowyHome.artwork((java.util.Map)a[0]);
            case "render.icon.begin": return SnowyHome.beginIcon((android.graphics.Canvas)a[0], (E1.i6)a[1], ((Number)a[3]).intValue());
            case "render.icon.end": return null; // the engine restores the canvas it saved
            case "cache.tiles-allowed": return !SnowyHome.enabled();
            case "cache.folder-layers-allowed": return !SnowyHome.enabled();
            case "settings.page": return SnowySettings.page((String)a[0]);
            case "settings.action": SnowySettings.action((String)a[0]); return null;
            default: return null;
        }
    }
}
