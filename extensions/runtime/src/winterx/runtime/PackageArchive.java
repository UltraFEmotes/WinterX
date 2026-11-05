package winterx.runtime;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.URI;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Pattern;
import java.util.zip.Adler32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.json.JSONArray;
import org.json.JSONObject;

/** Validates winterx.springys/3 archives exactly as tools/native_package.py does. Never executes package code. */
public final class PackageArchive {
    static final String FORMAT = "winterx.springys/3", API = "winterx.native/1";
    static final String DEX = "code/classes.dex", JAR = "code/classes.jar";
    static final int MAX_ZIP = 12 * 1024 * 1024, MAX_FILES = 128, MAX_PAYLOAD = 16 * 1024 * 1024, MAX_EXPANDED = 32 * 1024 * 1024;
    static final int MAX_ART = 2 * 1024 * 1024, MAX_APPS = 4;
    static final Pattern ID = Pattern.compile("[a-z0-9]+(?:[.-][a-z0-9]+)+");
    static final Pattern VERSION = Pattern.compile("[0-9]+(?:\\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?");
    static final Pattern CLASS = Pattern.compile("[a-zA-Z_$][A-Za-z0-9_$]*(?:\\.[a-zA-Z_$][A-Za-z0-9_$]*)+");
    static final Pattern POINT = Pattern.compile("[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+");
    static final Pattern SOURCE = Pattern.compile("source/(?:[A-Za-z0-9_$.-]+/)*[A-Za-z0-9_$.-]+\\.(?:java|js|json)");
    static final Pattern LICENSE = Pattern.compile("licenses/[A-Za-z0-9._-]+/(?:LICENSE|NOTICE)(?:\\.txt)?");
    static final Pattern APP = Pattern.compile("apps/[A-Za-z0-9][A-Za-z0-9._-]{0,80}\\.sapp");
    static final Pattern INJECT = Pattern.compile("inject/[A-Za-z0-9][A-Za-z0-9._-]{0,80}\\.js");
    static final Pattern ART = Pattern.compile("assets/[A-Za-z0-9][A-Za-z0-9._/-]*\\.(?:png|jpg|jpeg)", Pattern.CASE_INSENSITIVE);
    static final Pattern HEX = Pattern.compile("[0-9a-f]{64}");
    static final Pattern SETTINGS_ENTRY = Pattern.compile("[A-Za-z0-9_./-]+");
    static final Pattern DEX_NAME = Pattern.compile("L[A-Za-z0-9_$/-]+;");
    static final Pattern OBFUSCATED = Pattern.compile("(?:[A-Za-z]|[A-Za-z][0-9]+)/.*", Pattern.DOTALL);
    static final Set<String> META = new HashSet<>(Arrays.asList("format", "type", "runtime", "api", "entry", "id", "name", "version",
        "description", "author", "license", "source", "exports", "capabilities", "files", "icon", "previews", "features", "requires",
        "settings_entry", "apps", "inject"));
    /** Trusted WinterX apps keep their pinned installs; a package can never replace them. */
    static final Set<String> RESERVED_APPS = new HashSet<>(Arrays.asList("com.ruby.manager", "com.ruby.jailbreak", "com.winterx.iexplored"));

    private PackageArchive() {}

    public static final class Inspected {
        public final JSONObject metadata;
        public final Map<String, byte[]> media, payloads;
        Inspected(JSONObject metadata, Map<String, byte[]> media, Map<String, byte[]> payloads) {
            this.metadata = metadata; this.media = media; this.payloads = payloads;
        }
    }

    static IOException error(String message) { return new IOException(message); }

    public static String sha256(byte[] value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value);
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest) hex.append(Character.forDigit((b >> 4) & 15, 16)).append(Character.forDigit(b & 15, 16));
            return hex.toString();
        } catch (Exception impossible) { throw new IllegalStateException(impossible); }
    }

    static boolean safePath(String name) {
        if (name == null || name.length() > 240 || name.startsWith("/") || name.indexOf('\\') >= 0) return false;
        for (String part : name.split("/", -1)) if (part.isEmpty() || ".".equals(part) || "..".equals(part)) return false;
        return true;
    }

    static boolean reservedClass(String name) {
        String[] prefixes = {"java/", "javax/", "android/", "dalvik/", "com/guille/spring/", "winterx/extension/", "winterx/runtime/",
            "winterx/tweaks/", "winterx/recovery/", "winterx/appearance/"};
        for (String prefix : prefixes) if (name.startsWith(prefix)) return true;
        return OBFUSCATED.matcher(name).matches();
    }

    static String text(JSONObject object, String key, int limit) throws IOException {
        Object value = object.opt(key);
        if (!(value instanceof String) || ((String)value).trim().isEmpty() || ((String)value).length() > limit || ((String)value).indexOf('\0') >= 0)
            throw error("Invalid " + key);
        return (String)value;
    }

    static List<String> strings(Object value, int max, Pattern pattern, int length) {
        if (value == null) return new ArrayList<>();
        if (!(value instanceof JSONArray) || ((JSONArray)value).length() > max) return null;
        List<String> result = new ArrayList<>();
        JSONArray array = (JSONArray)value;
        for (int i = 0; i < array.length(); i++) {
            Object item = array.opt(i);
            if (!(item instanceof String) || ((String)item).length() > length || !pattern.matcher((String)item).matches() || result.contains(item)) return null;
            result.add((String)item);
        }
        return result;
    }

    static String artPath(Object value) throws IOException {
        if (!(value instanceof String) || !ART.matcher((String)value).matches()) throw error("Artwork must be a PNG or JPEG inside assets/");
        for (String part : ((String)value).split("/", -1)) if (part.isEmpty() || ".".equals(part) || "..".equals(part)) throw error("Invalid artwork path");
        return (String)value;
    }

    static void image(String name, byte[] payload) throws IOException {
        if (payload.length == 0 || payload.length > MAX_ART) throw error("Artwork too large or empty: " + name);
        if (name.toLowerCase(Locale.ROOT).endsWith(".png")) {
            byte[] signature = {(byte)0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'};
            if (payload.length < 24 || !Arrays.equals(Arrays.copyOf(payload, 8), signature) || payload[12] != 'I' || payload[13] != 'H' || payload[14] != 'D' || payload[15] != 'R')
                throw error("Invalid PNG: " + name);
            long width = u32be(payload, 16), height = u32be(payload, 20);
            if (width < 1 || width > 4096 || height < 1 || height > 4096) throw error("PNG dimensions out of range: " + name);
        } else if (payload.length < 5 || (payload[0] & 0xff) != 0xff || (payload[1] & 0xff) != 0xd8 || (payload[2] & 0xff) != 0xff
                   || (payload[payload.length - 2] & 0xff) != 0xff || (payload[payload.length - 1] & 0xff) != 0xd9) {
            throw error("Invalid JPEG: " + name);
        }
    }

    static long u32be(byte[] b, int at) { return ((b[at] & 0xffL) << 24) | ((b[at + 1] & 0xffL) << 16) | ((b[at + 2] & 0xffL) << 8) | (b[at + 3] & 0xffL); }
    static long u32(byte[] b, int at) { return (b[at] & 0xffL) | ((b[at + 1] & 0xffL) << 8) | ((b[at + 2] & 0xffL) << 16) | ((b[at + 3] & 0xffL) << 24); }

    /** Read a ZIP from memory with bounded entry count and per-entry/total sizes; duplicate names are refused. */
    static Map<String, byte[]> unzip(byte[] raw, int maxEntries, long maxEntry, long maxTotal, boolean allowDirectories) throws IOException {
        Map<String, byte[]> entries = new LinkedHashMap<>();
        Set<String> folded = new HashSet<>();
        long total = 0;
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(raw))) {
            byte[] buffer = new byte[65536];
            for (ZipEntry entry; (entry = zip.getNextEntry()) != null;) {
                String name = entry.getName();
                if (entries.size() >= maxEntries) throw error("Archive has too many entries");
                if (entry.getMethod() != ZipEntry.STORED && entry.getMethod() != ZipEntry.DEFLATED) throw error("Unsupported ZIP compression");
                if (entry.isDirectory()) {
                    if (!allowDirectories || !safePath(name.substring(0, name.length() - 1))) throw error("Unsafe or oversized package entry");
                    if (entries.put(name, null) != null || entries.containsKey(name) && !folded.add(name.toLowerCase(Locale.ROOT))) throw error("Duplicate archive entry");
                    continue;
                }
                if (entries.containsKey(name) || !folded.add(name.toLowerCase(Locale.ROOT))) throw error("Duplicate or case-colliding package path");
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                for (int n; (n = zip.read(buffer)) > 0;) {
                    total += n;
                    if (out.size() + n > maxEntry || total > maxTotal) throw error("Unsafe or oversized package entry");
                    out.write(buffer, 0, n);
                }
                entries.put(name, out.toByteArray());
            }
        }
        return entries;
    }

    static List<String> dexClasses(byte[] raw) throws IOException {
        String[] magics = {"dex\n035\0", "dex\n037\0", "dex\n038\0", "dex\n039\0", "dex\n040\0"};
        boolean magic = false;
        if (raw.length >= 112) {
            String head = new String(raw, 0, 8, StandardCharsets.ISO_8859_1);
            for (String m : magics) magic |= m.equals(head);
        }
        if (!magic || u32(raw, 32) != raw.length || u32(raw, 36) != 112 || u32(raw, 40) != 0x12345678L) throw error("Invalid Android DEX header/checksum");
        try {
            MessageDigest sha1 = MessageDigest.getInstance("SHA-1"); sha1.update(raw, 32, raw.length - 32);
            if (!Arrays.equals(sha1.digest(), Arrays.copyOfRange(raw, 12, 32))) throw error("Invalid Android DEX header/checksum");
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
        Adler32 adler = new Adler32(); adler.update(raw, 12, raw.length - 12);
        if (adler.getValue() != u32(raw, 8)) throw error("Invalid Android DEX header/checksum");
        long stringCount = u32(raw, 56), strings = u32(raw, 60), typeCount = u32(raw, 64), types = u32(raw, 68);
        long classCount = u32(raw, 96), classes = u32(raw, 100);
        if (classCount < 1 || classCount > 20000) throw error("Invalid Android DEX class count");
        long[][] tables = {{strings, stringCount, 4}, {types, typeCount, 4}, {classes, classCount, 32}};
        for (long[] t : tables) if (t[0] < 112 || t[0] % 4 != 0 || t[0] + t[1] * t[2] > raw.length) throw error("Invalid Android DEX table");
        List<String> result = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (int index = 0; index < classCount; index++) {
            long typeIndex = u32(raw, (int)(classes + index * 32L));
            if (typeIndex >= typeCount) throw error("Invalid DEX class type index");
            long stringIndex = u32(raw, (int)(types + typeIndex * 4));
            if (stringIndex >= stringCount) throw error("Invalid DEX type string index");
            int offset = (int)u32(raw, (int)(strings + stringIndex * 4));
            boolean ended = false;
            for (int i = 0; i < 5; i++) {
                if (offset < 0 || offset >= raw.length) throw error("Truncated DEX string");
                int b = raw[offset++] & 0xff;
                if (b < 128) { ended = true; break; }
            }
            if (!ended) throw error("Invalid DEX string length");
            int end = -1;
            for (int i = offset; i < Math.min(raw.length, offset + 1024); i++) if (raw[i] == 0) { end = i; break; }
            if (end < 0) throw error("Unterminated DEX class name");
            String name = new String(raw, offset, end - offset, StandardCharsets.ISO_8859_1);
            if (!DEX_NAME.matcher(name).matches() || !safePath(name.substring(1, name.length() - 1))) throw error("Invalid DEX class name");
            if (!seen.add(name)) throw error("Duplicate DEX class definition");
            result.add(name);
        }
        return result;
    }

    static void checkJar(byte[] raw, String entryClass) throws IOException {
        Map<String, byte[]> entries = unzip(raw, 20000, 64L * 1024 * 1024, 64L * 1024 * 1024, true);
        if (!entries.containsKey(entryClass.replace('.', '/') + ".class")) throw error("Native entry class missing or duplicated");
        for (Map.Entry<String, byte[]> entry : entries.entrySet()) {
            String name = entry.getKey();
            if (entry.getValue() == null) continue;
            if (!safePath(name) || reservedClass(name)) throw error("Native package cannot replace platform/Spring/runtime classes");
            byte[] value = entry.getValue();
            if (name.endsWith(".class") && (value.length < 4 || (value[0] & 0xff) != 0xca || (value[1] & 0xff) != 0xfe || (value[2] & 0xff) != 0xba || (value[3] & 0xff) != 0xbe))
                throw error("Invalid JVM class payload");
        }
    }

    /** A bundled Spring app: a .sapp ZIP whose app.json names a non-reserved app ID and positive build. */
    static JSONObject bundledApp(String path, byte[] raw) throws IOException {
        Map<String, byte[]> files = unzip(raw, 512, MAX_PAYLOAD, 40L * 1024 * 1024, true);
        byte[] manifest = files.get("app.json");
        if (manifest == null || manifest.length > 64 * 1024 || !files.containsKey("main.js") || files.get("main.js") == null)
            throw error("Bundled app needs app.json and main.js: " + path);
        JSONObject app = StrictJson.object(manifest);
        String id = text(app, "id", 120);
        if (!ID.matcher(id).matches() || RESERVED_APPS.contains(id)) throw error("Bundled app cannot use app ID " + id);
        Object build = app.opt("build");
        if (!(build instanceof Integer) || (Integer)build < 1) throw error("Bundled app needs a positive integer build: " + path);
        JSONObject result = new JSONObject();
        try {
            result.put("path", path).put("id", id).put("build", build).put("name", text(app, "name", 80));
            if (app.opt("version") instanceof String) result.put("version", app.getString("version"));
        } catch (org.json.JSONException impossible) { throw error(impossible.getMessage()); }
        return result;
    }

    public static Inspected inspect(byte[] raw, String expectedSha256, boolean includeCode) throws IOException {
        if (raw.length > MAX_ZIP) throw error("Package exceeds 12 MB");
        String digest = sha256(raw);
        if (expectedSha256 != null && (!HEX.matcher(expectedSha256).matches() || !digest.equals(expectedSha256))) throw error("Package SHA-256 does not match");
        Map<String, byte[]> archive = unzip(raw, MAX_FILES, MAX_PAYLOAD, MAX_EXPANDED, false);
        if (archive.size() < 4) throw error("Native package exceeds its entry/expanded-byte limit");
        for (String name : archive.keySet()) if (!safePath(name)) throw error("Unsafe or oversized native package entry");
        byte[] rawManifest = archive.get("manifest.json");
        if (rawManifest == null || rawManifest.length > 128 * 1024) throw error("Native manifest missing or oversized");
        JSONObject manifest = StrictJson.object(rawManifest);
        for (Iterator<String> keys = manifest.keys(); keys.hasNext();) if (!META.contains(keys.next())) throw error("Invalid source-backed native package manifest");
        if (!FORMAT.equals(manifest.opt("format")) || !"tweak".equals(manifest.opt("type")) || !"java".equals(manifest.opt("runtime")) || !API.equals(manifest.opt("api")))
            throw error("Invalid source-backed native package manifest");
        String id = text(manifest, "id", 120), version = text(manifest, "version", 64);
        if (!ID.matcher(id).matches() || !VERSION.matcher(version).matches()) throw error("Invalid native package identity/version");
        text(manifest, "name", 80); text(manifest, "description", 4000); text(manifest, "author", 120); text(manifest, "license", 80);
        String entry = text(manifest, "entry", 180);
        if (!CLASS.matcher(entry).matches() || reservedClass(entry.replace('.', '/'))) throw error("Native entry must name the package implementation, not a framework class");
        Object capabilities = manifest.opt("capabilities");
        if (!(capabilities instanceof JSONArray) || ((JSONArray)capabilities).length() != 1 || !"native.hooks".equals(((JSONArray)capabilities).opt(0)))
            throw error("Native packages must declare the native.hooks capability");
        List<String> exports = strings(manifest.opt("exports"), 128, POINT, 160);
        if (exports == null || exports.isEmpty() || !(manifest.opt("exports") instanceof JSONArray)) throw error("Invalid native hook exports");
        if (strings(manifest.opt("features"), 32, POINT, 160) == null) throw error("Invalid native feature declarations");
        List<String> requires = strings(manifest.opt("requires"), 16, ID, 120);
        if (requires == null || requires.contains(id)) throw error("Invalid native package dependencies");
        Object source = manifest.opt("source");
        boolean sourceOk = source instanceof String && ((String)source).length() <= 500;
        if (sourceOk) for (char c : ((String)source).toCharArray()) if (c < 33) sourceOk = false;
        if (!sourceOk) throw error("Native packages must link their published source");
        try {
            URI url = new URI((String)source);
            if (!"https".equals(url.getScheme()) || url.getHost() == null || url.getUserInfo() != null || url.getFragment() != null)
                throw error("Native source must be an HTTPS URL without credentials or fragments");
        } catch (java.net.URISyntaxException bad) { throw error("Native source must be an HTTPS URL without credentials or fragments"); }
        Object settingsEntry = manifest.opt("settings_entry");
        if (settingsEntry != null && (!(settingsEntry instanceof String) || ((String)settingsEntry).length() > 180 || !SETTINGS_ENTRY.matcher((String)settingsEntry).matches()))
            throw error("Invalid native Settings entry");
        Object filesValue = manifest.opt("files");
        if (!(filesValue instanceof JSONObject)) throw error("Native package must pin both Android DEX and JVM code");
        JSONObject declared = (JSONObject)filesValue;
        Map<String, String> pinned = new TreeMap<>();
        for (Iterator<String> keys = declared.keys(); keys.hasNext();) {
            String name = keys.next(); Object value = declared.opt(name);
            if (!(value instanceof String) || !HEX.matcher((String)value).matches()) throw error("Native package must pin both Android DEX and JVM code");
            pinned.put(name, (String)value);
        }
        if (!pinned.containsKey(DEX) || !pinned.containsKey(JAR)) throw error("Native package must pin both Android DEX and JVM code");
        boolean javaSource = false;
        for (String name : pinned.keySet()) javaSource |= SOURCE.matcher(name).matches() && name.endsWith(".java");
        if (!javaSource) throw error("Native packages must include editable Java source");
        String icon = manifest.has("icon") && manifest.opt("icon") != null && manifest.opt("icon") != JSONObject.NULL && !"".equals(manifest.opt("icon")) ? artPath(manifest.opt("icon")) : null;
        Object previewValue = manifest.opt("previews");
        List<String> previews = new ArrayList<>();
        if (previewValue != null) {
            if (!(previewValue instanceof JSONArray) || ((JSONArray)previewValue).length() > 5) throw error("Invalid native package previews");
            for (int i = 0; i < ((JSONArray)previewValue).length(); i++) previews.add(artPath(((JSONArray)previewValue).opt(i)));
        }
        Set<String> artwork = new HashSet<>(previews);
        if (icon != null) artwork.add(icon);
        List<String> apps = strings(manifest.opt("apps"), MAX_APPS, APP, 120);
        if (apps == null) throw error("Invalid bundled app list");
        for (String app : apps) if (!pinned.containsKey(app)) throw error("Bundled app must be pinned in files: " + app);
        Object injectValue = manifest.opt("inject");
        if (injectValue != null) {
            if (!(injectValue instanceof JSONArray) || ((JSONArray)injectValue).length() < 1 || ((JSONArray)injectValue).length() > 16) throw error("Invalid app script injection list");
            JSONArray inject = (JSONArray)injectValue;
            for (int i = 0; i < inject.length(); i++) {
                Object item = inject.opt(i);
                if (!(item instanceof JSONObject)) throw error("Invalid app script injection entry");
                JSONObject injection = (JSONObject)item;
                for (Iterator<String> keys = injection.keys(); keys.hasNext();) { String key = keys.next(); if (!"apps".equals(key) && !"script".equals(key)) throw error("Invalid app script injection entry"); }
                Object script = injection.opt("script"), targets = injection.opt("apps");
                if (!(script instanceof String) || !INJECT.matcher((String)script).matches() || !pinned.containsKey(script)) throw error("Injected script must be an inject/*.js file pinned in files");
                if (!(targets instanceof JSONArray) || ((JSONArray)targets).length() < 1 || ((JSONArray)targets).length() > 32) throw error("Injected script needs a list of target app IDs");
                for (int k = 0; k < ((JSONArray)targets).length(); k++) {
                    Object target = ((JSONArray)targets).opt(k);
                    if (!(target instanceof String) || !"*".equals(target) && (!ID.matcher((String)target).matches() || RESERVED_APPS.contains(target)))
                        throw error("Invalid injection target: " + target);
                }
            }
        }
        Set<String> expectedNames = new HashSet<>(pinned.keySet()); expectedNames.add("manifest.json"); expectedNames.addAll(artwork);
        if (!expectedNames.equals(archive.keySet())) throw error("Native package contains undeclared files");
        Map<String, byte[]> payloads = new TreeMap<>();
        for (Map.Entry<String, String> file : pinned.entrySet()) {
            String name = file.getKey();
            if (!DEX.equals(name) && !JAR.equals(name) && !SOURCE.matcher(name).matches() && !LICENSE.matcher(name).matches() && !APP.matcher(name).matches() && !INJECT.matcher(name).matches())
                throw error("Unsupported native code/source/license path: " + name);
            byte[] value = archive.get(name);
            if (!sha256(value).equals(file.getValue())) throw error("Native package payload checksum mismatch: " + name);
            if (name.startsWith("source/") || name.startsWith("inject/")) {
                if (value.length == 0 || value.length > 256 * 1024) throw error("Invalid or oversized native source file");
                for (byte b : value) if (b == 0) throw error("Invalid or oversized native source file");
                try { StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(value)); }
                catch (CharacterCodingException bad) { throw error("Invalid or oversized native source file"); }
            }
            payloads.put(name, value);
        }
        List<String> classes = dexClasses(payloads.get(DEX));
        if (!classes.contains("L" + entry.replace('.', '/') + ";")) throw error("Native Android entry class is missing");
        for (String name : classes) if (reservedClass(name.substring(1, name.length() - 1))) throw error("Native package cannot replace platform/Spring/runtime classes");
        checkJar(payloads.get(JAR), entry);
        JSONArray bundled = new JSONArray();
        Set<String> appIds = new HashSet<>();
        for (String app : apps) {
            JSONObject info = bundledApp(app, payloads.get(app));
            if (!appIds.add(info.optString("id"))) throw error("Two bundled apps share an app ID");
            bundled.put(info);
        }
        Map<String, byte[]> media = new TreeMap<>();
        for (String name : artwork) { byte[] value = archive.get(name); image(name, value); media.put(name, value); }
        try {
            JSONObject metadata = new JSONObject(manifest.toString());
            metadata.put("sha256", digest).put("code_sha256", pinned.get(DEX)).put("jvm_sha256", pinned.get(JAR))
                .put("icon", icon == null ? JSONObject.NULL : icon).put("previews", new JSONArray(previews));
            if (!apps.isEmpty()) metadata.put("bundled_apps", bundled);
            return new Inspected(metadata, media, includeCode ? payloads : null);
        } catch (org.json.JSONException impossible) { throw error(impossible.getMessage()); }
    }

    /** JSON syntax check that refuses duplicate object keys before org.json (which keeps the last one) parses it. */
    static final class StrictJson {
        private final String s; private int i;
        private StrictJson(String s) { this.s = s; }
        static JSONObject object(byte[] raw) throws IOException {
            String text;
            try { text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(raw)).toString(); }
            catch (CharacterCodingException bad) { throw error("Invalid UTF-8 JSON"); }
            StrictJson parser = new StrictJson(text);
            parser.space();
            if (parser.peek() != '{') throw error("JSON must be an object");
            parser.value(0); parser.space();
            if (parser.i != text.length()) throw error("Trailing JSON data");
            try { return new JSONObject(text); } catch (org.json.JSONException bad) { throw error("Invalid JSON: " + bad.getMessage()); }
        }
        private char peek() throws IOException { if (i >= s.length()) throw error("Truncated JSON"); return s.charAt(i); }
        private void space() { while (i < s.length() && " \t\r\n".indexOf(s.charAt(i)) >= 0) i++; }
        private void expect(char c) throws IOException { if (peek() != c) throw error("Invalid JSON"); i++; }
        private void value(int depth) throws IOException {
            if (depth > 64) throw error("JSON nested too deeply");
            space(); char c = peek();
            if (c == '{') {
                i++; Set<String> keys = new HashSet<>(); space();
                if (peek() == '}') { i++; return; }
                while (true) {
                    space(); String key = string();
                    if (!keys.add(key)) throw error("Duplicate JSON key: " + key);
                    space(); expect(':'); value(depth + 1); space();
                    if (peek() == ',') { i++; continue; }
                    expect('}'); return;
                }
            } else if (c == '[') {
                i++; space();
                if (peek() == ']') { i++; return; }
                while (true) { value(depth + 1); space(); if (peek() == ',') { i++; continue; } expect(']'); return; }
            } else if (c == '"') { string(); }
            else {
                int start = i;
                while (i < s.length() && "{}[],: \t\r\n".indexOf(s.charAt(i)) < 0) i++;
                String token = s.substring(start, i);
                if (!token.matches("true|false|null|-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")) throw error("Invalid JSON value");
            }
        }
        private String string() throws IOException {
            expect('"'); StringBuilder out = new StringBuilder();
            while (true) {
                char c = peek(); i++;
                if (c == '"') return out.toString();
                if (c < 0x20) throw error("Invalid JSON string");
                if (c != '\\') { out.append(c); continue; }
                char e = peek(); i++;
                switch (e) {
                    case '"': case '\\': case '/': out.append(e); break;
                    case 'b': out.append('\b'); break; case 'f': out.append('\f'); break;
                    case 'n': out.append('\n'); break; case 'r': out.append('\r'); break; case 't': out.append('\t'); break;
                    case 'u':
                        if (i + 4 > s.length() || !s.substring(i, i + 4).matches("[0-9A-Fa-f]{4}")) throw error("Invalid JSON escape");
                        out.append((char)Integer.parseInt(s.substring(i, i + 4), 16)); i += 4; break;
                    default: throw error("Invalid JSON escape");
                }
            }
        }
    }

    /** Python json.dumps(value, ensure_ascii=False, sort_keys=True) byte-for-byte, so revisions stay interchangeable. */
    public static byte[] canonical(Object value) {
        StringBuilder out = new StringBuilder(); write(out, value);
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }
    private static void write(StringBuilder out, Object value) {
        if (value == null || value == JSONObject.NULL) out.append("null");
        else if (value instanceof JSONObject) {
            JSONObject object = (JSONObject)value; List<String> keys = new ArrayList<>();
            for (Iterator<String> it = object.keys(); it.hasNext();) keys.add(it.next());
            java.util.Collections.sort(keys);
            out.append('{');
            for (int k = 0; k < keys.size(); k++) {
                if (k > 0) out.append(", ");
                quote(out, keys.get(k)); out.append(": "); write(out, object.opt(keys.get(k)));
            }
            out.append('}');
        } else if (value instanceof JSONArray) {
            JSONArray array = (JSONArray)value; out.append('[');
            for (int k = 0; k < array.length(); k++) { if (k > 0) out.append(", "); write(out, array.opt(k)); }
            out.append(']');
        } else if (value instanceof String) quote(out, (String)value);
        else if (value instanceof Boolean) out.append(((Boolean)value) ? "true" : "false");
        else if (value instanceof Double || value instanceof Float) {
            double d = ((Number)value).doubleValue();
            out.append(d == Math.rint(d) && Math.abs(d) < 1e16 ? String.valueOf((long)d) + ".0" : String.valueOf(d));
        } else out.append(String.valueOf(value));
    }
    private static void quote(StringBuilder out, String value) {
        out.append('"');
        for (int k = 0; k < value.length(); k++) {
            char c = value.charAt(k);
            switch (c) {
                case '"': out.append("\\\""); break; case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n"); break; case '\r': out.append("\\r"); break; case '\t': out.append("\\t"); break;
                case '\b': out.append("\\b"); break; case '\f': out.append("\\f"); break;
                default:
                    if (c < 0x20) out.append(String.format(Locale.ROOT, "\\u%04x", (int)c)); else out.append(c);
            }
        }
        out.append('"');
    }
}
