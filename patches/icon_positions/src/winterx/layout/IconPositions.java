package winterx.layout;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.IOException;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;

/** Position data for a free-layout hook. Coordinates are fractions of the home-screen area. */
public final class IconPositions {
    private static final int MAX_ITEMS = 500;
    private final LinkedHashMap<String, Placement> entries = new LinkedHashMap<>();

    public static final class Placement {
        public final int page;
        public final String id;
        public final double x, y;
        Placement(int page, String id, double x, double y) { this.page = page; this.id = id; this.x = x; this.y = y; }
    }
    private static String key(int page, String id) { return page + "\u0000" + id; }
    private static void validate(int page, String id, double x, double y) {
        if (page < 0 || page > 100 || id == null || id.isEmpty() || id.length() > 256 || id.indexOf('\0') >= 0 ||
            !Double.isFinite(x) || !Double.isFinite(y) || x < 0 || x > 1 || y < 0 || y > 1)
            throw new IllegalArgumentException("Invalid icon position");
    }
    public synchronized void put(int page, String id, double x, double y) {
        validate(page, id, x, y);
        String key = key(page, id);
        if (!entries.containsKey(key) && entries.size() >= MAX_ITEMS) throw new IllegalStateException("Too many icon positions");
        entries.remove(key);
        entries.put(key, new Placement(page, id, x, y));
    }
    public synchronized Placement get(int page, String id) { return entries.get(key(page, id)); }
    public synchronized boolean remove(int page, String id) { return entries.remove(key(page, id)) != null; }
    public synchronized List<Placement> list() { return new ArrayList<>(entries.values()); }

    /** Last moved icon wins when icons overlap. Width and height use the same normalized units. */
    public synchronized Placement hit(int page, double x, double y, double width, double height) {
        if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(width) || !Double.isFinite(height) || width <= 0 || height <= 0)
            throw new IllegalArgumentException("Invalid hit test");
        Placement found = null;
        for (Placement p : entries.values())
            if (p.page == page && x >= p.x && x <= p.x + width && y >= p.y && y <= p.y + height) found = p;
        return found;
    }
    public synchronized void save(File file) throws Exception {
        JSONArray rows = new JSONArray();
        for (Placement p : entries.values()) rows.put(new JSONObject().put("page", p.page).put("id", p.id).put("x", p.x).put("y", p.y));
        byte[] bytes = new JSONObject().put("version", 1).put("positions", rows).toString().getBytes(StandardCharsets.UTF_8);
        File parent = file.getAbsoluteFile().getParentFile();
        if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create position folder");
        File temp = File.createTempFile(".winterx-positions-", ".tmp", parent);
        try {
            try (FileOutputStream out = new FileOutputStream(temp)) {
                out.write(bytes);
                out.getFD().sync();
            }
            try { Files.move(temp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE); }
            catch (java.nio.file.AtomicMoveNotSupportedException e) { Files.move(temp.toPath(), file.toPath(), StandardCopyOption.REPLACE_EXISTING); }
        } finally { Files.deleteIfExists(temp.toPath()); }
    }
    public static IconPositions load(File file) throws Exception {
        IconPositions result = new IconPositions();
        if (!file.exists()) return result;
        if (!file.isFile() || file.length() > 262144) throw new IOException("Invalid position file");
        JSONObject root = new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
        if (root.getInt("version") != 1) throw new IOException("Unsupported position format");
        JSONArray rows = root.getJSONArray("positions");
        if (rows.length() > MAX_ITEMS) throw new IOException("Too many icon positions");
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.getJSONObject(i);
            int page = row.getInt("page"); String id = row.getString("id");
            if (result.get(page, id) != null) throw new IOException("Duplicate icon position");
            result.put(page, id, row.getDouble("x"), row.getDouble("y"));
        }
        return result;
    }
}
