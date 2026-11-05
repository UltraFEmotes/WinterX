package winterx.tweaks;

import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONObject;
import sun.misc.Unsafe;
import winterx.layout.GridSlots;

public final class HomeApiCheck {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static Unsafe unsafe() throws Exception { Field f = Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object object, String name, Object value) throws Exception { Field f = object.getClass().getDeclaredField(name); f.setAccessible(true); f.set(object, value); }
    static E1.a app(String id) throws Exception { E1.a app = (E1.a)unsafe().allocateInstance(E1.a.class); set(app, "a", id); return app; }
    static void refuses(x1.i1 host, JSONObject request, String why) throws Exception {
        try { HomeApi.move(host, request); throw new AssertionError(why); } catch (java.io.IOException expected) {}
    }
    public static void main(String[] args) throws Exception {
        File root = new File(System.getProperty("ruby.test.dir")), ruby = new File(root, "ruby"); ruby.mkdirs();
        File pages = new File(root, "ios6_pages.json"); Files.write(pages.toPath(), "keep native pages".getBytes());
        E1.i6 profile = (E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile, "k", new E1.k0(4, 4, 34, 27, 38, 62, 0, 0, new ArrayList<>()));
        x1.i1 host = (x1.i1)unsafe().allocateInstance(x1.i1.class); set(host, "e", profile);
        List<E1.c> first = new ArrayList<>();
        for (String id : List.of("mail", "phone", "photos", "settings", "spring", "ruby"))
            first.add(new E1.c(app(id), first.size() / 4, first.size() % 4));
        set(host, "L1", first); set(host, "S1", new ArrayList<>()); set(host, "M1", new ArrayList<>(List.of(new E1.c(app("dock"), 0, 0))));
        JSONObject plain = HomeApi.snapshot(host); check(!plain.getBoolean("gridEnabled"), "snapshot enabled FreeMe");
        check(plain.getInt("capacity") == 16 && plain.getInt("columns") == 4, "grid rows treated as total cell capacity");
        E1.k0 normal = profile.k;
        set(profile, "k", new E1.k0(5, 4, 34, 27, 38, 62, 0, 0, new ArrayList<>()));
        check(HomeApi.snapshot(host).getInt("capacity") == 20, "five-row grid did not expose twenty cells");
        for (int[] dimensions : new int[][]{{0, 4}, {4, 0}, {-1, 4}, {26, 4}, {Integer.MAX_VALUE, 4}}) {
            set(profile, "k", new E1.k0(dimensions[0], dimensions[1], 34, 27, 38, 62, 0, 0, new ArrayList<>()));
            try { HomeApi.snapshot(host); throw new AssertionError("invalid/overflowing grid accepted"); }
            catch (IllegalArgumentException expected) {}
        }
        set(profile, "k", normal);
        JSONObject move = new JSONObject().put("id", "mail").put("page", 0).put("slot", 11).put("revision", plain.getString("revision"));
        refuses(host, move, "uninstalled FreeMe moved icon"); new File(ruby, "freeme.enabled").createNewFile();
        move.put("revision", HomeApi.snapshot(host).getString("revision"));
        JSONObject after = HomeApi.move(host, move);
        check(after.getJSONArray("pages").getJSONArray(0).getJSONObject(0).getInt("slot") == 11, "API did not move cell");
        check(first.get(0).b == 0 && first.get(0).c == 0, "native entry mutated");
        check(after.getJSONArray("dock").getString(0).equals("dock"), "dock changed");
        File grid = new File(ruby, "freeme-slots-v1.json"); byte[] saved = Files.readAllBytes(grid.toPath());
        refuses(host, move, "stale revision accepted"); move.put("revision", after.getString("revision"));
        refuses(host, new JSONObject(move.toString()).put("slot", 1), "occupied cell accepted");
        refuses(host, new JSONObject(move.toString()).put("slot", 1.5), "fractional cell accepted");
        refuses(host, new JSONObject(move.toString()).put("page", 1), "cross-page move silently accepted");
        refuses(host, new JSONObject(move.toString()).put("id", "folder:1"), "folder mutation accepted");
        set(host, "W1", unsafe().allocateInstance(E1.O1.class)); refuses(host, move, "active home editing accepted"); set(host, "W1", null);
        new File(ruby, "safe-mode.enabled").createNewFile(); refuses(host, move, "Safe Mode moved icon");
        check(java.util.Arrays.equals(saved, Files.readAllBytes(grid.toPath())), "failed move changed saved cells");
        check(new String(Files.readAllBytes(pages.toPath())).equals("keep native pages"), "native page data changed");
        new File(ruby, "safe-mode.enabled").delete();
        File preserved = new File(ruby, "preserved-grid"); Files.move(grid.toPath(), preserved.toPath());
        Files.createSymbolicLink(grid.toPath(), preserved.toPath());
        try { HomeApi.snapshot(host); throw new AssertionError("linked grid accepted"); } catch (java.io.IOException expected) {}
        check(java.util.Arrays.equals(saved, Files.readAllBytes(preserved.toPath())), "linked grid changed saved cells");
        Files.delete(grid.toPath()); Files.move(preserved.toPath(), grid.toPath());
        File savedRuby = new File(root, "saved-ruby"); Files.move(ruby.toPath(), savedRuby.toPath());
        Files.createSymbolicLink(ruby.toPath(), savedRuby.toPath());
        try { HomeApi.snapshot(host); throw new AssertionError("linked ruby directory accepted"); } catch (java.io.IOException expected) {}
        check(java.util.Arrays.equals(saved, Files.readAllBytes(new File(savedRuby, "freeme-slots-v1.json").toPath())), "linked ruby changed saved cells");
        System.out.println("Home API: real rows × columns, native snapshot/grid move, revision/collision/integer/edit/Safe Mode guards and child-link/data preservation passed at " + root.getName());
    }
}
