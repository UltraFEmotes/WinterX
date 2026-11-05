package winterx.layout;

import E1.c;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;
import winterx.extension.NativeRuntime;

/** FreeMe's optional grid policy behind the same public home API used by community code. */
public final class FreeMeHomeApi {
    private FreeMeHomeApi() {}
    private static File gridFile() throws Exception {
        File file = new File(NativeRuntime.files(), "ruby/freeme-slots-v1.json");
        if (Files.isSymbolicLink(file.toPath()) || !file.getCanonicalFile().equals(file.getAbsoluteFile())) throw new java.io.IOException("Home storage links refused");
        return file;
    }
    private static List<String> ids(List<c> page) {
        if (page == null || page.size() > 100) throw new IllegalArgumentException("Home page unavailable");
        List<String> result = new ArrayList<>(); for (c entry : page) result.add(entry.a.a); return result;
    }
    private static JSONArray page(List<c> entries, int page, int capacity, GridSlots grid) throws Exception {
        List<String> ids = ids(entries); Map<String, Integer> slots = grid.resolve(page, ids, capacity); JSONArray result = new JSONArray();
        for (String id : ids) result.put(new JSONObject().put("id", id).put("slot", slots.get(id))); return result;
    }
    public static JSONObject snapshot(x1.i1 spring) throws Exception {
        if (NativeRuntime.safeMode() || spring == null || spring.e == null || spring.S1 == null || spring.S1.size() > 100 || spring.W1 != null)
            throw new java.io.IOException("Home unavailable, editing or Safe Mode active");
        GridSlots grid = FreeMe.enabled() ? GridSlots.load(gridFile()) : new GridSlots(); int capacity = FreeMe.capacity(spring.e);
        JSONArray pages = new JSONArray(); pages.put(page(spring.L1, 0, capacity, grid)); int count = spring.L1.size();
        for (int i = 0; i < spring.S1.size(); i++) { List<c> entries = (List<c>)spring.S1.get(i); count += entries.size(); if (count > 500) throw new java.io.IOException("Too many home icons"); pages.put(page(entries, i + 1, capacity, grid)); }
        JSONArray dock = new JSONArray(); for (Object entry : spring.M1) dock.put(((E1.a)entry).a);
        JSONObject value = new JSONObject().put("abi", "winterx-home-grid-v1").put("columns", spring.e.k.b).put("capacity", capacity)
            .put("pages", pages).put("dock", dock).put("gridEnabled", FreeMe.enabled());
        MessageDigest hash = MessageDigest.getInstance("SHA-256"); hash.update(value.toString().getBytes(StandardCharsets.UTF_8));
        File file = gridFile(); if (file.isFile()) { if (file.length() > 262144) throw new java.io.IOException("Home grid exceeds limit"); byte[] raw = Files.readAllBytes(file.toPath()); if (raw.length > 262144) throw new java.io.IOException("Home grid exceeds limit"); hash.update(raw); }
        StringBuilder revision = new StringBuilder(); for (byte b : hash.digest()) revision.append(String.format(java.util.Locale.ROOT, "%02x", b & 255));
        return value.put("revision", revision.toString());
    }
    public static JSONObject move(x1.i1 spring, JSONObject request) throws Exception {
        if (!FreeMe.enabled()) throw new java.io.IOException("Enable FreeMe before moving grid cells");
        JSONObject before = snapshot(spring);
        if (!before.getString("revision").equals(request.getString("revision"))) throw new java.io.IOException("Home changed; take a fresh snapshot");
        Object pageValue = request.get("page"), slotValue = request.get("slot");
        if (!(pageValue instanceof Number) || !(slotValue instanceof Number) || ((Number)pageValue).doubleValue() != ((Number)pageValue).intValue() || ((Number)slotValue).doubleValue() != ((Number)slotValue).intValue()) throw new java.io.IOException("Grid page/slot must be integers");
        int page = ((Number)pageValue).intValue(), slot = ((Number)slotValue).intValue(), capacity = before.getInt("capacity"); String id = request.getString("id");
        if (page < 0 || page >= before.getJSONArray("pages").length() || slot < 0 || slot >= capacity || id.startsWith("folder:") || id.equals("folder-utilities")) throw new java.io.IOException("Invalid home grid move");
        List<String> ids = ids(page == 0 ? spring.L1 : (List<c>)spring.S1.get(page - 1)); if (!ids.contains(id)) throw new java.io.IOException("Only same-page moves of existing icons are supported");
        File file = gridFile(); GridSlots grid = GridSlots.load(file); Map<String, Integer> slots = grid.resolve(page, ids, capacity);
        for (Map.Entry<String, Integer> entry : slots.entrySet()) if (!entry.getKey().equals(id) && entry.getValue() == slot) throw new java.io.IOException("Cell occupied");
        slots.put(id, slot); grid.replace(page, slots);
        if (NativeRuntime.safeMode() || !FreeMe.enabled() || spring.W1 != null) throw new java.io.IOException("Grid disabled or editing began");
        grid.save(file); return snapshot(spring);
    }
}
