package winterx.layout;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** DockIn's own 4–7-icon controls. Defaults, validation and behavior ship in this package. */
public final class DockSettings {
    private static final String PAGE = "winterx-layout-p/dockin", ACTION = "winterx-layout-a/dockin-";
    private DockSettings() {}
    public static T6 page(String id) {
        if (!PAGE.equals(id) || !DockIn.installed()) return null;
        List<V6> rows = new ArrayList<>();
        for (int count = DockIn.MIN; count <= DockIn.MAX; count++) rows.add(Z3.g(Z3.a, ACTION + count,
            (count == DockIn.capacity() ? "✓ " : "") + count + " icons", null, null, null, 0x18));
        return new T6(id, "DockIn", Collections.singletonList(new W6("DOCK CAPACITY", null,
            "Default: 4. Move extra icons home before reducing capacity. Finish any icon drag before changing this setting.", null, rows)));
    }
    static boolean write(String name, String value) {
        File root = winterx.extension.NativeRuntime.files(), temporary = null;
        if (root == null) return false;
        File folder = new File(root, "ruby"), target = new File(folder, name);
        try {
            if (Files.isSymbolicLink(folder.toPath()) || Files.isSymbolicLink(target.toPath())) return false;
            if (!folder.isDirectory() && !folder.mkdirs()) return false;
            temporary = File.createTempFile(".dockin-", ".tmp", folder);
            try (FileOutputStream output = new FileOutputStream(temporary)) { output.write(value.getBytes(StandardCharsets.UTF_8)); output.getFD().sync(); }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); return true;
        } catch (Exception failure) { return false; }
        finally { if (temporary != null && temporary.exists()) temporary.delete(); }
    }
    public static void action(String id, x1.i1 controller) {
        if (id != null && id.matches("winterx-layout-a/dockin-[4-7]") && !DockIn.select(id.charAt(id.length() - 1) - '0', DockIn.liveCount(controller)))
            android.util.Log.w("WinterXDockIn", "Capacity unchanged: existing icons or an active drag prevent this change");
    }
}
