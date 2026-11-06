package winterx.legacyboot;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * kelindi's iphone-1-emulator (GPL-2.0-or-later, https://github.com/kelindi/iphone-1-emulator), as served by
 * https://2007.mobile at commit da5e9cc. Nothing of it ships in this package: each file is downloaded on first use
 * and must match the hash pinned here. Its worker then downloads Apple's iPhone OS 1.0 itself, also hash-checked.
 */
final class Engine {
    static final String SOURCE = "https://2007.mobile/";
    static final Map<String, String> FILES;
    static {
        String[] pins = {
            "emu-worker.js", "9fd5274088b29ab076b288878c960205315423684a8487af4423e2e0c7206403",
            "dist/emu.js", "47207dc63ddffe1d328ffbf686e93be0d23662dd8d8f3888f9d4bb999b958b86",
            "dist/emu.wasm", "6c168674625059f974a11ef808bcf06185ddbb11a1ce553f9bd22f3bc29d52c6",
            "seed-jit.js", "fe9ff4333b0aea3e26ac2fb30aabec08536f600fc0b97b7e2a213f1c504b0da5",
            "jit/seed.wasm", "d9c661556ab17bb8433ed9b0c3ecfd52e2fcafe58221b4cb84a920e4976b3881",
            "jit/regions.json", "c9d097ee798b3536e98fffe2f11b6aa408567ecc3e0a88e9250726f0eb640da9",
            "jit/abi.json", "78842488106b0f8912201561e4dbebcd0e61a8beaa1976f8785cfa82247ea698",
            "assets.js", "57239124797b93f1ce026c797a9f83137de1750decbe68acb1c3484c27686c8d",
            "sha256.js", "88562060586dd595d47e0c70225eb09ce54a9678bdd35bebdf27a2d9b41c3ee0",
            "manifest.json", "b25f9b40b90b5bb5bfa2ecc27c440298cb1d1fd574992ebe9e9bd427779ecf3a",
        };
        Map<String, String> files = new HashMap<>();
        for (int i = 0; i < pins.length; i += 2) files.put(pins[i], pins[i + 1]);
        FILES = Collections.unmodifiableMap(files);
    }

    private final File folder;
    Engine(File folder) { this.folder = folder; }

    static final class Reply {
        final int status; final String type; final byte[] body;
        Reply(int status, String type, byte[] body) { this.status = status; this.type = type; this.body = body; }
    }

    /** The page, or an engine file (downloaded and checked the first time). */
    Reply reply(String path) {
        try {
            if (path.isEmpty() || path.equals("index.html")) return new Reply(200, "text/html; charset=utf-8", Page.HTML.getBytes(StandardCharsets.UTF_8));
            if (!FILES.containsKey(path)) return new Reply(404, "text/plain", new byte[0]);
            File file = fetch(path);
            byte[] body = path.equals("emu-worker.js") ? worker(file) : Files.readAllBytes(file.toPath());
            return new Reply(200, type(path), body);
        } catch (Exception failure) {
            return new Reply(502, "text/plain", String.valueOf(failure.getMessage()).getBytes(StandardCharsets.UTF_8));
        }
    }

    /** The cached copy, or a fresh download that matches its pin. */
    synchronized File fetch(String path) throws Exception {
        File file = new File(folder, path);
        if (file.isFile() && FILES.get(path).equals(sha256(file))) return file;
        file.getParentFile().mkdirs();
        File temporary = new File(file.getPath() + ".tmp");
        HttpURLConnection connection = (HttpURLConnection)new URL(SOURCE + path).openConnection();
        connection.setConnectTimeout(20000); connection.setReadTimeout(60000);
        try (InputStream in = connection.getInputStream(); FileOutputStream out = new FileOutputStream(temporary)) {
            byte[] buffer = new byte[65536];
            for (int n; (n = in.read(buffer)) > 0;) out.write(buffer, 0, n);
        } finally { connection.disconnect(); }
        if (!FILES.get(path).equals(sha256(temporary))) { temporary.delete(); throw new SecurityException("Engine file changed: " + path); }
        if (!temporary.renameTo(file)) throw new java.io.IOException("Couldn't save " + path);
        return file;
    }

    /**
     * The worker gives a restored phone 20 s of real time to wake. Inside Spring, and above all on an emulated Android
     * device, the guest runs far slower than in a desktop browser, so allow 3 minutes.
     */
    static final String WAKE = "const deadline = performance.now() + 20000;";
    private static byte[] worker(File file) throws java.io.IOException {
        String text = new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
        if (!text.contains(WAKE)) throw new java.io.IOException("Unexpected emulator worker");
        return text.replace(WAKE, "const deadline = performance.now() + 180000;").getBytes(StandardCharsets.UTF_8);
    }

    long size() {
        long total = 0;
        for (String path : FILES.keySet()) total += new File(folder, path).length();
        return total;
    }

    void delete() { for (String path : FILES.keySet()) new File(folder, path).delete(); }

    private static String type(String path) {
        if (path.endsWith(".js")) return "text/javascript; charset=utf-8";
        if (path.endsWith(".wasm")) return "application/wasm";
        if (path.endsWith(".json")) return "application/json";
        return "application/octet-stream";
    }

    static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (FileInputStream in = new FileInputStream(file)) {
            byte[] buffer = new byte[65536];
            for (int n; (n = in.read(buffer)) > 0;) digest.update(buffer, 0, n);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format("%02x", b));
        return hex.toString();
    }
}
