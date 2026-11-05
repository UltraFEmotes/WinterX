package winterx.ssh;

import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import sun.misc.Unsafe;
import org.json.JSONObject;

/** Actual packaged J1.P.b single-archive file semantics. No launcher, JS runtime or inbox scan. */
public final class NativeArchiveCheck {
    static void check(boolean ok, String reason) { if (!ok) throw new AssertionError(reason); }
    static void set(Object target, String name, Object value) throws Exception { Field field = target.getClass().getDeclaredField(name); field.setAccessible(true); field.set(target, value); }
    public static void main(String[] args) throws Exception {
        File root = new File(System.getProperty("ruby.test.dir")).getCanonicalFile();
        E1.t.j = Boolean.parseBoolean(args[0]);
        File pages = new File(root, "ios4_pages.json"), slots = new File(root, "freeme-slots-v1.json");
        Files.writeString(pages.toPath(), "protected native pages"); Files.writeString(slots.toPath(), "protected sparse cells");
        byte[] oldPages = Files.readAllBytes(pages.toPath()), oldSlots = Files.readAllBytes(slots.toPath());
        String id = "me.example.nativearchivefixture";
        JSONObject manifest = new JSONObject().put("id", id).put("name", "Native archive fixture").put("version", "1.0").put("build", 1)
            .put("minSpring", 8).put("genre", "Utilities").put("statusBarStyle", "blackOpaque").put("tallScreen", true)
            .put("permissions", new JSONObject().put("network", new org.json.JSONArray()));
        File archive = new File(root, "fixture.sapp");
        try (ZipOutputStream out = new ZipOutputStream(Files.newOutputStream(archive.toPath()))) {
            for (String name : List.of("app.json", "main.js")) {
                out.putNextEntry(new ZipEntry(name)); out.write((name.equals("app.json") ? manifest.toString() : "// fixture; never executed\n").getBytes(StandardCharsets.UTF_8)); out.closeEntry();
            }
            android.graphics.Bitmap icon = android.graphics.Bitmap.createBitmap(114, 114, android.graphics.Bitmap.Config.ARGB_8888);
            icon.eraseColor(0xff226699); out.putNextEntry(new ZipEntry("icon.png"));
            check(icon.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, out), "fixture icon encoding failed"); out.closeEntry();
            android.graphics.Bitmap launch = android.graphics.Bitmap.createBitmap(640, 960, android.graphics.Bitmap.Config.ARGB_8888); launch.eraseColor(0xff111111);
            out.putNextEntry(new ZipEntry("launch.png"));
            check(launch.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, out), "fixture launch encoding failed"); out.closeEntry();
        }
        byte[] source = Files.readAllBytes(archive.toPath());
        Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true); Unsafe unsafe = (Unsafe)field.get(null);
        J1.P store = (J1.P)unsafe.allocateInstance(J1.P.class); File code = new File(root, "sapps"), data = new File(root, "sapps-data");
        set(store, "a", code); set(store, "b", data);
        check(!new File(code, id).exists() && !new File(data, id).exists(), "native fixture destination already exists");
        J1.x callback = (J1.x)unsafe.allocateInstance(J1.x.class); set(callback, "a", 2); set(callback, "b", new J1.y());
        J1.N installed = store.b(archive, callback);
        File revision = new File(code, id + "/1");
        check(installed.a.a.equals(id) && installed.b.getCanonicalFile().equals(revision.getCanonicalFile()), "native installer returned wrong ID/build path");
        check(new File(revision, "app.json").isFile() && Files.readString(new File(revision, "main.js").toPath()).equals("// fixture; never executed\n"), "native archive contents not staged exactly");
        check(new File(data, id).isDirectory() && !new File(code, id + "/.staging").exists(), "native new-app data/build transaction did not finish");
        check(J1.y.icons == 1, "native installer did not call its icon adapter exactly once");
        check(Arrays.equals(source, Files.readAllBytes(archive.toPath())) && Arrays.equals(oldPages, Files.readAllBytes(pages.toPath())) && Arrays.equals(oldSlots, Files.readAllBytes(slots.toPath())), "native file import changed archive or unrelated layouts");
        System.out.println("Packaged native single-archive importer: exact new ID/build/data paths and source/layout preservation passed; disposable files only, no app opened or JS executed");
    }
}
