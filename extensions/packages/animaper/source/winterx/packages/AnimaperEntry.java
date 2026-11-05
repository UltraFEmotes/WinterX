package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.animaper.Animaper;
import winterx.animaper.AnimaperSettings;

/** Animaper's independently installed implementation of the public hooks. */
public final class AnimaperEntry implements NativeTweak {
    public Object call(String point, Object[] a) {
        switch (point) {
            case "home.draw-location": return Animaper.location((E1.i6)a[0], (E1.c)a[1], ((Number)a[2]).intValue(), ((Number)a[3]).intValue());
            case "render.home.begin": return Animaper.beginFrame((android.graphics.Canvas)a[0], ((Number)a[1]).longValue(), (E1.S1)a[2], (E1.l4)a[3]);
            case "render.home.icon-context": Animaper.context((E1.q6)a[0], (I1.b0)a[1]); return null;
            case "render.home.end": Animaper.endFrame(a[0]); return null;
            case "render.icon.begin": return Animaper.beginIcon((android.graphics.Canvas)a[0], (E1.i6)a[1], ((Number)a[2]).intValue(), ((Number)a[3]).intValue());
            case "render.icon.end": Animaper.endIcon((android.graphics.Canvas)a[0], ((Number)a[1]).intValue()); return null;
            case "cache.tiles-allowed": return !Animaper.barrelEnabled();
            case "settings.page": return AnimaperSettings.page((String)a[0]);
            case "settings.action": AnimaperSettings.select((String)a[0]); return null;
            default: return null;
        }
    }
}
