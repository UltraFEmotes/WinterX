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

/** Native Spring Settings models for layout drafts and opt-in SnowyHome appearance. */
public final class LayoutSettings {
    public static final String PAGE = "winterx-layout-p/", ACTION = "winterx-layout-a/";
    private LayoutSettings() {}
    private static V6 row(String id, String title) { return Z3.g(Z3.a, id, title, null, null, null, 0x18); }
    public static void rows(List<V6> rows) {
        winterx.snowy.SnowySettings.rows(rows);
        winterx.ssh.SshSettings.rows(rows);
        winterx.messages.MessagePlus.rows(rows);
        if (FreeMe.installed()) rows.add(row(PAGE + "freeme", "FreeMe"));
        if (DockIn.installed()) rows.add(row(PAGE + "dockin", "DockIn"));
    }
    public static T6 page(String id) {
        T6 snowy = winterx.snowy.SnowySettings.page(id);
        if (snowy != null) return snowy;
        T6 ssh = winterx.ssh.SshSettings.page(id);
        if (ssh != null) return ssh;
        T6 messages = winterx.messages.MessagePlus.page(id);
        if (messages != null) return messages;
        List<V6> rows = new ArrayList<>();
        if ((PAGE + "freeme").equals(id) && FreeMe.installed()) {
            rows.add(row(ACTION + "freeme-toggle", (FreeMe.enabled() ? "✓ " : "") + "Enable FreeMe"));
            return new T6(id, "FreeMe", Collections.singletonList(new W6("HOME SCREEN GRID", null, "Snap to normal grid cells. Leave gaps on any home page. Dock and folder contents stay stock.", null, rows)));
        }
        if ((PAGE + "dockin").equals(id) && DockIn.installed()) {
            for (int value = DockIn.MIN; value <= DockIn.MAX; value++)
                rows.add(row(ACTION + "dockin-" + value, (value == DockIn.capacity() ? "✓ " : "") + value + " icons"));
            return new T6(id, "DockIn", Collections.singletonList(new W6("DOCK CAPACITY", null, "Default: 4. Move extra icons home before reducing capacity. Finish any icon drag before changing this setting.", null, rows)));
        }
        return null;
    }
    static boolean write(String name, String text) {
        File dir = FreeMe.folder(); File temp = null;
        try {
            if (dir == null || Files.isSymbolicLink(dir.toPath()) || Files.isSymbolicLink(new File(dir, name).toPath())) return false;
            if (!dir.isDirectory() && !dir.mkdirs()) return false;
            temp = File.createTempFile(".layout-", ".tmp", dir);
            try (FileOutputStream out = new FileOutputStream(temp)) { out.write(text.getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
            try { Files.move(temp.toPath(), new File(dir, name).toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE); }
            catch (java.nio.file.AtomicMoveNotSupportedException ex) { Files.move(temp.toPath(), new File(dir, name).toPath(), StandardCopyOption.REPLACE_EXISTING); }
            return true;
        } catch (Exception ex) { android.util.Log.e("WinterXLayout", "Could not save preferences", ex); return false; }
        finally { if (temp != null) temp.delete(); }
    }
    public static void action(String id, x1.i1 spring) {
        if (id != null && id.startsWith("winterx-layout-a/messageplus/")) {
            winterx.messages.MessagePlus.action(id); return;
        }
        if (id != null && id.startsWith("winterx-layout-a/ssh/")) {
            winterx.ssh.SshSettings.action(id); return;
        }
        if (id != null && id.startsWith("winterx-layout-a/snowy/")) {
            winterx.snowy.SnowySettings.action(id); return;
        }
        if ((ACTION + "freeme-toggle").equals(id) && FreeMe.installed()) {
            File disabled = new File(FreeMe.folder(), "freeme.disabled");
            if (FreeMe.enabled()) write("freeme.disabled", "disabled\n");
            else if (!Files.isSymbolicLink(disabled.toPath())) disabled.delete();
            return;
        }
        if (id != null && id.matches("winterx-layout-a/dockin-[4-7]")) {
            int count = DockIn.liveCount(spring);
            if (!DockIn.select(id.charAt(id.length() - 1) - '0', count))
                android.util.Log.w("WinterXDockIn", "Capacity unchanged: move extra dock icons home before reducing it");
        }
    }
}
