package winterx.coloredbar;

import android.app.ActivityThread;
import android.app.Application;
import android.util.Log;
import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import org.json.JSONArray;
import winterx.appearance.BarArtwork;
import winterx.appearance.RubyAppearance;

/** Native Settings preferences and per-render navigation artwork, never a global asset replacement. */
public final class ColoredBar {
    public static final String ENABLED = "coloredbar.enabled";
    public static final String COLOR = "coloredbar.color";
    public static final String EXCLUSIONS = "coloredbar.exclusions.json";
    public static final String PAGE = "winterx-cb-page";
    public static final String ROOT_ROW = "winterx-cb-picker";
    public static final String APPS_PAGE = PAGE + "/apps";
    public static final String PREFIX = "winterx-cb-color-";
    private static final String DIGIT_PAGE = PAGE + "/digit/";
    private static final String DIGIT_ACTION = "winterx-cb-digit/";
    private static final String APP_ACTION = "winterx-cb-exclude/";
    private static final String DEFAULT = "FF3B30";
    private static final String[] DIGITS = {"Red — first digit", "Red — second digit", "Green — first digit",
        "Green — second digit", "Blue — first digit", "Blue — second digit"};
    private static final String[][] CHOICES = {
        {"Red", "FF3B30"}, {"Orange", "FF9500"}, {"Yellow", "FFCC00"}, {"Green", "34C759"},
        {"Teal", "5AC8FA"}, {"Blue", "007AFF"}, {"Purple", "AF52DE"}, {"Graphite", "2C2C2E"}
    };
    private static final TreeMap<String, String> APPS = new TreeMap<>();
    private static Object observedPages, observedDock, observedExtra;
    private static long lastRead;
    private static String cachedColor = DEFAULT;
    private static Set<String> cachedExclusions = Collections.emptySet();

    private ColoredBar() {}

    private static File folder() {
        Application app = ActivityThread.currentApplication();
        return app == null ? null : new File(app.getFilesDir(), "ruby");
    }

    public static boolean enabled() {
        try {
            File dir = folder();
            return dir != null && !new File(dir, "safe-mode.enabled").isFile() && new File(dir, ENABLED).isFile();
        } catch (RuntimeException failure) { return false; }
    }

    private static String read(String name, int limit) {
        File dir = folder();
        if (dir == null) return null;
        File file = new File(dir, name);
        if (!file.isFile() || file.length() > limit) return null;
        try (FileInputStream in = new FileInputStream(file)) {
            byte[] bytes = new byte[(int) file.length()];
            int at = 0;
            while (at < bytes.length) {
                int n = in.read(bytes, at, bytes.length - at);
                if (n < 0) return null;
                at += n;
            }
            return new String(bytes, StandardCharsets.UTF_8);
        } catch (Exception failure) { return null; }
    }

    static synchronized String color() {
        refresh();
        return cachedColor;
    }

    private static void refresh() {
        long now = android.os.SystemClock.elapsedRealtime();
        if (lastRead != 0 && now >= lastRead && now - lastRead < 500) return;
        String hex = read(COLOR, 16);
        cachedColor = hex != null && hex.trim().matches("(?i)[0-9a-f]{6}") ? hex.trim().toUpperCase(Locale.US) : DEFAULT;
        java.util.HashSet<String> excluded = new java.util.HashSet<>();
        try {
            String json = read(EXCLUSIONS, 65536);
            JSONArray list = new JSONArray(json == null ? "[]" : json);
            for (int i = 0; i < Math.min(list.length(), 256); i++) {
                String id = list.optString(i);
                if (validApp(id)) excluded.add(id);
            }
        } catch (Exception ignored) {}
        cachedExclusions = excluded;
        lastRead = now;
    }

    private static boolean validApp(String id) {
        return id != null && id.length() <= 160 && id.matches("[A-Za-z0-9][A-Za-z0-9._:-]*");
    }

    static boolean navigationAsset(String name) {
        return BarArtwork.navigationAsset(name);
    }

    /** Called in Spring's two per-app render dispatchers, including screenshots of other apps. */
    public static synchronized Map assets(Map original, String appId) {
        if (original == null || RubyAppearance.isRuby(appId) || !enabled() || !validApp(appId)) return original;
        refresh();
        if (cachedExclusions.contains(appId)) return original;
        return BarArtwork.view(original, cachedColor, false);
    }

    /** I1.S0 is Settings-only, including its separate iOS 6 view and cached lookups. */
    public static synchronized Object settingsAsset(Object key, Object value) {
        if (!navigationAsset(key instanceof String ? (String) key : null) || !enabled()) return value;
        refresh();
        return cachedExclusions.contains("settings") ? value : BarArtwork.asset(key, value, cachedColor, false);
    }

    static int tintPixel(int pixel, int rgb) {
        return BarArtwork.tintPixel(pixel, rgb);
    }

    /** Read only; never changes Spring's pages, positions or icon ordering. */
    public static synchronized void observe(E1.q6 state) {
        if (state == null || !enabled()) return;
        if (observedPages == state.b && observedDock == state.c && observedExtra == state.n0) return;
        observedPages = state.b; observedDock = state.c; observedExtra = state.n0;
        APPS.clear();
        collect(state.b); collect(state.c); collect(state.n0);
        APPS.put("settings", "Settings");
    }

    private static void collect(Object items) {
        if (items instanceof E1.c) {
            collect(((E1.c) items).a);
        } else if (items instanceof E1.a) {
            E1.a app = (E1.a) items;
            if (validApp(app.a)) APPS.put(app.a, app.b == null ? app.a : app.b);
        } else if (items instanceof List) {
            for (Object item : (List) items) if (item instanceof E1.a || item instanceof E1.c || item instanceof List) collect(item);
        }
    }

    private static V6 row(String id, String title, String page) {
        return Z3.g(Z3.a, id, title, page, null, null, 0x18);
    }

    public static synchronized T6 page(String pageId) {
        if (pageId == null || !enabled()) return null;
        refresh();
        List<W6> sections = new ArrayList<>();
        if (PAGE.equals(pageId)) {
            List<V6> presets = new ArrayList<>();
            for (String[] choice : CHOICES) presets.add(row(PREFIX + choice[1], choice[0] + (choice[1].equals(cachedColor) ? "  ✓" : ""), null));
            List<V6> custom = new ArrayList<>();
            for (int i = 0; i < 6; i++) custom.add(row(DIGIT_PAGE + i, DIGITS[i] + ": " + cachedColor.charAt(i), DIGIT_PAGE + i));
            sections.add(new W6("PRESETS", null, null, null, presets));
            sections.add(new W6("CUSTOM HEX COLOUR — #" + cachedColor, "Choose each hex digit for any 24-bit RGB colour.", null, null, custom));
            sections.add(new W6(null, null, null, null, Collections.singletonList(row(APPS_PAGE, "Excluded Apps", APPS_PAGE))));
            return new T6(pageId, "ColoredBar", sections);
        }
        if (pageId.startsWith(DIGIT_PAGE) && pageId.substring(DIGIT_PAGE.length()).matches("[0-5]")) {
            int at = Integer.parseInt(pageId.substring(DIGIT_PAGE.length()));
            List<V6> values = new ArrayList<>();
            for (char digit : "0123456789ABCDEF".toCharArray()) values.add(row(DIGIT_ACTION + at + "/" + digit, digit + (digit == cachedColor.charAt(at) ? "  ✓" : ""), null));
            return new T6(pageId, DIGITS[at], Collections.singletonList(new W6("CURRENT — #" + cachedColor, null, null, null, values)));
        }
        if (APPS_PAGE.equals(pageId)) {
            List<V6> apps = new ArrayList<>();
            TreeMap<String, String> known = new TreeMap<>(APPS);
            for (String id : cachedExclusions) if (!known.containsKey(id)) known.put(id, id);
            known.remove("sapp:com.ruby.manager"); known.remove("com.ruby.manager");
            for (Map.Entry<String, String> app : known.entrySet()) apps.add(row(APP_ACTION + app.getKey(), app.getValue() + (cachedExclusions.contains(app.getKey()) ? "  ✓" : ""), null));
            return new T6(pageId, "Excluded Apps", Collections.singletonList(new W6("KEEP STOCK COLOURS", "Checked apps keep their original navigation artwork. Ruby is always excluded and keeps its own red bars.", null, null, apps)));
        }
        return null;
    }

    public static synchronized boolean action(String rowId) {
        if (rowId == null || !enabled()) return false;
        refresh();
        if (rowId.startsWith(PREFIX)) {
            String hex = rowId.substring(PREFIX.length()).toUpperCase(Locale.US);
            if (!hex.matches("[0-9A-F]{6}")) return false;
            return store(COLOR, hex + "\n");
        }
        if (rowId.startsWith(DIGIT_ACTION)) {
            String[] value = rowId.substring(DIGIT_ACTION.length()).split("/", -1);
            if (value.length != 2 || !value[0].matches("[0-5]") || !value[1].matches("[0-9A-F]")) return false;
            StringBuilder hex = new StringBuilder(cachedColor);
            hex.setCharAt(Integer.parseInt(value[0]), value[1].charAt(0));
            return store(COLOR, hex + "\n");
        }
        if (rowId.startsWith(APP_ACTION)) {
            String id = rowId.substring(APP_ACTION.length());
            if (RubyAppearance.isRuby(id) || !validApp(id) || (!APPS.containsKey(id) && !cachedExclusions.contains(id))) return false;
            java.util.TreeSet<String> excluded = new java.util.TreeSet<>(cachedExclusions);
            if (!excluded.remove(id)) excluded.add(id);
            return store(EXCLUSIONS, new JSONArray(excluded).toString());
        }
        return false;
    }

    private static boolean store(String name, String text) {
        File temp = null;
        try {
            File dir = folder();
            if (dir == null) return false;
            dir.mkdirs();
            temp = File.createTempFile(".coloredbar-", ".tmp", dir);
            try (FileOutputStream out = new FileOutputStream(temp)) {
                out.write(text.getBytes(StandardCharsets.UTF_8)); out.getFD().sync();
            }
            if (!temp.renameTo(new File(dir, name))) throw new java.io.IOException("Could not save ColoredBar preferences");
            lastRead = 0;
            return true;
        } catch (Exception failure) {
            Log.w("WinterX", "ColoredBar preference save failed", failure);
            return false;
        } finally { if (temp != null) temp.delete(); }
    }
}
