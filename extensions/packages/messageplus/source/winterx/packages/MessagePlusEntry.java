package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.messages.MessagePlus;

public final class MessagePlusEntry implements NativeTweak {
    public Object call(String point, Object[] a) {
        switch (point) {
            case "messages.list-button": return MessagePlus.button((E1.N0)a[0]);
            case "media.photo-quality": return MessagePlus.photoQuality(((Number)a[0]).intValue());
            case "messages.pointer-down": return MessagePlus.press((x1.i1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue());
            case "messages.pointer-move": return MessagePlus.move((x1.i1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue());
            case "messages.pointer-up": return MessagePlus.release((x1.i1)a[0], ((Number)a[1]).floatValue(), ((Number)a[2]).floatValue());
            case "messages.pointer-cancel": MessagePlus.cancel((com.guille.spring.LauncherActivity)a[0]); return null;
            case "settings.page": return MessagePlus.page((String)a[0]);
            case "settings.action": MessagePlus.action((String)a[0]); return null;
            default: return null;
        }
    }
}
