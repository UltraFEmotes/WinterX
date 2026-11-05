package winterx.snowy;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.json.JSONObject;

/** Explicit native Settings import from the private inbox, never overwrites a revision or selects it. */
public final class PackImport {
    public static final String ABI = "snowyhome-import-v1";
    private PackImport() {}
    private static boolean name(String name) {
        if (!name.matches("icons/[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\\.png")) return false;
        String stem = name.substring(6).split("\\.")[0].toUpperCase(Locale.US);
        return !stem.matches("CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]");
    }
    private static File safe(File file) throws Exception {
        if (Files.isSymbolicLink(file.toPath()) || !file.getCanonicalFile().equals(file.getAbsoluteFile()))
            throw new java.io.IOException("Pack links refused");
        return file;
    }
    static Map<String, String> inbox() {
        Map<String, String> result = new LinkedHashMap<>(); File dir = SnowyHome.folder();
        if (dir == null) return result;
        try (java.nio.file.DirectoryStream<java.nio.file.Path> stream = Files.newDirectoryStream(safe(new File(dir, "inbox")).toPath())) {
            int count = 0;
            for (java.nio.file.Path path : stream) {
                if (++count > 32) break;
                String name = path.getFileName().toString();
                if (!name.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\\.zip")) continue;
                File file = safe(path.toFile());
                if (file.isFile() && file.length() <= 16 * 1024 * 1024) result.put(IconPack.sha(name.getBytes(StandardCharsets.UTF_8)), name);
            }
        } catch (Exception ignored) {}
        return result;
    }
    public static synchronized String install(String token) throws Exception {
        if (!SnowyHome.enabled() || token == null || !token.matches("[0-9a-f]{64}")) throw new java.io.IOException("Import unavailable");
        String filename = inbox().get(token); if (filename == null) throw new java.io.IOException("Pack not in inbox");
        File dir = SnowyHome.folder(), source = safe(new File(dir, "inbox/" + filename));
        byte[] archive = IconPack.read(source, 16 * 1024 * 1024);
        Map<String, byte[]> entries = new HashMap<>(); Set<String> names = new HashSet<>(); int total = 0;
        try (ZipInputStream zip = new ZipInputStream(new java.io.ByteArrayInputStream(archive))) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                String name = entry.getName();
                if (entries.size() >= 129 || entry.isDirectory() || !names.add(name.toLowerCase(Locale.US)) ||
                    (!name.equals("manifest.json") && !name(name)) || (entry.getMethod() != 0 && entry.getMethod() != 8))
                    throw new java.io.IOException("Invalid/duplicate pack entry");
                int limit = name.equals("manifest.json") ? 65536 : 1024 * 1024;
                ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] block = new byte[8192]; int n;
                while ((n = zip.read(block)) != -1) {
                    total += n;
                    if (bytes.size() + n > limit || total > 32 * 1024 * 1024) throw new java.io.IOException("Pack byte limit exceeded");
                    bytes.write(block, 0, n);
                }
                entries.put(name, bytes.toByteArray()); zip.closeEntry();
            }
        }
        byte[] raw = entries.get("manifest.json"); if (raw == null) throw new java.io.IOException("Missing manifest");
        JSONObject manifest = new JSONObject(new String(raw, StandardCharsets.UTF_8));
        // IconPack.load supplies the canonical manifest/schema validation before publication.
        JSONObject icons = manifest.getJSONObject("icons"); Set<String> wanted = new HashSet<>(); wanted.add("manifest.json");
        if (icons.length() < 1 || icons.length() > 128) throw new java.io.IOException("Invalid icon count");
        for (Iterator<String> keys = icons.keys(); keys.hasNext();) {
            String app = keys.next(); JSONObject item = icons.getJSONObject(app); String name = item.getString("file");
            byte[] png = entries.get(name);
            if (!IconPack.app(app) || !name(name) || png == null || !IconPack.png(png) || !IconPack.sha(png).equals(item.getString("sha256")))
                throw new java.io.IOException("Invalid icon/checksum");
            wanted.add(name);
        }
        if (!wanted.equals(entries.keySet())) throw new java.io.IOException("Unreferenced pack files");
        String revision = IconPack.sha(archive); File packs = safe(new File(dir, "packs"));
        if (!packs.isDirectory() && !packs.mkdirs()) throw new java.io.IOException("Cannot create packs folder");
        File target = safe(new File(packs, revision));
        if (target.exists()) {
            IconPack existing = IconPack.load(packs, revision);
            if (existing == null) throw new java.io.IOException("Existing revision invalid; not overwritten");
            for (Iterator<String> keys = icons.keys(); keys.hasNext();) if (existing.icon(keys.next()) == null)
                throw new java.io.IOException("Existing icon invalid; not overwritten");
            return revision;
        }
        File stage = Files.createTempDirectory(packs.toPath(), ".import-").toFile();
        try {
            new File(stage, "icons").mkdir();
            entries.put("manifest.sha256", IconPack.sha(raw).getBytes(StandardCharsets.UTF_8));
            for (Map.Entry<String, byte[]> entry : entries.entrySet()) {
                try (FileOutputStream out = new FileOutputStream(new File(stage, entry.getKey()))) { out.write(entry.getValue()); out.getFD().sync(); }
            }
            // Validate using a temporary hash-named revision inside a private staging parent.
            File validation = new File(stage, revision); validation.mkdir();
            for (String name : new String[]{"manifest.json", "manifest.sha256", "icons"}) Files.move(new File(stage, name).toPath(), new File(validation, name).toPath());
            if (IconPack.load(stage, revision) == null) throw new java.io.IOException("Invalid pack manifest");
            if (!SnowyHome.enabled()) throw new java.io.IOException("SnowyHome disabled during import");
            // No REPLACE_EXISTING, including an empty/invalid revision created during validation.
            if (target.exists()) throw new java.io.IOException("Revision appeared during import; not overwritten");
            Files.move(validation.toPath(), target.toPath());
            return revision;
        } finally {
            // Only this newly allocated staging tree, never existing packs or inbox data.
            try (java.util.stream.Stream<java.nio.file.Path> paths = Files.walk(stage.toPath())) {
                paths.sorted(java.util.Comparator.reverseOrder()).forEach(path -> { try { Files.deleteIfExists(path); } catch (Exception ignored) {} });
            }
        }
    }
}
