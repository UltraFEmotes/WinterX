package winterx.layout;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.util.Collections;

/** FreeMe's own Settings code, installed from its package. Saved cells are untouched. */
public final class FreeMeSettings {
    private static final String PAGE = "winterx-layout-p/freeme", ACTION = "winterx-layout-a/freeme-toggle";
    private FreeMeSettings() {}
    public static T6 page(String id) {
        if (!PAGE.equals(id) || !FreeMe.installed()) return null;
        V6 row = Z3.g(Z3.a, ACTION, (FreeMe.enabled() ? "✓ " : "") + "Enable FreeMe", null, null, null, 0x18);
        return new T6(id, "FreeMe", Collections.singletonList(new W6("HOME SCREEN GRID", null,
            "Snap to normal grid cells. Leave gaps on any home page. Dock and folder contents stay native.", null, Collections.singletonList(row))));
    }
    public static void action(String id) {
        if (!ACTION.equals(id) || !FreeMe.installed()) return;
        File disabled = new File(FreeMe.folder(), "freeme.disabled");
        try {
            if (Files.isSymbolicLink(disabled.toPath())) return;
            if (FreeMe.enabled()) try (FileOutputStream output = new FileOutputStream(disabled)) { output.write("disabled\n".getBytes(java.nio.charset.StandardCharsets.UTF_8)); output.getFD().sync(); }
            else Files.deleteIfExists(disabled.toPath());
        } catch (Exception failure) { android.util.Log.w("WinterXFreeMe", "Preference unchanged", failure); }
    }
}
