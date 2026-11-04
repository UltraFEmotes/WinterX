import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.FreeMe;
import winterx.layout.GridSlots;
import winterx.layout.IconRuntime;
import winterx.layout.LayoutSettings;
import winterx.layout.DockIn;
import winterx.layout.SpringHooks;

/** Actual patched edit, renderer, touch and animation classes, using isolated data only. */
public class PatchedFreeMeCheck {
    static Unsafe unsafe() throws Exception { Field f = Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o, String name, Object v) throws Exception { Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o, v); }
    static void check(boolean ok, String why) { if (!ok) throw new AssertionError(why); }
    static E1.a app(String id) throws Exception { E1.a a = (E1.a)unsafe().allocateInstance(E1.a.class); set(a, "a", id); return a; }
    static List<E1.c> entries(List<String> ids) throws Exception {
        List<E1.c> result = new ArrayList<>();
        for (int i = 0; i < ids.size(); i++) result.add(new E1.c(app(ids.get(i)), i / 4, i % 4));
        return result;
    }
    static List<String> page(E1.i2 model, int n) { return (List<String>)model.b.get(n); }
    static void drop(E1.O1 edit, int sourcePage, int index, int targetPage, E1.i6 profile, int slot, long now) {
        edit.o(sourcePage, index, 40f, 100f, now);
        check(edit.m != null, "drag failed to start");
        M1.b point = E1.d4.w(profile, slot / 4, slot % 4);
        float scale = profile.b / 320f;
        edit.m.f = ((Number)point.h).floatValue() / scale + 3f + edit.m.c + (E1.t.j ? 30f : 29.5f);
        edit.m.g = ((Number)point.w).floatValue() / scale + 4f + edit.m.d + 37f;
        edit.w = targetPage; edit.D = "two"; // stale hover must not create a new folder
        edit.x(now + 1);
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); System.setProperty("ruby.test.dir", root.toString());
        E1.t.j = args.length > 1 && Boolean.parseBoolean(args[1]);
        File dir = new File(root, "ruby"); dir.mkdirs();
        File legacy = new File(dir, "icon-positions-v1.json");
        Files.writeString(legacy.toPath(), "{\"version\":1,\"positions\":[{\"page\":0,\"id\":\"one\",\"x\":0.7,\"y\":0.8}]}");
        byte[] legacyBefore = Files.readAllBytes(legacy.toPath());
        for (String name : List.of("ios4_pages.json", "ios6_pages.json", "ios7_pages.json")) Files.writeString(new File(root, name).toPath(), "protected " + name);
        new File(dir, "free-icons.enabled").createNewFile();
        E1.i6 profile = (E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile, "b", 640); set(profile, "c", E1.t.j ? 1136 : 960); set(profile, "d", 40); set(profile, "e", 114);
        set(profile, "k", new E1.k0(16, 4, 34, 27, 38, 62, 0, 0, List.of(34, 186, 338, 490)));
        x1.i1 host = (x1.i1)unsafe().allocateInstance(x1.i1.class);
        set(host, "e", profile); set(host, "b", E1.r7.T); set(host, "L6", 0f);
        x1.P0 callback = x1.P0.class.getDeclaredConstructor(x1.i1.class, int.class).newInstance(host, 0);
        E1.i2 model = new E1.i2(new ArrayList<>(List.of("dock")), new ArrayList<>(List.of(new ArrayList<>(List.of("one", "two", "three")), new ArrayList<>(List.of("four")))), new LinkedHashMap<>());
        List<E1.c> stock = entries(page(model, 0));
        check(FreeMe.entries(stock, profile, 0) == stock, "uninstalled FreeMe changed entries");
        new File(dir, "freeme.enabled").createNewFile();
        E1.O1 edit = new E1.O1(model, 16, 4, callback);
        drop(edit, 0, 0, 0, profile, 11, 1000);
        E1.i2 moved = edit.r();
        check(page(moved, 0).equals(page(model, 0)), "same-page move changed stock order");
        check(moved.a.equals(model.a), "FreeMe changed dock");
        GridSlots grid = GridSlots.load(new File(dir, "freeme-slots-v1.json"));
        check(grid.get(0, "one") == 11 && grid.get(0, "two") == 1 && grid.get(0, "three") == 2, "grid slots not preserved");
        check(stock.get(0).b == 0 && stock.get(0).c == 0, "stock entries mutated");
        set(host, "L1", stock); set(host, "S1", List.of(entries(page(model, 1)))); set(host, "M1", new ArrayList<>());
        M1.b expected = E1.d4.w(profile, 2, 3);
        int x = ((Number)expected.h).intValue(), y = ((Number)expected.w).intValue();
        E1.A0 hit = host.o1(x + 10, y + 10);
        check(hit != null && hit.b == 0, "touch missed snapped icon");
        check(host.o1(44, 77) == null, "old cell still tappable");
        M1.b animation = host.n4(hit);
        check(((Number)animation.h).intValue() == x && ((Number)animation.w).intValue() == y, "launch animation disagrees with grid");
        E1.q6 state = (E1.q6)unsafe().allocateInstance(E1.q6.class);
        set(state, "a", profile); set(state, "b", stock); set(state, "n0", new ArrayList<>()); set(state, "o0", 0f);
        I1.b0 draw = (I1.b0)I1.h0.i0(state).get(0);
        check(draw.b == x && draw.c == y, "renderer disagrees with touch");
        grid.put(0, "android:freeme-delete", 10);
        grid.save(new File(dir, "freeme-slots-v1.json"));
        set(host, "L1", List.of(new E1.c(app("android:freeme-delete"), 0, 0)));
        M1.b deletePoint = E1.d4.w(profile, 2, 2);
        check("android:freeme-delete".equals(host.I(((Number)deletePoint.h).floatValue() + 2f, ((Number)deletePoint.w).floatValue() + 2f)), "native delete badge missed moved cell");
        check(host.I(36f, 69f) == null, "old delete badge remained active");
        set(host, "L1", stock);
        E1.O1 hovering = new E1.O1(moved, 16, 4, callback);
        hovering.o(0, 1, 40f, 100f, 1500);
        E1.I1 hover = hovering.p(x / 2f + (E1.t.j ? 30f : 29.5f), y / 2f + 37f, 0);
        check(hover != null && ((E1.j2)hover.d).a == 0 && ((E1.j2)hover.d).b == 0, "hover targeted compact-grid index instead of moved icon");
        hovering.x(1501);
        Map<String, E1.P1> folders = new LinkedHashMap<>();
        folders.put("folder", new E1.P1(List.of("inside"), "Stock Folder"));
        E1.i2 folderModel = new E1.i2(new ArrayList<>(), new ArrayList<>(List.of(new ArrayList<>(List.of("folder", "one")))), folders);
        E1.O1 folderEdit = new E1.O1(folderModel, 16, 4, callback);
        folderEdit.o(0, 1, 40f, 100f, 1600);
        M1.b folderPoint = E1.d4.w(profile, 0, 0);
        E1.I1 folderHover = folderEdit.p(((Number)folderPoint.h).floatValue() / 2f + 29.5f, ((Number)folderPoint.w).floatValue() / 2f + 37f, 0);
        check(folderHover != null && ((E1.j2)folderHover.d).b == 2, "existing folder lost native hover target");
        check(folderEdit.g.containsKey("folder") && folderModel.c.get("folder") == folders.get("folder"), "folder contents changed");
        folderEdit.D = "folder"; folderEdit.x(1601);
        check(page(folderEdit.r(), 0).equals(List.of("folder")) &&
              ((E1.P1)folderEdit.r().c.get("folder")).b.containsAll(List.of("inside", "one")), "native home-to-folder drop lost routing/membership");
        E1.i2 dockFolderModel = new E1.i2(new ArrayList<>(List.of("dock")), new ArrayList<>(List.of(new ArrayList<>(List.of("folder")))), folders);
        E1.O1 dockFolder = new E1.O1(dockFolderModel, 16, 4, callback);
        dockFolder.o(-1, 0, 40f, 100f, 1700); dockFolder.D = "folder"; dockFolder.x(1701);
        check(dockFolder.r().a.isEmpty() && ((E1.P1)dockFolder.r().c.get("folder")).b.containsAll(List.of("inside", "dock")), "native dock-to-folder drop lost routing/membership");
        E1.O1 cross = new E1.O1(moved, 16, 4, callback);
        drop(cross, 0, 0, 1, profile, 15, 2000);
        E1.i2 across = cross.r();
        check(page(across, 0).equals(List.of("two", "three")) && page(across, 1).equals(List.of("four", "one")), "cross-page membership wrong or duplicated");
        grid = GridSlots.load(new File(dir, "freeme-slots-v1.json"));
        check(grid.get(0, "one") == null && grid.get(1, "one") == 15 && grid.get(0, "two") == 1, "cross-page slots lost");
        byte[] before = Files.readAllBytes(new File(dir, "freeme-slots-v1.json").toPath());
        E1.O1 collision = new E1.O1(across, 16, 4, callback);
        drop(collision, 1, 1, 1, profile, 0, 3000);
        check(page(collision.r(), 1).equals(page(across, 1)), "collision changed membership");
        check(Arrays.equals(before, Files.readAllBytes(new File(dir, "freeme-slots-v1.json").toPath())), "collision overwrote saved grid");
        Map<String, Integer> added = grid.resolve(0, List.of("two", "three", "new-app"), 16);
        check(new HashSet<>(added.values()).size() == 3 && added.get("two") == 1 && added.get("three") == 2, "new app overlapped stored cells");
        E1.O1 newPage = new E1.O1(across, 16, 4, callback);
        drop(newPage, 1, 1, 2, profile, 12, 4000);
        check(page(newPage.r(), 2).equals(List.of("one")), "new-page drop failed");
        check(newPage.r().a.equals(model.a), "cross-page move changed dock");
        // Native dock-to-home reorders its transient hole before the FreeMe drop hook.
        E1.O1 fromDock = new E1.O1(moved, 16, 4, callback);
        fromDock.o(-1, 0, 40f, E1.t.f - 50f, 4500);
        fromDock.f.remove("\u0000hole");
        ((List<String>)fromDock.e.get(0)).add("\u0000hole");
        fromDock.n = 0; fromDock.o = 3;
        M1.b emptyCell = E1.d4.w(profile, 3, 0);
        fromDock.m.f = ((Number)emptyCell.h).floatValue() / 2f + fromDock.m.c + (E1.t.j ? 30f : 29.5f);
        fromDock.m.g = ((Number)emptyCell.w).floatValue() / 2f + fromDock.m.d + 37f;
        fromDock.w = 0; fromDock.D = null; fromDock.x(4501);
        check(fromDock.r().a.isEmpty() && page(fromDock.r(), 0).equals(List.of("one", "two", "three", "dock")), "dock-to-home lost or duplicated icon");
        check(GridSlots.load(new File(dir, "freeme-slots-v1.json")).get(0, "dock") == 12, "dock-to-home did not snap to chosen empty cell");
        // A failed sparse-grid write restores both native memberships before stock finalizes its hole.
        File slotsFile = new File(dir, "freeme-slots-v1.json"), preserved = new File(dir, "preserved-slots.json");
        Files.move(slotsFile.toPath(), preserved.toPath());
        Files.createSymbolicLink(slotsFile.toPath(), preserved.toPath());
        E1.O1 failed = new E1.O1(moved, 16, 4, callback);
        failed.o(-1, 0, 40f, E1.t.f - 50f, 4600);
        failed.f.remove("\u0000hole"); ((List<String>)failed.e.get(0)).add("\u0000hole"); failed.n = 0; failed.o = 3;
        failed.m.f = ((Number)emptyCell.h).floatValue() / 2f + failed.m.c + (E1.t.j ? 30f : 29.5f);
        failed.m.g = ((Number)emptyCell.w).floatValue() / 2f + failed.m.d + 37f;
        failed.w = 0; failed.x(4601);
        check(failed.r().a.equals(moved.a) && page(failed.r(), 0).equals(page(moved, 0)), "failed dock transfer did not restore memberships");
        Files.delete(slotsFile.toPath()); Files.move(preserved.toPath(), slotsFile.toPath());
        byte[] beforeNativeDock = Files.readAllBytes(slotsFile.toPath());
        E1.O1 intoDock = new E1.O1(moved, 16, 4, callback);
        intoDock.o(0, 0, 40f, 100f, 4700);
        ((List<String>)intoDock.e.get(0)).remove("\u0000hole"); intoDock.f.add("\u0000hole"); intoDock.n = -1; intoDock.o = 1;
        intoDock.m.g = profile.c / 2f - 45f + intoDock.m.d; intoDock.w = 0; intoDock.D = null; intoDock.x(4701);
        check(intoDock.r().a.equals(List.of("dock", "one")) && page(intoDock.r(), 0).equals(List.of("two", "three")), "native home-to-dock transfer lost membership");
        check(Arrays.equals(beforeNativeDock, Files.readAllBytes(slotsFile.toPath())), "native dock transfer rewrote sparse preferences");
        byte[] beforeAvailability = Files.readAllBytes(slotsFile.toPath());
        E1.O1 refreshed = new E1.O1(moved, 16, 4, callback);
        refreshed.o(0, 0, 40f, 100f, 4800);
        ((List<String>)refreshed.e.get(0)).remove("two");
        ((List<String>)refreshed.e.get(1)).add("new-live-app");
        refreshed.x(4801);
        check(!page(refreshed.r(), 0).contains("two") && page(refreshed.r(), 1).contains("new-live-app"), "snapshot overwrote changing app availability");
        check(Arrays.equals(beforeAvailability, Files.readAllBytes(slotsFile.toPath())), "availability change rewrote sparse preferences");
        E1.O1 interrupted = new E1.O1(moved, 16, 4, callback);
        interrupted.o(0, 0, 40f, 100f, 4900);
        ((List<String>)interrupted.e.get(0)).remove("\u0000hole"); interrupted.f.add("\u0000hole"); interrupted.n = -1; interrupted.o = 1;
        new File(dir, "freeme.disabled").createNewFile(); interrupted.x(4901);
        check(interrupted.r().a.equals(moved.a) && page(interrupted.r(), 0).equals(page(moved, 0)), "disabled mid-drag did not restore original memberships");
        check(Arrays.equals(beforeAvailability, Files.readAllBytes(slotsFile.toPath())), "interrupted drag overwrote saved cells");
        new File(dir, "freeme.disabled").delete();
        E1.O1 cancelled = new E1.O1(moved, 16, 4, callback);
        cancelled.o(0, 0, 40f, 100f, 4950); set(host, "W1", cancelled);
        cancelled.m.f = 200f; cancelled.m.g = 200f; cancelled.w = 1;
        SpringHooks.pointer(host, 2); SpringHooks.pointer(host, 3); cancelled.x(4951);
        check(cancelled.r().a.equals(moved.a) && page(cancelled.r(), 0).equals(page(moved, 0)) && page(cancelled.r(), 1).equals(page(moved, 1)), "cancelled pointer committed cross-page movement");
        check(Arrays.equals(beforeAvailability, Files.readAllBytes(slotsFile.toPath())), "cancelled pointer changed saved cells");
        cancelled.j(6000); set(host, "W1", null);
        LayoutSettings.action(LayoutSettings.ACTION + "freeme-toggle", host);
        check(!FreeMe.enabled() && FreeMe.installed(), "disable toggle removed installation");
        check(FreeMe.entries(stock, profile, 0) == stock, "disabled FreeMe changed stock");
        LayoutSettings.action(LayoutSettings.ACTION + "freeme-toggle", host);
        check(FreeMe.enabled(), "enable toggle failed");
        new File(dir, "dockin.enabled").createNewFile();
        check(DockIn.capacity() == 4 && !DockIn.select(3, 0) && !DockIn.select(8, 0), "DockIn minimum/default/range invalid");
        check(DockIn.select(7, 4) && DockIn.capacity() == 7, "DockIn preference not saved");
        check(!DockIn.select(4, 7) && DockIn.capacity() == 7, "capacity shrink discarded icons");
        new File(dir, "safe-mode.enabled").createNewFile();
        check(!FreeMe.enabled() && FreeMe.entries(stock, profile, 0) == stock && DockIn.capacity() == 4, "Safe Mode left layout tweaks active");
        check(Arrays.equals(legacyBefore, Files.readAllBytes(legacy.toPath())), "legacy positions overwritten");
        for (String name : List.of("ios4_pages.json", "ios6_pages.json", "ios7_pages.json")) check(Files.readString(new File(root, name).toPath()).equals("protected " + name), "native layout file overwritten");
        new File(dir, "safe-mode.enabled").delete();
        System.out.println("FreeMe packaged hooks: grid snapping, gaps, cross/new pages, renderer/touch/animation, collision, Safe Mode and data preservation passed; DockIn preferences passed");
    }
}
