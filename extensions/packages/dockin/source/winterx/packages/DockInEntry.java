package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.extension.NativePlatform;
import winterx.layout.DockIn;
import winterx.layout.DockMotion;
import winterx.layout.DockSettings;

public final class DockInEntry implements NativeTweak {
    public Object call(String point, Object[] a) {
        switch (point) {
            case "dock.icon.begin-legacy": return DockIn.beginLegacy((android.graphics.Canvas)a[0], (E1.q6)a[1], ((Number)a[2]).intValue(), ((Number)a[3]).intValue(), ((Number)a[4]).intValue());
            case "dock.icon.begin-native": return DockIn.beginNative((android.graphics.Canvas)a[0], (E1.q6)a[1], ((Number)a[2]).intValue());
            case "dock.icon.begin-motion": return DockIn.beginMotion((android.graphics.Canvas)a[0], (E1.q6)a[1], (E1.G1)a[2], ((Number)a[3]).floatValue());
            case "dock.icon.end": DockIn.endIcon((android.graphics.Canvas)a[0], ((Number)a[1]).intValue()); return null;
            case "dock.geometry-enabled": return DockIn.geometry((x1.i1)a[0]);
            case "dock.hit": return DockIn.hit((x1.i1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue());
            case "dock.delete-hit": return DockIn.deleteHit((x1.i1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue());
            case "dock.edit-capacity": return DockIn.editCapacity((E1.O1)a[0]);
            case "dock.normalize-capacity": return DockIn.normalizeCapacity((java.util.List)a[0]);
            case "dock.launch-size": return DockIn.launchSize((x1.i1)a[0], (String)a[1]);
            case "dock.location": return DockIn.location((E1.i6)a[0], ((Number)a[1]).intValue(), ((Number)a[2]).intValue());
            case "dock.frame": DockMotion.frame((x1.i1)a[0], (java.util.List)a[1], ((Number)a[2]).longValue()); return null;
            case "dock.hover": return DockIn.hover((E1.O1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue(), ((Number)a[3]).intValue(), (E1.i6)a[4]);
            case "dock.edit-location": return DockIn.editLocation((E1.O1)a[0], ((Number)a[1]).intValue(), ((Number)a[2]).intValue(), (E1.i6)a[3]);
            case "dock.motion-begin": DockMotion.begin((E1.O1)a[0], (E1.i6)a[1]); return null;
            case "home.hover": return DockIn.hover((E1.O1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue(), ((Number)a[3]).intValue(), NativePlatform.editProfile((E1.O1)a[0]));
            case "home.edit-location": return DockIn.editLocation((E1.O1)a[0], ((Number)a[1]).intValue(), ((Number)a[2]).intValue(), NativePlatform.editProfile((E1.O1)a[0]));
            case "home.drag-begin": DockMotion.begin((E1.O1)a[0], NativePlatform.editProfile((E1.O1)a[0])); return null;
            case "settings.page": return DockSettings.page((String)a[0]);
            case "settings.action": DockSettings.action((String)a[0], a.length > 1 ? (x1.i1)a[1] : null); return null;
            default: return null;
        }
    }
}
