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
        set(profile, "k", new E1.k0(16, 4, 34, 27, 38, 62, 0, 0, new ArrayList<>()));
        x1.i1 host = (x1.i1)unsafe().allocateInstance(x1.i1.class); set(host, "e", profile);
        List<E1.c> first = new ArrayList<>(); first.add(new E1.c(app("mail"), 0, 0)); first.add(new E1.c(app("phone"), 0, 1));
        set(host, "L1", first); set(host, "S1", new ArrayList<>()); set(host, "M1", new ArrayList<>(List.of(new E1.c(app("dock"), 0, 0))));
        JSONObject plain = HomeApi.snapshot(host); check(!plain.getBoolean("gridEnabled"), "snapshot enabled FreeMe");
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
        System.out.println("Home API: native snapshot, grid move, revision conflict, collision/integer/edit/Safe Mode guards and native data preservation passed");
    }
}
