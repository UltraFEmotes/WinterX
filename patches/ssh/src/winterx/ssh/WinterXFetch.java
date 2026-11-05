package winterx.ssh;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Bounded, read-only system information. No shell, private files or unique device identifiers. */
public final class WinterXFetch {
    private static final Class<?>[] NO_TYPES = new Class<?>[0];
    private static final String[] LOGO = {
        " __      __ __  __",
        " \\ \\ /\\ / / \\ \\/ /",
        "  \\ V  V /   >  <",
        "   \\_/\\_/   /_/\\_\\"
    };
    private static final String RED = "\u001b[1;31m", BOLD = "\u001b[1m", RESET = "\u001b[0m";
    private WinterXFetch() {}

    private static Class<?> platform(String name) {
        try { return Class.forName(name, false, WinterXFetch.class.getClassLoader()); }
        catch (ReflectiveOperationException | RuntimeException | LinkageError unavailable) { return null; }
    }
    private static Object field(Object object, String name) {
        if (object == null) return null;
        try {
            Class<?> type = object instanceof Class<?> ? (Class<?>)object : object.getClass();
            return type.getField(name).get(object instanceof Class<?> ? null : object);
        } catch (ReflectiveOperationException | RuntimeException | LinkageError unavailable) { return null; }
    }
    private static Object call(Object object, String name, Class<?>[] types, Object... arguments) {
        if (object == null) return null;
        try {
            Class<?> type = object instanceof Class<?> ? (Class<?>)object : object.getClass();
            Method method = type.getMethod(name, types);
            return method.invoke(object instanceof Class<?> ? null : object, arguments);
        } catch (ReflectiveOperationException | RuntimeException | LinkageError unavailable) { return null; }
    }
    private static String text(Object value) { return value == null ? "unavailable" : String.valueOf(value); }
    private static long number(Object value) { return value instanceof Number ? ((Number)value).longValue() : -1; }
    private static String property(String name) {
        try { return text(System.getProperty(name)); }
        catch (SecurityException unavailable) { return "unavailable"; }
    }
    private static String display(Object app) {
        Object resources = call(app, "getResources", NO_TYPES);
        Object metrics = call(resources, "getDisplayMetrics", NO_TYPES);
        long width = number(field(metrics, "widthPixels")), height = number(field(metrics, "heightPixels"));
        long dpi = number(field(metrics, "densityDpi"));
        if (width < 1 || height < 1 || width > 32768 || height > 32768 || dpi < 1 || dpi > 10000)
            return "unavailable";
        return width + " x " + height + " / " + dpi + " dpi";
    }
    private static String version(Object app) {
        Object name = call(app, "getPackageName", NO_TYPES), manager = call(app, "getPackageManager", NO_TYPES);
        if (!(name instanceof String)) return "unavailable";
        Object info = call(manager, "getPackageInfo", new Class<?>[]{String.class, int.class}, name, 0);
        return text(field(info, "versionName"));
    }
    private static String uptime(long milliseconds) {
        if (milliseconds < 0) return "unavailable";
        long minutes = milliseconds / 60000, days = minutes / 1440, hours = minutes / 60 % 24;
        return (days > 0 ? days + "d " : "") + hours + "h " + minutes % 60 + "m";
    }
    static Map<String, String> facts() {
        Map<String, String> values = new LinkedHashMap<>();
        Object app = call(platform("android.app.ActivityThread"), "currentApplication", NO_TYPES);
        Class<?> build = platform("android.os.Build"), android = platform("android.os.Build$VERSION");
        String host = property("os.name"), vm = property("java.vm.name");
        String runtime = app == null ? "Host JVM (no Android app)"
            : vm.equals("Dalvik") || vm.equals("ART") ? "Android"
            : host.equals("Mac OS X") || host.equals("Darwin") ? "Android compatibility on macOS"
            : "Android compatibility / " + host;
        values.put("Build", "development / ssh-info-v1");
        values.put("Runtime", runtime);
        values.put("Spring", version(app));
        values.put("Reported device", text(field(build, "MANUFACTURER")) + " " + text(field(build, "MODEL")));
        Object release = field(android, "RELEASE"); long sdk = number(field(android, "SDK_INT"));
        values.put("Reported Android", release == null || sdk < 1 ? "unavailable" : text(release) + " / API " + sdk);
        values.put("Reported display", display(app));
        values.put("Host OS", host + " " + property("os.version"));
        values.put("CPU arch", property("os.arch"));
        Runtime java = Runtime.getRuntime();
        values.put("Runtime CPUs", String.valueOf(java.availableProcessors()));
        long used = Math.max(0, java.totalMemory() - java.freeMemory());
        values.put("Java heap", used / 1048576 + " / " + java.maxMemory() / 1048576 + " MiB");
        values.put("Device uptime", uptime(number(call(platform("android.os.SystemClock"), "elapsedRealtime", NO_TYPES))));
        values.put("SSH", "winterx@127.0.0.1:2222");
        values.put("Access", "Spring process; no su");
        return values;
    }
    private static String clean(String value, int maximum) {
        if (value == null || value.trim().isEmpty()) return "unavailable";
        StringBuilder safe = new StringBuilder();
        for (int i = 0; i < value.length() && safe.length() <= maximum; i++) {
            char c = value.charAt(i);
            boolean control = Character.isISOControl(c) || c >= '\u200b' && c <= '\u200f'
                || c >= '\u2028' && c <= '\u202e' || c >= '\u2066' && c <= '\u2069';
            safe.append(control ? ' ' : c);
        }
        String result = safe.toString().trim();
        return result.length() > maximum ? result.substring(0, maximum - 3) + "..." : result;
    }
    private static String pad(String value, int width) {
        StringBuilder padded = new StringBuilder(value);
        while (padded.length() < width) padded.append(' ');
        return padded.toString();
    }
    static String render(Map<String, String> values, boolean color) {
        List<String> lines = new ArrayList<>();
        lines.add(color ? RED + "WinterX" + RESET : "WinterX"); lines.add("-------");
        int count = 0;
        for (Map.Entry<String, String> value : values.entrySet()) {
            if (++count > 16) break;
            String label = pad(clean(value.getKey(), 17), 17);
            lines.add((color ? BOLD + label + RESET : label) + "  " + clean(value.getValue(), 36));
        }
        int width = 0; for (String line : LOGO) width = Math.max(width, line.length());
        StringBuilder report = new StringBuilder();
        for (int i = 0; i < lines.size(); i++) {
            String logo = pad(i < LOGO.length ? LOGO[i] : "", width);
            report.append(color ? RED + logo + RESET : logo).append("   ").append(lines.get(i)).append('\n');
        }
        return report.toString();
    }
    public static String report(boolean color) { return render(facts(), color); }
}
