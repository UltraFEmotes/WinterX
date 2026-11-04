package winterx.tweaks;

import android.util.Log;
import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Settings integration for .springys/2 tweaks.
 *
 * Root page: one WINTERX TWEAKS section listing installed, enabled tweaks.
 * Tweak pages and rows are declared in the package manifest and rendered with
 * Spring's own Settings factories, so they look native. Row ids:
 *   winterx-tw-p/<id>                  open a tweak's main page
 *   winterx-tw-p/<id>/<page>           open a tweak's secondary page
 *   winterx-tw-r/<id>/<page>/<row>     action or toggle
 */
public final class TweakSettings {
    public static final String PAGE_PREFIX = "winterx-tw-p/";
    public static final String ROW_PREFIX = "winterx-tw-r/";
    private static final int LIMIT = 40;

    private TweakSettings() {}

    /** Append the tweaks section to a root Settings model. */
    public static T6 decorate(T6 page) {
        if (page == null || !"root".equals(page.a)) return page;
        if (TweakHost.safeMode()) return page;
        File root = TweakHost.root();
        try {
            List<W6> sections = new ArrayList<>();
            for (Object sectionObject : page.c) sections.add((W6) sectionObject);
            List<V6> rows = new ArrayList<>();
            File[] tweaks = root == null ? null : root.listFiles();
            if (tweaks != null) {
                Arrays.sort(tweaks);
                for (File dir : tweaks) {
                    if (rows.size() >= LIMIT) break;
                    if (dir == null || !dir.isDirectory()) continue;
                    String id = dir.getName();
                    JSONObject manifest = TweakHost.manifestOf(id);
                    if (manifest == null) continue;
                    if (manifest.optJSONObject("settings") == null) continue;
                    rows.add(row(PAGE_PREFIX + id, sanitize(manifest.optString("name", id))));
                }
            }
            if (winterx.coloredbar.ColoredBar.enabled()) rows.add(row("winterx-cb-picker", "ColoredBar"));
            winterx.layout.LayoutSettings.rows(rows);
            if (rows.isEmpty()) return page;
            for (Object section : page.c) for (Object entry : ((W6) section).c) {
                String id = ((V6) entry).a;
                if (id.startsWith(PAGE_PREFIX) || "winterx-cb-picker".equals(id) || id.startsWith(winterx.layout.LayoutSettings.PAGE)) return page;
            }
            sections.add(new W6("WINTERX TWEAKS", null, null, null, rows));
            return new T6(page.a, page.b, sections);
        } catch (RuntimeException failure) {
            Log.w("WinterX", "tweak settings decorate failed", failure);
            return page;
        }
    }

    /** Serve a tweak Settings page, or null for Spring stock pages. */
    public static T6 page(String pageId) {
        if (pageId == null || !pageId.startsWith(PAGE_PREFIX)) return null;
        if (TweakHost.safeMode()) return null;
        String[] parts = pageId.substring(PAGE_PREFIX.length()).split("/", -1);
        if (parts.length != 1 && parts.length != 2) return null;
        if (!TweakHost.validId(parts[0])) return null;
        if (parts.length == 2 && !parts[1].matches("[a-z0-9-]{1,40}")) return null;
        JSONObject manifest = TweakHost.manifestOf(parts[0]);
        if (manifest == null) return null;
        JSONObject settings = manifest.optJSONObject("settings");
        if (settings == null) return null;
        try {
            JSONObject asked = parts.length == 1 || "main".equals(parts[1]) ? settings.optJSONObject("main")
                    : settings.optJSONObject("pages") == null ? null
                      : settings.optJSONObject("pages").optJSONObject(parts[1]);
            if (asked == null) return null;
            String title = parts.length == 1 ? manifest.optString("name", parts[0]) : asked.optString("title", parts[1]);
            JSONArray sectionsSpec = asked.optJSONArray("sections");
            int wanted = sectionsSpec == null ? 0 : Math.min(sectionsSpec.length(), LIMIT);
            List<W6> sections = new ArrayList<>();
            for (int index = 0; index < wanted; index++) {
                JSONObject section = sectionsSpec.optJSONObject(index);
                if (section == null) continue;
                JSONArray rowsSpec = section.optJSONArray("rows");
                int rowCount = rowsSpec == null ? 0 : Math.min(rowsSpec.length(), LIMIT);
                List<V6> rows = new ArrayList<>();
                for (int rowIndex = 0; rowIndex < rowCount; rowIndex++) {
                    addRow(rows, parts[0], parts.length == 1 ? "main" : parts[1], rowsSpec.optJSONObject(rowIndex));
                }
                if (rows.isEmpty()) continue;
                String header = sanitize(section.optString("title", ""));
                sections.add(new W6(header.isEmpty() ? null : header, null, null, null, rows));
            }
            if (sections.isEmpty()) return null;
            return new T6(pageId, sanitize(title), sections);
        } catch (RuntimeException failure) {
            Log.w("WinterX", "tweak page failed", failure);
            return null;
        }
    }

    private static String sanitize(String value) {
        if (value == null) return "";
        String clean = value.replaceAll("[\\r\\n\\t]", " ").trim();
        return clean.length() > 60 ? clean.substring(0, 60) : clean;
    }

    private static V6 row(String id, String title) {
        return Z3.g(Z3.a, id, sanitize(title), null, null, null, 0x18);
    }

    private static void addRow(List<V6> rows, String tweak, String pageId, JSONObject spec) {
        if (spec == null) return;
        String type = spec.optString("type", "button");
        if (!"button".equals(type) && !"toggle".equals(type) && !"page".equals(type)) return;
        String rowId = spec.optString("id", "");
        if (!rowId.matches("[a-z0-9-]{1,40}")) return;
        String title = sanitize(spec.optString("title", ""));
        if (title.isEmpty()) return;
        if ("page".equals(type)) {
            String target = spec.optString("page", "");
            if (target.isEmpty() || !target.matches("[a-z0-9-]{1,40}")) return;
            if ("main".equals(target) && "main".equals(pageId)) return;
            rows.add(row(PAGE_PREFIX + tweak + "/" + target, title));
            return;
        }
        boolean toggleState = "toggle".equals(type)
                && TweakHost.setting(tweak, pageId + "/" + rowId, "off");
        String shown = "toggle".equals(type)
                ? (toggleState ? "✓ " + title : title)
                : title;
        rows.add(row(ROW_PREFIX + tweak + "/" + pageId + "/" + rowId, shown));
    }

    /** Handle one tapped action/toggle row (smali routes winterx-tw-r/ here). */
    public static void action(String rowId) {
        if (rowId == null || !rowId.startsWith(ROW_PREFIX)) return;
        if (TweakHost.safeMode()) return;
        String[] parts = rowId.substring(ROW_PREFIX.length()).split("/", -1);
        if (parts.length != 3 || !TweakHost.validId(parts[0])) return;
        if (!parts[1].matches("[a-z0-9-]{1,40}")) return;
        String row = parts[2];
        if (!row.matches("[a-z0-9-]{1,40}")) return;
        JSONObject manifest = TweakHost.manifestOf(parts[0]);
        if (manifest == null) return;
        try {
            JSONObject settings = manifest.optJSONObject("settings");
            JSONObject pages = settings == null ? null : settings.optJSONObject("pages");
            JSONObject main = settings == null ? null : settings.optJSONObject("main");
            JSONObject asked = "main".equals(parts[1]) ? main
                    : pages == null ? null : pages.optJSONObject(parts[1]);
            JSONObject found = findRow(asked, row);
            if (found == null) return; // never act on rows the manifest does not declare
            String type = found.optString("type", "button");
            if ("toggle".equals(type)) {
                boolean on = TweakHost.setting(parts[0], parts[1] + "/" + row, "off");
                TweakHost.setSetting(parts[0], parts[1] + "/" + row, !on);
            }
            if ("button".equals(type) || "toggle".equals(type)) TweakHost.tapped(rowId);
        } catch (RuntimeException failure) {
            Log.w("WinterX", "tweak action failed", failure);
        }
    }

    private static JSONObject findRow(JSONObject page, String rowId) {
        if (page == null) return null;
        JSONArray sections = page.optJSONArray("sections");
        int count = sections == null ? 0 : sections.length();
        for (int i = 0; i < count; i++) {
            JSONObject section = sections.optJSONObject(i);
            JSONArray rows = section == null ? null : section.optJSONArray("rows");
            int rowsCount = rows == null ? 0 : rows.length();
            for (int r = 0; r < rowsCount; r++) {
                JSONObject candidate = rows.optJSONObject(r);
                if (candidate != null && rowId.equals(candidate.optString("id", ""))) return candidate;
            }
        }
        return null;
    }
}
