package winterx.tweaks;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;
import winterx.extension.NativeRuntime;

/** Generic Spring home snapshot; mutations and custom grid policy come from installed code providers. */
public final class HomeApi {
    public static final String ABI = "winterx-home-grid-v1";
    private HomeApi() {}
    private static JSONArray page(List<E1.c> values, int columns) throws Exception {
        if (values == null || values.size() > 100) throw new java.io.IOException("Invalid native home page");
        JSONArray result = new JSONArray();
        for (E1.c entry : values) result.put(new JSONObject().put("id", entry.a.a).put("slot", entry.b * columns + entry.c));
        return result;
    }
    public static JSONObject snapshot(x1.i1 spring) throws Exception {
        Object provided = NativeRuntime.dispatch("home.snapshot", new Object[]{spring}, null, "first", false, JSONObject.class);
        if (provided instanceof JSONObject) return (JSONObject)provided;
        if (TweakHost.safeMode() || spring == null || spring.e == null || spring.e.k == null || spring.W1 != null || spring.S1 == null || spring.S1.size() > 100)
            throw new java.io.IOException("Home unavailable or editing/Safe Mode active");
        int rows = spring.e.k.a, columns = spring.e.k.b;
        if (rows < 1 || columns < 1 || (long)rows * columns > 100) throw new java.io.IOException("Invalid native grid");
        JSONArray pages = new JSONArray(), dock = new JSONArray(); pages.put(page(spring.L1, columns));
        int count = spring.L1.size();
        for (Object value : spring.S1) { List<E1.c> entries = (List<E1.c>)value; count += entries.size(); if (count > 500) throw new java.io.IOException("Too many home icons"); pages.put(page(entries, columns)); }
        if (spring.M1 == null || spring.M1.size() > 100) throw new java.io.IOException("Invalid native dock");
        for (Object value : spring.M1) if (value instanceof E1.a) dock.put(((E1.a)value).a);
        JSONObject result = new JSONObject().put("abi", ABI).put("columns", columns).put("capacity", rows * columns)
            .put("pages", pages).put("dock", dock).put("gridEnabled", false);
        StringBuilder revision = new StringBuilder();
        for (byte value : MessageDigest.getInstance("SHA-256").digest(result.toString().getBytes(StandardCharsets.UTF_8))) revision.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
        return result.put("revision", revision.toString());
    }
    public static JSONObject move(x1.i1 spring, JSONObject request) throws Exception {
        Object result = NativeRuntime.dispatch("home.move", new Object[]{spring, request}, null, "first", false, JSONObject.class);
        if (result instanceof JSONObject) return (JSONObject)result;
        throw new java.io.IOException("No installed home-grid code provider accepted this move");
    }
}
