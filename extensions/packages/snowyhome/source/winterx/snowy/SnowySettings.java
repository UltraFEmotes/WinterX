package winterx.snowy;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.json.JSONObject;

/** Spring's actual Settings rows; uses existing layout navigation/action dispatch and live redraw. */
public final class SnowySettings {
    private static final String PAGE = "winterx-layout-p/snowy/", ACTION = "winterx-layout-a/snowy/";
    private static final String[][] COLORS = {{"Stock", "stock"}, {"Red", "#FF3B30"}, {"Blue", "#007AFF"},
        {"Green", "#34C759"}, {"Purple", "#AF52DE"}, {"Orange", "#FF9500"}, {"Graphite", "#2C2C2E"}};
    private static final String[] CORNERS = {"Stock", "Square", "Subtle", "Rounded", "Soft", "Circle"};
    private static final double[] RADII = {-1, 0, .10, .18, .30, .50};
    static volatile String importStatus = "Choose a pack ZIP, or copy ZIPs into ruby/snowyhome/inbox and pick one here. Imports do not select or delete packs.";
    private static final java.util.concurrent.atomic.AtomicBoolean importing = new java.util.concurrent.atomic.AtomicBoolean();
    private SnowySettings() {}
    private static V6 row(String id, String title) { return Z3.g(Z3.a, id, title, null, null, null, 0x18); }
    public static void rows(List<V6> rows) { if (SnowyHome.enabled()) rows.add(row(PAGE + "main", "SnowyHome")); }
    private static Map<String, IconPack> packs() {
        Map<String, IconPack> values = new TreeMap<>(); File dir = SnowyHome.folder(); if (dir == null) return values;
        File folder = new File(dir, "packs"); if (Files.isSymbolicLink(folder.toPath())) return values;
        // DirectoryStream avoids materializing an unbounded array of filenames.
        try (java.nio.file.DirectoryStream<java.nio.file.Path> stream = Files.newDirectoryStream(folder.toPath())) {
            int count = 0;
            for (java.nio.file.Path path : stream) {
                if (++count > 32) break;
                IconPack pack = IconPack.load(folder, path.getFileName().toString());
                if (pack != null) values.put(pack.revision, pack);
            }
        } catch (Exception ignored) {}
        return values;
    }
    public static T6 page(String id) {
        if (!SnowyHome.enabled() || id == null || !id.startsWith(PAGE)) return null;
        JSONObject preferences = SnowyHome.preferences(); List<V6> rows = new ArrayList<>(); String title, footer;
        if (id.equals(PAGE + "main")) {
            rows.add(row(PAGE + "packs", "Icon Pack")); rows.add(row(PAGE + "badges", "Badge Colour"));
            rows.add(row(PAGE + "corners", "Icon Corners"));
            rows.add(row(ACTION + "labels", (preferences.optBoolean("hideLabels") ? "✓ " : "") + "Hide Icon Labels"));
            title = "SnowyHome"; footer = "Appearance only. Original icons, names, geometry and saved layouts are preserved. Disabled in Safe Mode.";
        } else if (id.equals(PAGE + "packs")) {
            String selected = preferences.optString("pack", "stock");
            rows.add(row(ACTION + "pack/stock", (selected.equals("stock") ? "✓ " : "") + "Stock Icons"));
            rows.add(row(PAGE + "import", "Import Icon Pack"));
            for (IconPack pack : packs().values()) rows.add(row(ACTION + "pack/" + pack.revision, (selected.equals(pack.revision) ? "✓ " : "") + pack.name));
            title = "Icon Pack"; footer = "Import a ZIP from the private inbox, then select its verified revision. Missing or invalid icons fall back to Spring originals. Shows up to 32 revisions.";
        } else if (id.equals(PAGE + "import")) {
            rows.add(row(ACTION + "pick", "Choose a ZIP…"));
            for (Map.Entry<String, String> pack : PackImport.inbox().entrySet()) rows.add(row(ACTION + "import/" + pack.getKey(), pack.getValue()));
            title = "Import Icon Pack"; footer = importStatus;
        } else if (id.equals(PAGE + "badges")) {
            for (int i = 0; i < COLORS.length; i++) rows.add(row(ACTION + "badge/" + i,
                (COLORS[i][1].equalsIgnoreCase(preferences.optString("badge", "stock")) ? "✓ " : "") + COLORS[i][0]));
            title = "Badge Colour"; footer = "Recolours the red badge artwork only; white glyphs, highlights, size and alpha remain stock.";
        } else if (id.equals(PAGE + "corners")) {
            for (int i = 0; i < CORNERS.length; i++) rows.add(row(ACTION + "corners/" + i,
                (preferences.optDouble("corners", -1) == RADII[i] ? "✓ " : "") + CORNERS[i]));
            title = "Icon Corners"; footer = "Clips a private bitmap copy, not the shared icon cache. Transparent corners in original art cannot be restored by a square mask.";
        } else return null;
        return new T6(id, title, Collections.singletonList(new W6(title.toUpperCase(java.util.Locale.US), null, footer, null, rows)));
    }
    public static boolean action(String id) {
        if (!SnowyHome.enabled() || id == null || !id.startsWith(ACTION)) return false;
        String suffix = id.substring(ACTION.length());
        if (suffix.matches("import/[0-9a-f]{64}")) {
            if (!importing.compareAndSet(false, true)) return false;
            final String token = suffix.substring(7); importStatus = "Validating and importing…";
            Thread worker = new Thread(() -> {
                try { String revision = PackImport.install(token); importStatus = "Imported " + revision.substring(0, 12) + ". Return to Icon Pack to select it."; }
                catch (Exception failure) { importStatus = "Not imported: " + failure.getMessage(); }
                finally { importing.set(false); }
            }, "WinterX-pack-import"); worker.setDaemon(true); worker.start(); return true;
        }
        if (suffix.equals("pick")) { PackPicker.open(); return true; }
        if (suffix.equals("labels")) return SnowyHome.select("hideLabels", !SnowyHome.preferences().optBoolean("hideLabels"));
        if (suffix.matches("badge/[0-6]")) return SnowyHome.select("badge", COLORS[suffix.charAt(suffix.length() - 1) - '0'][1]);
        if (suffix.matches("corners/[0-5]")) return SnowyHome.select("corners", RADII[suffix.charAt(suffix.length() - 1) - '0']);
        if (suffix.equals("pack/stock")) return SnowyHome.select("pack", "stock");
        if (suffix.matches("pack/[0-9a-f]{64}")) {
            String revision = suffix.substring(5); File dir = SnowyHome.folder();
            if (dir != null && IconPack.load(new File(dir, "packs"), revision) != null) return SnowyHome.select("pack", revision);
        }
        return false;
    }
}
