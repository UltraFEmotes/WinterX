package winterx.layout;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** FreeMe's sparse grid, separate from Spring's compact lists and the old pixel-position test. */
public final class GridSlots {
    private final Map<Integer, LinkedHashMap<String, Integer>> pages = new LinkedHashMap<>();

    private static void validate(int page, String id, int slot) {
        if (page < 0 || page > 100 || id == null || id.isEmpty() || id.length() > 256 ||
            id.indexOf('\0') >= 0 || slot < 0 || slot >= 100)
            throw new IllegalArgumentException("Invalid grid slot");
    }
    public void put(int page, String id, int slot) {
        validate(page, id, slot);
        LinkedHashMap<String, Integer> entries = pages.get(page);
        if (entries == null) { entries = new LinkedHashMap<>(); pages.put(page, entries); }
        for (Map.Entry<String, Integer> entry : entries.entrySet())
            if (!entry.getKey().equals(id) && entry.getValue() == slot)
                throw new IllegalArgumentException("Occupied grid slot");
        entries.put(id, slot);
    }
    public Integer get(int page, String id) {
        Map<String, Integer> entries = pages.get(page);
        return entries == null ? null : entries.get(id);
    }
    /** Resolve only live icons. Stale IDs do not reserve slots; new apps cannot overlap saved icons. */
    public LinkedHashMap<String, Integer> resolve(int page, List<String> ids, int capacity) {
        if (page < 0 || page > 100 || capacity < 1 || capacity > 100 || ids.size() > capacity)
            throw new IllegalArgumentException("Invalid page capacity");
        Set<String> live = new HashSet<>();
        for (String id : ids) {
            validate(page, id, 0);
            if (!live.add(id)) throw new IllegalArgumentException("Duplicate live icon");
        }
        LinkedHashMap<String, Integer> result = new LinkedHashMap<>();
        boolean[] used = new boolean[capacity];
        for (String id : ids) {
            Integer slot = get(page, id);
            if (slot != null && slot < capacity && !used[slot]) {
                result.put(id, slot); used[slot] = true;
            }
        }
        for (int i = 0; i < ids.size(); i++) {
            String id = ids.get(i);
            if (result.containsKey(id)) continue;
            int slot = i;
            if (used[slot]) { slot = 0; while (used[slot]) slot++; }
            result.put(id, slot); used[slot] = true;
        }
        return result;
    }
    public void replace(int page, Map<String, Integer> entries) {
        GridSlots validated = new GridSlots();
        for (Map.Entry<String, Integer> entry : entries.entrySet()) validated.put(page, entry.getKey(), entry.getValue());
        pages.remove(page);
        if (!entries.isEmpty()) pages.put(page, new LinkedHashMap<>(entries));
    }
    public static GridSlots load(File file) throws Exception {
        GridSlots result = new GridSlots();
        if (!file.exists()) return result;
        if (!file.isFile() || Files.isSymbolicLink(file.toPath()) || file.length() > 262144)
            throw new IOException("Invalid FreeMe grid file");
        JSONObject root = new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
        if (root.getInt("version") != 1) throw new IOException("Unsupported FreeMe grid format");
        JSONArray rows = root.getJSONArray("slots");
        if (rows.length() > 500) throw new IOException("Too many FreeMe grid entries");
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.getJSONObject(i);
            int page = row.getInt("page"); String id = row.getString("id");
            if (result.get(page, id) != null) throw new IOException("Duplicate FreeMe icon");
            result.put(page, id, row.getInt("slot"));
        }
        return result;
    }
    public void save(File file) throws Exception {
        JSONArray rows = new JSONArray();
        for (Map.Entry<Integer, LinkedHashMap<String, Integer>> page : pages.entrySet())
            for (Map.Entry<String, Integer> entry : page.getValue().entrySet())
                rows.put(new JSONObject().put("page", page.getKey()).put("id", entry.getKey()).put("slot", entry.getValue()));
        if (rows.length() > 500) throw new IOException("Too many FreeMe grid entries");
        File parent = file.getAbsoluteFile().getParentFile();
        if (Files.isSymbolicLink(parent.toPath()) || Files.isSymbolicLink(file.toPath()))
            throw new IOException("FreeMe storage must not contain links");
        if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create FreeMe folder");
        File temp = File.createTempFile(".freeme-", ".tmp", parent);
        try {
            try (FileOutputStream out = new FileOutputStream(temp)) {
                out.write(new JSONObject().put("version", 1).put("slots", rows).toString().getBytes(StandardCharsets.UTF_8));
                out.getFD().sync();
            }
            try { Files.move(temp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE); }
            catch (java.nio.file.AtomicMoveNotSupportedException ex) { Files.move(temp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING); }
        } finally { Files.deleteIfExists(temp.toPath()); }
    }
}
