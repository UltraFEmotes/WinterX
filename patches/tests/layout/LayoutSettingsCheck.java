import java.io.File;
import java.nio.file.Files;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.FreeMe;
import winterx.layout.DockIn;
import winterx.layout.LayoutSettings;
import winterx.tweaks.TweakSettings;
public class LayoutSettingsCheck {
    static void check(boolean ok, String why) { if (!ok) throw new AssertionError(why); }
    static boolean contains(E1.T6 page, String id) {
        for (Object section : page.c) for (Object entry : ((E1.W6)section).c) if (id.equals(((E1.V6)entry).a)) return true;
        return false;
    }
    static E1.T6 routed(String id, boolean packaged) throws Exception {
        return packaged ? (E1.T6)Class.forName("ruby.RubyHooks").getMethod("settingsPage", String.class).invoke(null, id) : LayoutSettings.page(id);
    }
    public static void main(String[] args) throws Exception {
        File dir = new File(System.getProperty("ruby.test.dir"), "ruby"); dir.mkdirs();
        boolean packaged = args.length > 0 && Boolean.parseBoolean(args[0]);
        E1.T6 ios4 = E1.Z3.c, ios6 = null;
        for (Object value : E1.Z3.s) if ("root".equals(((E1.T6)value).a)) ios6 = (E1.T6)value;
        check(ios6 != null, "missing native iOS 6 root");
        check(routed(LayoutSettings.PAGE + "freeme", packaged) == null && routed(LayoutSettings.PAGE + "dockin", packaged) == null, "uninstalled pages visible");
        new File(dir, "freeme.enabled").createNewFile(); new File(dir, "dockin.enabled").createNewFile();
        for (E1.T6 root : List.of(ios4, ios6)) {
            E1.T6 decorated = TweakSettings.decorate(root);
            check(contains(decorated, LayoutSettings.PAGE + "freeme") && contains(decorated, LayoutSettings.PAGE + "dockin"), "layout tweak missing from native root");
            check(TweakSettings.decorate(decorated) == decorated, "duplicate tweak section");
        }
        E1.T6 page = routed(LayoutSettings.PAGE + "freeme", packaged);
        check(page != null && ((E1.W6)page.c.get(0)).c.size() == 1, "FreeMe native toggle missing");
        LayoutSettings.action(LayoutSettings.ACTION + "freeme-toggle", null);
        check(!FreeMe.enabled() && FreeMe.installed(), "toggle did not preserve installation");
        LayoutSettings.action(LayoutSettings.ACTION + "freeme-toggle", null);
        check(FreeMe.enabled(), "toggle did not enable");
        page = routed(LayoutSettings.PAGE + "dockin", packaged);
        List<?> rows = ((E1.W6)page.c.get(0)).c;
        check(rows.size() == 4 && ((E1.V6)rows.get(0)).b.contains("✓"), "DockIn default 4/options incorrect");
        LayoutSettings.action(LayoutSettings.ACTION + "dockin-7", null);
        check(DockIn.capacity() == 4, "unknown live icon count allowed preference changes");
        Field unsafeField = Unsafe.class.getDeclaredField("theUnsafe"); unsafeField.setAccessible(true);
        x1.i1 host = (x1.i1)((Unsafe)unsafeField.get(null)).allocateInstance(x1.i1.class);
        Field dock = x1.i1.class.getDeclaredField("M1"); dock.setAccessible(true); dock.set(host, new ArrayList<>());
        for (int value = 4; value <= 7; value++) {
            LayoutSettings.action(LayoutSettings.ACTION + "dockin-" + value, host);
            check(DockIn.capacity() == value, "valid DockIn selection failed");
        }
        LayoutSettings.action(LayoutSettings.ACTION + "dockin-3", null);
        check(DockIn.capacity() == 7 && !DockIn.select(4, 7), "invalid/reducing selection changed capacity");
        for (String bad : List.of("0", "3", "8", "9999999999999999999999999", "5.5", "not a number")) {
            Files.writeString(new File(dir, "dockin.capacity").toPath(), bad);
            check(DockIn.capacity() == 4, "malformed preference escaped bounds");
        }
        new File(dir, "safe-mode.enabled").createNewFile();
        check(routed(LayoutSettings.PAGE + "freeme", packaged) == null && routed(LayoutSettings.PAGE + "dockin", packaged) == null, "Safe Mode left native pages active");
        check(!contains(TweakSettings.decorate(ios6), LayoutSettings.PAGE + "freeme"), "Safe Mode left root row active");
        System.out.println("Native layout Settings: iOS 4/6 roots, routing, toggle, 4–7/default-4 capacity, malformed preference and Safe Mode passed");
    }
}
