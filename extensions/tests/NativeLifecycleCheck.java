import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import org.json.JSONArray;
import org.json.JSONObject;
import winterx.extension.NativeRuntime;

/** Direct loader fault fixtures, distinct from valid .springys envelope tests. */
public final class NativeLifecycleCheck {
    private static Path root;
    private static byte[] jar;
    private static String hash(byte[] value) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(value)) result.append(String.format("%02x", b & 255));
        return result.toString();
    }
    private static Path add(String id, String... requires) throws Exception {
        Path folder = root.resolve("winterx-tweaks/" + id);
        Files.createDirectories(folder.resolve("code"));
        Files.write(folder.resolve("code/classes.jar"), jar);
        JSONObject manifest = new JSONObject().put("format", "winterx.springys/3").put("type", "tweak")
            .put("runtime", "java").put("api", "winterx.native/1").put("id", id).put("entry", "me.fixture.Probe")
            .put("exports", new JSONArray(Arrays.asList("fixture.value"))).put("requires", new JSONArray(Arrays.asList(requires)))
            .put("files", new JSONObject().put("code/classes.jar", hash(jar)));
        byte[] bytes = manifest.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
        Files.write(folder.resolve("manifest.json"), bytes);
        Files.writeString(folder.resolve("manifest.sha256"), hash(bytes));
        Files.writeString(folder.resolve("enabled"), "enabled\n");
        return folder;
    }
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    public static void main(String[] arguments) throws Exception {
        root = Path.of(arguments[0]); jar = Files.readAllBytes(Path.of(arguments[1]));
        String scenario = arguments[2];
        Files.createDirectories(root.resolve("ruby"));
        Path layout = root.resolve("ios6_pages.json"); Files.writeString(layout, "preserved user layout");
        byte[] before = Files.readAllBytes(layout);
        if ("dependencies".equals(scenario)) {
            Path child = add("me.fixture.a-child", "me.fixture.z-base"), base = add("me.fixture.z-base");
            NativeRuntime.initialize(root.toFile());
            check(NativeRuntime.manifests().size() == 2, "topological start failed");
            check(Files.exists(child.resolve("data/started.txt")), "dependent code did not execute");
            Files.delete(base.resolve("enabled"));
            check(!NativeRuntime.enabled("me.fixture.a-child"), "dependent survived revoked dependency");
            long deadline = System.nanoTime() + 3_000_000_000L;
            while (!Files.exists(child.resolve("data/stopped.txt")) && System.nanoTime() < deadline) Thread.sleep(20);
            check(Files.exists(child.resolve("data/stopped.txt")), "dependent stop was not called");
        } else if ("missing".equals(scenario) || "cycle".equals(scenario)) {
            Path child = add("me.fixture.a-child", "me.fixture.z-base");
            if ("cycle".equals(scenario)) add("me.fixture.z-base", "me.fixture.a-child");
            NativeRuntime.initialize(root.toFile());
            check(NativeRuntime.manifests().isEmpty(), "invalid dependency graph executed code");
            check(!Files.exists(child.resolve("data/started.txt")), "invalid dependency started");
        } else if ("safe".equals(scenario)) {
            Path good = add("me.fixture.z-good");
            Files.writeString(root.resolve("ruby/safe-mode.enabled"), "1");
            NativeRuntime.initialize(root.toFile());
            check(NativeRuntime.manifests().isEmpty() && !Files.exists(good.resolve("data/started.txt")), "Safe Mode executed package code");
        } else {
            String badId = "me.fixture.a-" + scenario;
            Path bad = add(badId); add("me.fixture.z-good");
            if ("integrity".equals(scenario)) Files.writeString(bad.resolve("code/classes.jar"), "tampered");
            NativeRuntime.initialize(root.toFile());
            Object answer = NativeRuntime.dispatch("fixture.value", new Object[0], Integer.valueOf(99), "first", false, Integer.class);
            check(Integer.valueOf(7).equals(answer), "faulty package blocked the healthy provider");
            check(!NativeRuntime.enabled(badId) && NativeRuntime.enabled("me.fixture.z-good"), "package fault was not isolated");
            check(Files.isRegularFile(bad.resolve("last-error.txt")), "package fault lacked a diagnostic");
        }
        check(Arrays.equals(before, Files.readAllBytes(layout)), "loader changed saved layout");
        System.out.println("Native lifecycle passed: " + scenario);
    }
}
