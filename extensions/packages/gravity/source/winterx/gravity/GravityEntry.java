package winterx.gravity;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Collections;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

public final class GravityEntry implements NativeTweak {
    private TweakContext context;
    private Gravity gravity;

    @Override public void start(TweakContext context) throws Exception {
        this.context = context;
        gravity = new Gravity(context);
        gravity.shakeEnabled = !"off".equals(read("shake.txt"));
        gravity.start();
    }

    @Override public void stop() { if (gravity != null) gravity.stop(); }

    @Override public Object call(String point, Object[] a) throws Exception {
        if (!context.active()) return null;
        switch (point) {
            case "render.icon.begin": return gravity.beginIcon((android.graphics.Canvas)a[0], (E1.i6)a[1], ((Number)a[2]).intValue(), ((Number)a[3]).intValue());
            case "render.icon.end": return null;                 // the engine restores the canvas it saved
            case "render.home.icon-context": gravity.context((E1.q6)a[0], (I1.b0)a[1]); return null;
            case "cache.tiles-allowed": return !gravity.active();  // draw each icon separately while they move
            case "render.hide-labels": return gravity.active();     // loose icons look and stack better without labels
            case "settings.page": return "main".equals(a[0]) ? page() : null;   // only our own page, never Spring's
            case "settings.tap":
                if ("drop".equals(a[1])) gravity.toggle();
                else if ("shake".equals(a[1])) { gravity.shakeEnabled = !gravity.shakeEnabled; write("shake.txt", gravity.shakeEnabled ? "on" : "off"); }
                return null;
            default: return null;
        }
    }

    private T6 page() {
        String row = "winterx-tw-r/" + context.id() + "/main/";
        V6 drop = Z3.g(Z3.a, row + "drop", gravity.active() ? "Put the icons back" : "Drop the icons", null, null, null, 0x18);
        V6 shake = Z3.g(Z3.a, row + "shake", (gravity.shakeEnabled ? "✓ " : "") + "Shake to start and stop", null, null, null, 0x18);
        W6 section = new W6("GRAVITY", null,
            "Shake the phone to drop the icons; they fall the way it's tilted. Grab and throw them. Shake again or press Home to put them back.",
            null, Arrays.asList(drop, shake));
        return new T6("winterx-tw-p/" + context.id(), "Gravity", Collections.singletonList(section));
    }

    private String read(String name) {
        try { File file = context.data(name); return file.isFile() ? new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8).trim() : null; }
        catch (Exception unavailable) { return null; }
    }
    private void write(String name, String value) {
        try { File file = context.data(name); file.getParentFile().mkdirs(); Files.write(file.toPath(), value.getBytes(StandardCharsets.UTF_8)); }
        catch (Exception ignored) {}
    }
}
