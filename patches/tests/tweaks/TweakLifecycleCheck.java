package winterx.tweaks;

import com.guille.spring.sapp.QuickJs;
import java.io.File;
import java.nio.file.Files;
import java.util.function.BooleanSupplier;
import org.json.JSONObject;

/** Exercises real TweakHost loading/storage/cleanup against the JVM QuickJs spy. */
public final class TweakLifecycleCheck {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static void await(BooleanSupplier condition, String why) throws Exception {
        long end = System.nanoTime() + 3000000000L;
        while (!condition.getAsBoolean() && System.nanoTime() < end) Thread.sleep(10);
        check(condition.getAsBoolean(), why);
    }
    static File install(String id, String script, boolean corrupt) throws Exception {
        File dir = new File(System.getProperty("ruby.test.dir"), "winterx-tweaks/" + id);
        new File(dir, "code").mkdirs();
        JSONObject manifest = new JSONObject();
        manifest.put("format", "winterx.springys/2"); manifest.put("type", "tweak");
        manifest.put("id", id); manifest.put("entry", "tweak/main.js");
        TweakHost.writeText(new File(dir, "manifest.json"), manifest.toString());
        TweakHost.writeText(new File(dir, "manifest.sha256"), TweakHost.digestOf(new File(dir, "manifest.json")) + "\n");
        TweakHost.writeText(new File(dir, "code/main.js"), script);
        TweakHost.writeText(new File(dir, "sha256"), corrupt ? "00\n" : TweakHost.digestOf(new File(dir, "code/main.js")) + "\n");
        new File(dir, "enabled").createNewFile();
        return dir;
    }
    public static void main(String[] args) throws Exception {
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby"); ruby.mkdirs();
        File good = install("me.example.good", "TEST_STORAGE", false);
        File broken = install("me.example.broken", "TEST_THROW", false);
        File corrupt = install("me.example.corrupt", "should not execute", true);
        File safe = new File(ruby, "safe-mode.enabled"); safe.createNewFile();
        TweakHost.start(null);
        check(QuickJs.CREATED.isEmpty(), "Safe Mode constructed a JS context");
        safe.delete();
        TweakHost.start(null);
        try { await(() -> TweakHost.loaded("me.example.good"), "good tweak did not load"); }
        catch (AssertionError failure) {
            throw new AssertionError("good tweak did not load: " + TweakHost.readText(new File(good, "last-error.txt")), failure);
        }
        await(() -> new File(broken, "last-error.txt").isFile(), "script error not recorded");
        await(() -> new File(corrupt, "last-error.txt").isFile(), "hash failure not recorded");
        check(!TweakHost.loaded("me.example.broken") && !TweakHost.loaded("me.example.corrupt"), "failed tweak active");
        check(QuickJs.CREATED.size() == 2, "corrupt code constructed context");
        QuickJs context = null;
        for (QuickJs value : QuickJs.CREATED) {
            if (value.filename.startsWith("me.example.good/")) context = value;
            else check(value.closed, "failed context leaked");
        }
        final QuickJs running = context;
        check(running != null && running.owner.startsWith("WinterX-tweak-") && running.ranJobs, "worker/jobs invalid");
        check("private data".equals(TweakHost.readText(new File(good, "data/example.txt"))), "host storage missing");
        check(TweakHost.readText(new File(good, "state.json")).contains("3"), "state not persisted");
        TweakHost.tapped("winterx-tw-r/me.example.good/main/run");
        await(() -> "settingsTap".equals(running.event), "native event not dispatched");
        File outside = new File(System.getProperty("ruby.test.dir"), "outside.txt");
        Files.createSymbolicLink(new File(good, "data/linked.txt").toPath(), outside.toPath());
        try { TweakHost.file("me.example.good", "data/linked.txt"); throw new AssertionError("symlink accepted"); }
        catch (java.io.IOException expected) {}
        // Replacing a revision must stop old code before it can receive new Settings callbacks.
        TweakHost.writeText(new File(good, "sha256"), "1111111111111111111111111111111111111111111111111111111111111111\n");
        await(() -> running.closed, "updated context not closed");
        check(!TweakHost.loaded("me.example.good"), "old revision still active");
        System.out.println("Tweak lifecycle: startup gate, worker affinity, host storage, integrity, failure isolation, jobs and update cleanup passed (JNI spy)");
    }
}
