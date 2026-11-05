package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.coloredbar.ColoredBar;

public final class ColoredBarEntry implements NativeTweak {
    public Object call(String point, Object[] a) {
        switch (point) {
            case "assets.app-bars": return ColoredBar.assets((java.util.Map)a[0], (String)a[1]);
            case "assets.settings": return ColoredBar.settingsAsset(a[0], a[1]);
            case "app.observe": ColoredBar.observe((E1.q6)a[0]); return null;
            case "settings.page": return ColoredBar.page((String)a[0]);
            case "settings.handle": return ColoredBar.action((String)a[0]);
            case "settings.action": ColoredBar.action((String)a[0]); return null;
            default: return null;
        }
    }
}
