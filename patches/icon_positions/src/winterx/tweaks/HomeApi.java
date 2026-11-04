package winterx.tweaks;

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
import winterx.layout.FreeMe;
import winterx.layout.GridSlots;

/** Version-specific home API; all callers must dispatch to the UI thread and verify package revision. */
public final class HomeApi {
    public static final String ABI = "winterx-home-grid-v1";
    private HomeApi() {}
    private static File gridFile() throws Exception {
        File root = android.app.ActivityThread.currentApplication().getFilesDir();
        File path = new File(root, "ruby/freeme-slots-v1.json");
        if (Files.isSymbolicLink(path.toPath()) || !path.getCanonicalFile().equals(path.getAbsoluteFile()))
            throw new java.io.IOException("Home storage links refused");
        return path;
    }
    private static List<String> ids(List<c> page) {
        if (page == null || page.size() > 100) throw new IllegalArgumentException("Home page unavailable");
        List<String> ids = new ArrayList<>();
        for (c entry : page) ids.add(entry.a.a);
        return ids;
    }
    private static JSONArray page(List<c> entries, int page, int capacity, GridSlots grid) throws Exception {
        List<String> ids = ids(entries); JSONArray rows = new JSONArray();
        Map<String, Integer> slots = grid.resolve(page, ids, capacity);
        for (String id : ids) rows.put(new JSONObject().put("id", id).put("slot", slots.get(id)));
        return rows;
    }
    public static JSONObject snapshot(x1.i1 spring) throws Exception {
        if (TweakHost.safeMode() || spring == null || spring.e == null || spring.S1 == null || spring.S1.size() > 100)
            throw new java.io.IOException("Home unavailable or Safe Mode enabled");
        if (spring.W1 != null) throw new java.io.IOException("Finish home editing before using the home API");
        GridSlots grid = FreeMe.enabled() ? GridSlots.load(gridFile()) : new GridSlots();
        int capacity = spring.e.k.a, columns = spring.e.k.b;
        JSONArray pages = new JSONArray(); pages.put(page((List<c>)spring.L1, 0, capacity, grid));
        int count = ((List<?>)spring.L1).size();
        for (int i = 0; i < spring.S1.size(); i++) {
            List<c> entries = (List<c>)spring.S1.get(i); count += entries.size();
            if (count > 500) throw new java.io.IOException("Too many home icons");
            pages.put(page(entries, i + 1, capacity, grid));
        }
        JSONArray dock = new JSONArray(); for (String id : ids((List<c>)spring.M1)) dock.put(id);
        JSONObject value = new JSONObject().put("abi", ABI).put("columns", columns).put("capacity", capacity)
            .put("pages", pages).put("dock", dock).put("gridEnabled", FreeMe.enabled());
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        hash.update(value.toString().getBytes(StandardCharsets.UTF_8));
        File file = gridFile(); if (file.isFile()) {
            if (file.length() > 262144) throw new java.io.IOException("Home grid exceeds limit");
            byte[] raw = Files.readAllBytes(file.toPath());
            if (raw.length > 262144) throw new java.io.IOException("Home grid exceeds limit");
            hash.update(raw);
        }
        StringBuilder revision = new StringBuilder(); for (byte b : hash.digest()) revision.append(String.format(java.util.Locale.US, "%02x", b & 255));
        return value.put("revision", revision.toString());
    }
    public static JSONObject move(x1.i1 spring, JSONObject request) throws Exception {
        if (!FreeMe.enabled()) throw new java.io.IOException("Enable FreeMe before moving grid cells");
        JSONObject before = snapshot(spring);
        if (!before.getString("revision").equals(request.getString("revision"))) throw new java.io.IOException("Home changed; take a fresh snapshot");
        Object pageValue = request.get("page"), slotValue = request.get("slot");
        if (!(pageValue instanceof Number) || !(slotValue instanceof Number) ||
            ((Number)pageValue).doubleValue() != ((Number)pageValue).intValue() ||
            ((Number)slotValue).doubleValue() != ((Number)slotValue).intValue()) throw new java.io.IOException("Grid page/slot must be integers");
        int page = ((Number)pageValue).intValue(), slot = ((Number)slotValue).intValue(); String id = request.getString("id");
        if (page < 0 || page >= before.getJSONArray("pages").length() || slot < 0 || slot >= spring.e.k.a ||
            id.startsWith("folder:") || id.equals("folder-utilities")) throw new java.io.IOException("Invalid home grid move");
        List<String> ids = ids(page == 0 ? (List<c>)spring.L1 : (List<c>)spring.S1.get(page - 1));
        if (!ids.contains(id)) throw new java.io.IOException("This API moves existing icons within their current page only");
        File file = gridFile(); GridSlots grid = GridSlots.load(file);
        Map<String, Integer> slots = grid.resolve(page, ids, spring.e.k.a);
        for (Map.Entry<String, Integer> entry : slots.entrySet())
            if (!entry.getKey().equals(id) && entry.getValue() == slot) throw new java.io.IOException("Cell occupied");
        slots.put(id, slot); grid.replace(page, slots);
        if (TweakHost.safeMode() || !FreeMe.enabled() || spring.W1 != null) throw new java.io.IOException("Home grid disabled or editing started");
        grid.save(file);
        return snapshot(spring);
    }
}
