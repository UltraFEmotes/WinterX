package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.layout.FreeMe;
import winterx.layout.FreeMeHomeApi;
import winterx.layout.FreeMeSettings;
import winterx.layout.SpringHooks;

public final class FreeMeEntry implements NativeTweak {
    public Object call(String point, Object[] a) throws Exception {
        switch (point) {
            case "home.custom-grid-enabled": return FreeMe.enabled();
            case "home.entries": return FreeMe.entries((java.util.List)a[0], (E1.i6)a[1], ((Number)a[2]).intValue());
            case "folder.background-entries": return FreeMe.folderEntries((E1.q6)a[0]);
            case "home.launch-location": return FreeMe.animation((x1.i1)a[0], (E1.A0)a[1]);
            case "home.delete-hit": return FreeMe.deleteHit((x1.i1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue());
            case "home.location": return SpringHooks.location((E1.i6)a[0], (E1.c)a[1], ((Number)a[2]).intValue());
            case "home.edit-location": return SpringHooks.editLocation((E1.O1)a[0], ((Number)a[1]).intValue(), ((Number)a[2]).intValue());
            case "home.animated-location": return SpringHooks.animatedLocation((E1.O1)a[0], ((Number)a[1]).intValue(), ((Number)a[2]).intValue());
            case "home.hover": return SpringHooks.hover((E1.O1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue(), ((Number)a[3]).intValue());
            case "home.drag-begin": SpringHooks.begin((E1.O1)a[0], ((Number)a[1]).intValue(), ((Number)a[2]).intValue()); return null;
            case "home.before-drop": SpringHooks.beforeDrop((E1.O1)a[0]); return null;
            case "home.pointer": SpringHooks.pointer((x1.i1)a[0], ((Number)a[1]).intValue()); return null;
            case "cache.folder-layers-allowed": return !FreeMe.enabled();
            case "settings.page": return FreeMeSettings.page((String)a[0]);
            case "settings.action": FreeMeSettings.action((String)a[0]); return null;
            case "home.snapshot": return FreeMeHomeApi.snapshot((x1.i1)a[0]);
            case "home.move": return FreeMeHomeApi.move((x1.i1)a[0], (org.json.JSONObject)a[1]);
            default: return null;
        }
    }
}
