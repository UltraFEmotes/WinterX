package winterx.snowy;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import E1.T6;
import E1.V6;
import E1.W6;
import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import org.json.JSONObject;
import sun.misc.Unsafe;

/** Real user-pack bytes and native bitmap/import code, with an isolated application root. */
public final class IconPackArchiveCheck {
    static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
    static E1.a app(String id) throws Exception {
        Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true);
        E1.a app = (E1.a)((Unsafe)field.get(null)).allocateInstance(E1.a.class);
        field = E1.a.class.getDeclaredField("a"); field.setAccessible(true); field.set(app, id);
        field = E1.a.class.getDeclaredField("c"); field.setAccessible(true); field.set(app, "spring-icon/" + id);
        return app;
    }
    static int pixel(Bitmap image, int x, int y) {
        int[] value = new int[1]; image.getPixels(value, 0, 1, x, y, 1, 1); return value[0];
    }
    public static void main(String[] args) throws Exception {
        File files = new File(System.getProperty("ruby.test.dir")), ruby = new File(files, "ruby");
        File inbox = new File(ruby, "snowyhome/inbox/fixture.zip");
        byte[] archive = Files.readAllBytes(inbox.toPath());
        File pages = new File(files, "ios6_pages.json"); Files.writeString(pages.toPath(), "keep current pages");
        File sparse = new File(ruby, "freeme-slots-v1.json"); Files.writeString(sparse.toPath(), "keep sparse cells");
        new File(ruby, "snowyhome.enabled").createNewFile();
        String token = IconPack.sha("fixture.zip".getBytes(StandardCharsets.UTF_8));
        check(PackImport.inbox().containsKey(token), "regular pack missing from native inbox");
        check(args[0].equals(PackImport.install(token)), "native import returned wrong revision");
        File folder = SnowyHome.folder(), packs = new File(folder, "packs"), preferences = new File(folder, "preferences.json");
        check(!preferences.exists(), "import selected a pack automatically");
        IconPack pack = IconPack.load(packs, args[0]); check(pack != null, "native pack loader refused archive");
        JSONObject manifest = new JSONObject(new String(Files.readAllBytes(new File(packs, args[0] + "/manifest.json").toPath()), StandardCharsets.UTF_8));
        JSONObject mappings = manifest.getJSONObject("icons");
        T6 page = SnowySettings.page("winterx-layout-p/snowy/packs"); int listed = 0;
        for (Object section : page.c) for (Object row : ((W6)section).c)
            if (("winterx-layout-a/snowy/pack/" + args[0]).equals(((V6)row).a)) listed++;
        check(listed == 1, "imported pack missing/duplicated in native picker");
        check(SnowySettings.action("winterx-layout-a/snowy/pack/" + args[0]), "fixture pack selection refused");
        int count = 0;
        for (Iterator<String> ids = mappings.keys(); ids.hasNext();) {
            String id = ids.next(); byte[] png = pack.icon(id); check(png != null, "native checksum/PNG check refused " + id);
            Bitmap decoded = BitmapFactory.decodeByteArray(png, 0, png.length);
            check(decoded != null && decoded.getWidth() == decoded.getHeight(), "PNG did not decode: " + id);
            Bitmap original = Bitmap.createBitmap(decoded.getWidth(), decoded.getHeight(), Bitmap.Config.ARGB_8888); original.eraseColor(0xffff00ff);
            E1.a model = app(id); Bitmap themed = SnowyHome.icon(model, original);
            check(themed != original && themed.getWidth() == original.getWidth() && themed.getHeight() == original.getHeight(), "native bitmap copy/geometry failed: " + id);
            int end = decoded.getWidth() - 1, center = decoded.getWidth() / 2;
            for (int[] point : new int[][]{{0, 0}, {center, center}, {end, end}})
                check(pixel(themed, point[0], point[1]) == pixel(decoded, point[0], point[1]), "native artwork pixel changed: " + id);
            Map<String, Bitmap> artwork = new HashMap<>(); artwork.put("spring-icon/" + id, original);
            check(I1.h0.c(model, null, null, artwork) == themed, "actual packaged renderer missed mapped icon: " + id);
            check(!original.isRecycled() && pixel(original, center, center) == 0xffff00ff, "shared original changed: " + id);
            decoded.recycle(); count++;
        }
        Bitmap stock = Bitmap.createBitmap(114, 114, Bitmap.Config.ARGB_8888);
        check(SnowyHome.icon(app("folder:1"), stock) == stock, "native folder replaced");
        check(SnowyHome.icon(app("unmapped-native-icon"), stock) == stock, "unmapped icon replaced");
        byte[] saved = Files.readAllBytes(preferences.toPath());
        check(args[0].equals(PackImport.install(token)) && Arrays.equals(saved, Files.readAllBytes(preferences.toPath())), "reimport changed selected preferences");
        new File(ruby, "safe-mode.enabled").createNewFile();
        check(SnowyHome.icon(app(mappings.keys().next()), stock) == stock, "Safe Mode retained pack rendering");
        check(Arrays.equals(archive, Files.readAllBytes(inbox.toPath())) && Files.readString(pages.toPath()).equals("keep current pages") &&
            Files.readString(sparse.toPath()).equals("keep sparse cells"), "import/render changed ZIP or native layout fixture");
        System.out.println(pack.name + ": " + count + " mapped PNGs passed native import/picker/checksums/decode/renderer/pixels and preservation at " + files.getName() + " (isolated; not live UI)");
    }
}
