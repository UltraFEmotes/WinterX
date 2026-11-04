package winterx.snowy;

import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import org.json.JSONObject;

/** Immutable, per-image checksum-verified icon-pack revision. No code or arbitrary file paths. */
public final class IconPack {
    public final String revision, name;
    private final File root;
    private final Map<String, JSONObject> icons;
    private IconPack(File root, String revision, String name, Map<String, JSONObject> icons) {
        this.root = root; this.revision = revision; this.name = name; this.icons = Collections.unmodifiableMap(icons);
    }
    static byte[] read(File file, int limit) throws Exception {
        if (Files.isSymbolicLink(file.toPath()) || !file.isFile() || file.length() > limit) throw new java.io.IOException("Invalid bounded pack file");
        try (FileInputStream in = new FileInputStream(file); java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream()) {
            byte[] buffer = new byte[8192]; int n;
            while ((n = in.read(buffer)) != -1) { if (out.size() + n > limit) throw new java.io.IOException("Pack file exceeds limit"); out.write(buffer, 0, n); }
            return out.toByteArray();
        }
    }
    static String sha(byte[] value) throws Exception {
        StringBuilder hex = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(value)) hex.append(String.format(java.util.Locale.US, "%02x", b & 255));
        return hex.toString();
    }
    static boolean app(String id) { return id != null && id.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,159}") && !id.startsWith("folder:") && !id.equals("folder-utilities"); }
    static boolean text(JSONObject value, String key) throws Exception {
        Object raw = value.get(key);
        if (!(raw instanceof String)) return false;
        String text = (String)raw;
        return !text.trim().isEmpty() && text.length() <= 80 && !text.matches("(?s).*[\\x00-\\x1f].*");
    }
    static boolean png(byte[] raw) {
        try {
            java.nio.ByteBuffer bytes = java.nio.ByteBuffer.wrap(raw);
            if (raw.length < 45 || bytes.getLong() != 0x89504e470d0a1a0aL) return false;
            boolean header = false, pixels = false;
            for (int count = 0; count < 4096 && bytes.remaining() >= 12; count++) {
                int length = bytes.getInt(), type = bytes.getInt(), at = bytes.position();
                if (length < 0 || length > bytes.remaining() - 4 || type == 0x6163544c) return false; // no APNG
                if (!header) {
                    if (type != 0x49484452 || length != 13) return false;
                    int width = bytes.getInt(at), height = bytes.getInt(at + 4);
                    if (width != height || width < 16 || width > 1024) return false;
                    header = true;
                } else if (type == 0x49484452) return false;
                java.util.zip.CRC32 crc = new java.util.zip.CRC32(); crc.update(raw, at - 4, length + 4);
                bytes.position(at + length);
                if ((int)crc.getValue() != bytes.getInt()) return false;
                if (type == 0x49444154) pixels = true;
                if (type == 0x49454e44) return length == 0 && pixels && bytes.remaining() == 0;
            }
        } catch (RuntimeException failure) { return false; }
        return false;
    }
    public static IconPack load(File packs, String revision) {
        try {
            if (packs == null || revision == null || !revision.matches("[0-9a-f]{64}") || Files.isSymbolicLink(packs.toPath()) || !packs.isDirectory()) return null;
            File root = new File(packs, revision), images = new File(root, "icons");
            if (Files.isSymbolicLink(root.toPath()) || Files.isSymbolicLink(images.toPath()) || !root.isDirectory() || !images.isDirectory()) return null;
            if (!root.getCanonicalFile().equals(root.getAbsoluteFile())) return null;
            byte[] raw = read(new File(root, "manifest.json"), 65536);
            String pinned = new String(read(new File(root, "manifest.sha256"), 64), StandardCharsets.UTF_8);
            if (!pinned.matches("[0-9a-f]{64}") || !sha(raw).equals(pinned)) return null;
            JSONObject value = new JSONObject(new String(raw, StandardCharsets.UTF_8));
            if (!"winterx.iconpack/1".equals(value.optString("format")) || value.length() != 6 ||
                !text(value, "id") || !text(value, "name") || !text(value, "author") || !text(value, "version") ||
                !value.getString("id").matches("[a-z0-9]+(?:[.-][a-z0-9]+)+") ||
                !value.getString("version").matches("[0-9]+(?:\\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?")) return null;
            String name = value.getString("name");
            if (name.trim().isEmpty() || name.length() > 80 || name.matches("(?s).*[\\x00-\\x1f].*")) return null;
            JSONObject source = value.getJSONObject("icons");
            if (source.length() < 1 || source.length() > 128) return null;
            Map<String, JSONObject> icons = new HashMap<>(); Iterator<String> keys = source.keys();
            while (keys.hasNext()) {
                String id = keys.next(); JSONObject icon = source.getJSONObject(id);
                if (!app(id) || icon.length() != 2 || !icon.getString("file").matches("icons/[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\\.png") ||
                    !icon.getString("sha256").matches("[0-9a-f]{64}")) return null;
                icons.put(id, icon);
            }
            return new IconPack(root, revision, name, icons);
        } catch (Exception failure) { return null; }
    }
    public byte[] icon(String id) {
        try {
            JSONObject icon = icons.get(id); if (icon == null) return null;
            File images = new File(root, "icons"), file = new File(root, icon.getString("file"));
            if (Files.isSymbolicLink(root.toPath()) || Files.isSymbolicLink(images.toPath()) || !file.getCanonicalFile().equals(file.getAbsoluteFile())) return null;
            byte[] raw = read(file, 1024 * 1024);
            return sha(raw).equals(icon.getString("sha256")) && png(raw) ? raw : null;
        } catch (Exception failure) { return null; }
    }
}
