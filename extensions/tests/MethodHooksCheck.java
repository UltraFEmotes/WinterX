import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import org.json.JSONArray;
import org.json.JSONObject;
import winterx.extension.MethodHooks;
import winterx.extension.NativeRuntime;

/** Universal method hooks on real instrumented Spring classes, through real loaded tweak packages. */
public final class MethodHooksCheck {
    static Path root; static byte[] jar;
    static String hash(byte[] value) throws Exception {
        StringBuilder result = new StringBuilder();
        for (byte b : MessageDigest.getInstance("SHA-256").digest(value)) result.append(String.format("%02x", b & 255));
        return result.toString();
    }
    static Path add(String id) throws Exception {
        Path folder = root.resolve("winterx-tweaks/" + id);
        Files.createDirectories(folder.resolve("code"));
        Files.write(folder.resolve("code/classes.jar"), jar);
        JSONObject manifest = new JSONObject().put("format", "winterx.springys/3").put("type", "tweak").put("runtime", "java")
            .put("api", "winterx.native/1").put("id", id).put("entry", "me.fixture.hooks.HookProbe")
            .put("exports", new JSONArray(Arrays.asList("fixture.none"))).put("files", new JSONObject().put("code/classes.jar", hash(jar)));
        byte[] bytes = manifest.toString().getBytes("UTF-8");
        Files.write(folder.resolve("manifest.json"), bytes);
        Files.writeString(folder.resolve("manifest.sha256"), hash(bytes));
        Files.writeString(folder.resolve("enabled"), "enabled\n");
        return folder;
    }
    static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    static Method method(String owner, String name, Class<?>... types) throws Exception {
        Method method = Class.forName(owner).getDeclaredMethod(name, types); method.setAccessible(true); return method;
    }
    static Object invoke(Method method, Object... args) throws Throwable {
        try { return method.invoke(null, args); } catch (InvocationTargetException thrown) { throw thrown.getCause(); }
    }

    public static void main(String[] arguments) throws Throwable {
        root = Path.of(arguments[0]); jar = Files.readAllBytes(Path.of(arguments[1]));
        Files.createDirectories(root.resolve("ruby"));
        Method digit = method("org.mozilla.javascript.TokenStream", "isDigit", int.class);
        Method alpha = method("org.mozilla.javascript.TokenStream", "isAlpha", int.class);
        Method hex = method("org.mozilla.javascript.TokenStream", "isHexDigit", int.class);
        check(MethodHooks.hookable("org.mozilla.javascript.TokenStream.isDigit(I)Z"), "dotted signature not accepted");
        if ("safe".equals(arguments[2])) {
            Files.writeString(root.resolve("ruby/safe-mode.enabled"), "1");
            add("me.fixture.a-digits");
            NativeRuntime.initialize(root.toFile());
            check(MethodHooks.table == null, "hooks registered in Safe Mode");
            check(!(Boolean)invoke(digit, (int)'x'), "Safe Mode still ran a hook");
            System.out.println("Method hooks passed: Safe Mode registers nothing");
            return;
        }
        check(MethodHooks.table == null && (Boolean)invoke(digit, (int)'7') && !(Boolean)invoke(digit, (int)'x'), "instrumented original changed before hooking");
        for (String id : new String[]{"a-digits", "b-more", "c-bad", "d-args"}) add("me.fixture." + id);
        NativeRuntime.initialize(root.toFile());
        check(MethodHooks.table != null, "no hooks registered");
        check((Boolean)invoke(digit, (int)'5') && !(Boolean)invoke(digit, (int)'q'), "chain did not reach the original");
        check((Boolean)invoke(digit, (int)'x'), "first hook did not replace the result");
        check((Boolean)invoke(digit, (int)'y'), "second hook in the chain did not run");
        check((Boolean)invoke(alpha, (int)'1'), "argument change did not reach the original");
        check((Boolean)invoke(hex, (int)'g') && !(Boolean)invoke(hex, (int)'f'), "after-hook did not change the result");
        // Called directly, as Spring does (reflection would rewrap Kotlin's trimmed NPE on desktop Java).
        a2.g.e(null, "skip");
        boolean threw = false;
        try { a2.g.e(null, "value"); } catch (NullPointerException expected) { threw = true; }
        check(threw, "original exception was not preserved");
        // A failing hook switches only its own tweak off; the call still completes through the original.
        check(!(Boolean)invoke(digit, (int)'z'), "failed hook changed the result");
        check(!NativeRuntime.enabled("me.fixture.c-bad") && Files.isRegularFile(root.resolve("winterx-tweaks/me.fixture.c-bad/last-error.txt")), "failing tweak not disabled");
        check((Boolean)invoke(digit, (int)'x') && (Boolean)invoke(digit, (int)'y'), "other tweaks lost their hooks");
        // Removing a tweak turns its hooks off without a restart.
        Files.delete(root.resolve("winterx-tweaks/me.fixture.b-more/enabled"));
        Thread.sleep(1100);
        check(!(Boolean)invoke(digit, (int)'y') && (Boolean)invoke(digit, (int)'x'), "removed tweak's hook still ran");
        long start = System.nanoTime();
        for (int i = 0; i < 200000; i++) invoke(digit, (int)'5');
        System.out.printf("Method hooks passed: chain, replace, skip, args, after, original exceptions, failure isolation, removal (%.1f µs per hooked call)%n",
            (System.nanoTime() - start) / 200000 / 1000.0);
    }
}
