package winterx.snowy;

import android.graphics.Bitmap;
import E1.T6;
import E1.V6;
import E1.W6;
import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import sun.misc.Unsafe;
import winterx.layout.LayoutSettings;

public final class SnowyHomeCheck {
    private static final String PAGE = "winterx-layout-p/snowy/", ACTION = "winterx-layout-a/snowy/";
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
    static E1.a app(String id) throws Exception {
        Field unsafeField = Unsafe.class.getDeclaredField("theUnsafe"); unsafeField.setAccessible(true);
        E1.a app = (E1.a)((Unsafe)unsafeField.get(null)).allocateInstance(E1.a.class);
        Field field = E1.a.class.getDeclaredField("a"); field.setAccessible(true); field.set(app, id);
        field = E1.a.class.getDeclaredField("c"); field.setAccessible(true); field.set(app, "spring-icon/" + id);
        return app;
    }
    static V6 row(T6 page, String id) {
        if (page == null) return null;
        for (Object section : page.c) for (Object row : ((W6)section).c) if (((V6)row).a.equals(id)) return (V6)row;
        return null;
    }
    static int pixel(Bitmap image, int x, int y) { int[] p = new int[1]; image.getPixels(p, 0, 1, x, y, 1, 1); return p[0]; }
    static boolean near(int actual, int expected) {
        // Canvas stores premultiplied colours: round-tripping partial alpha can lose 1–2 RGB levels.
        if ((actual >>> 24) != (expected >>> 24)) return false;
        for (int shift : new int[]{0, 8, 16}) if (Math.abs((actual >> shift & 255) - (expected >> shift & 255)) > 2) return false;
        return true;
    }
    public static void main(String[] args) throws Exception {
        File files = new File(System.getProperty("ruby.test.dir")), ruby = new File(files, "ruby"), folder = new File(ruby, "snowyhome");
        File pages = new File(files, "ios6_pages.json"); Files.write(pages.toPath(), "preserved layout".getBytes(StandardCharsets.UTF_8));
        File sparse = new File(ruby, "freeme-slots-v1.json"); Files.write(sparse.toPath(), "preserved cells".getBytes(StandardCharsets.UTF_8));
        Bitmap original = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888); original.eraseColor(0xffff0000);
        E1.a mail = app("mail"); check(SnowyHome.icon(mail, original) == original, "uninstalled icon changed");
        check(LayoutSettings.page(PAGE + "main") == null, "uninstalled Settings page visible");
        File marker = new File(ruby, "snowyhome.enabled"); marker.createNewFile();
        check(row(LayoutSettings.page(PAGE + "packs"), PAGE + "import") != null, "native import row missing");
        String token = IconPack.sha("test.zip".getBytes(StandardCharsets.UTF_8));
        File revisionDir = new File(folder, "packs/" + args[0]); revisionDir.mkdirs();
        File existing = new File(revisionDir, "keep.txt"); Files.writeString(existing.toPath(), "existing invalid revision");
        try { PackImport.install(token); throw new AssertionError("invalid existing revision overwritten"); }
        catch (java.io.IOException expected) {}
        check(Files.readString(existing.toPath()).equals("existing invalid revision"), "existing revision changed on refusal");
        Files.delete(existing.toPath()); Files.delete(revisionDir.toPath());
        byte[] inboxBytes = Files.readAllBytes(new File(folder, "inbox/test.zip").toPath());
        String imported = PackImport.install(token);
        check(imported.equals(args[0]) && PackImport.install(token).equals(imported), "import/idempotence failed");
        check(!new File(folder, "preferences.json").exists(), "import selected or rewrote preferences");
        check(new File(folder, "inbox/test.zip").isFile(), "import deleted source archive");
        try { PackImport.install(String.join("", java.util.Collections.nCopies(64, "0"))); throw new AssertionError("missing inbox pack imported"); }
        catch (java.io.IOException expected) {}
        check(SnowyHome.icon(mail, original) == original, "stock preference changed icon");
        check(LayoutSettings.page(PAGE + "main") != null, "native Settings model missing");
        ArrayList<V6> rows = new ArrayList<>(); LayoutSettings.rows(rows);
        check(rows.stream().anyMatch(v -> v.a.equals(PAGE + "main")), "native root row missing");
        check(row(LayoutSettings.page(PAGE + "packs"), ACTION + "pack/" + args[0]) != null, "verified pack not listed");
        check(!SnowySettings.action(ACTION + "pack/" + String.join("", java.util.Collections.nCopies(64, "0"))), "missing pack selected");
        check(SnowySettings.action(ACTION + "pack/" + args[0]), "pack selection failed");
        byte[] selectedPrefs = Files.readAllBytes(new File(folder, "preferences.json").toPath());
        check(PackImport.install(token).equals(imported), "selected revision reimport failed");
        check(java.util.Arrays.equals(selectedPrefs, Files.readAllBytes(new File(folder, "preferences.json").toPath())), "reimport rewrote selected preferences");
        check(java.util.Arrays.equals(inboxBytes, Files.readAllBytes(new File(folder, "inbox/test.zip").toPath())), "import rewrote inbox ZIP");
        Bitmap themed = SnowyHome.icon(mail, original);
        if (args.length > 1 && Boolean.parseBoolean(args[1])) {
            java.lang.reflect.Method resolver = I1.h0.class.getMethod("c", E1.a.class, E1.q6.class, I1.I0.class, Map.class);
            check(I1.h0.class.getMethod("winterxStockIcon", E1.a.class, E1.q6.class, I1.I0.class, Map.class).getReturnType() == Bitmap.class,
                "packaged stock fallback missing");
            Map<String, Bitmap> art = new HashMap<>(); art.put("spring-icon/mail", original);
            check(resolver.invoke(null, mail, null, null, art) == themed, "actual packaged icon resolver missed SnowyHome");
            Field unsafeField = Unsafe.class.getDeclaredField("theUnsafe"); unsafeField.setAccessible(true);
            Unsafe unsafe = (Unsafe)unsafeField.get(null);
            for (String controllerName : new String[]{"E1.B0", "E1.b4"}) {
                Class<?> controller = Class.forName(controllerName); Object instance = unsafe.allocateInstance(controller);
                T6 nativePage = (T6)controller.getMethod("a", String.class).invoke(instance, PAGE + "main");
                check(nativePage != null && "SnowyHome".equals(nativePage.b), "actual native controller missed SnowyHome");
            }
        }
        check(themed != original && themed.getWidth() == 64 && themed.getHeight() == 64, "pack dimensions changed");
        check(near(pixel(themed, 32, 32), 0xa01450c8), "replacement colour/alpha incorrect: " + Integer.toHexString(pixel(themed, 32, 32)));
        check(SnowyHome.icon(mail, original) == themed, "private icon cache missed");
        check(SnowyHome.icon(app("phone"), original) == original, "unmapped icon changed");
        check(SnowyHome.icon(app("folder:1"), original) == original, "native folder artwork changed");
        check(pixel(original, 32, 32) == 0xffff0000 && !original.isRecycled(), "shared source modified/recycled");
        check(SnowySettings.action(ACTION + "corners/5"), "circle selection failed");
        Bitmap rounded = SnowyHome.icon(mail, original);
        check((pixel(rounded, 0, 0) >>> 24) == 0 && near(pixel(rounded, 32, 32), 0xa01450c8), "round mask affected centre or missed corner");
        check(SnowySettings.action(ACTION + "labels") && SnowyHome.hiddenLabels(), "label preference not live");
        if (args.length > 1 && Boolean.parseBoolean(args[1])) {
            // Hidden labels must exit before Spring touches its stock font/profile models.
            I1.h0.class.getMethod("G", android.graphics.Canvas.class, I1.I0.class, E1.i6.class,
                String.class, int.class, int.class, boolean.class).invoke(null, null, null, null, "fixture label", 0, 0, false);
        }
        check(SnowySettings.action(ACTION + "badge/2"), "badge preference failed");
        Bitmap badge = Bitmap.createBitmap(3, 1, Bitmap.Config.ARGB_8888);
        badge.setPixels(new int[]{0x80ff0000, 0xffffffff, 0}, 0, 3, 0, 0, 3, 1);
        Map<String, Object> stock = new HashMap<>(); String key = "ios4/chrome/badge_bg.png";
        stock.put(key, badge); stock.put("ios4/chrome/badge_exclamation.png", badge); stock.put("wallpaper", original);
        Map view = SnowyHome.artwork(stock); Bitmap tinted = (Bitmap)view.get(key);
        check(tinted != badge && near(pixel(tinted, 0, 0), 0x80007aff), "badge RGB/alpha incorrect");
        check(pixel(tinted, 1, 0) == 0xffffffff && pixel(tinted, 2, 0) == 0, "badge glyph or transparent margin tinted");
        check(stock.get(key) == badge && pixel(badge, 0, 0) == 0x80ff0000, "shared badge changed");
        check(new HashMap(view).get(key) == tinted && view.get("wallpaper") == original, "map view semantics incorrect");
        check(SnowySettings.action(ACTION + "pack/stock") && SnowySettings.action(ACTION + "corners/0"), "stock reset failed");
        File image = new File(folder, "packs/" + args[0] + "/icons/mail.png"); Files.write(image.toPath(), new byte[]{1, 2, 3});
        try { PackImport.install(token); throw new AssertionError("tampered existing icon replaced on import"); }
        catch (java.io.IOException expected) {}
        check(java.util.Arrays.equals(Files.readAllBytes(image.toPath()), new byte[]{1, 2, 3}), "tampered revision overwritten");
        check(SnowySettings.action(ACTION + "pack/" + args[0]), "manifest selection failed");
        check(SnowyHome.icon(mail, original) == original, "tampered icon did not fall back");
        File preferences = new File(folder, "preferences.json"); byte[] saved = Files.readAllBytes(preferences.toPath());
        File safe = new File(ruby, "safe-mode.enabled"); safe.createNewFile();
        check(SnowyHome.icon(mail, original) == original && SnowyHome.artwork(stock) == stock && !SnowyHome.hiddenLabels(), "Safe Mode did not restore stock");
        check(view.get(key) == badge, "retained artwork view ignored Safe Mode");
        check(LayoutSettings.page(PAGE + "main") == null && !SnowySettings.action(ACTION + "labels"), "Safe Mode allowed preferences");
        try { PackImport.install(token); throw new AssertionError("Safe Mode imported pack"); } catch (java.io.IOException expected) {}
        marker.delete(); check(java.util.Arrays.equals(saved, Files.readAllBytes(preferences.toPath())), "removal erased preferences");
        check(!themed.isRecycled(), "cached displayed bitmap recycled after preference change");
        check(new String(Files.readAllBytes(pages.toPath()), StandardCharsets.UTF_8).equals("preserved layout"), "saved pages modified");
        check(new String(Files.readAllBytes(sparse.toPath()), StandardCharsets.UTF_8).equals("preserved cells"), "sparse cells modified");
        safe.delete(); marker.createNewFile();
        File packs = new File(folder, "packs"), savedPacks = new File(folder, "saved-packs");
        Files.move(packs.toPath(), savedPacks.toPath()); Files.createSymbolicLink(packs.toPath(), savedPacks.toPath());
        check(!SnowySettings.action(ACTION + "pack/" + args[0]), "linked packs directory selected");
        try { PackImport.install(token); throw new AssertionError("linked packs imported"); } catch (java.io.IOException expected) {}
        Files.delete(packs.toPath()); Files.move(savedPacks.toPath(), packs.toPath());
        File inbox = new File(folder, "inbox"), savedInbox = new File(folder, "saved-inbox");
        Files.move(inbox.toPath(), savedInbox.toPath()); Files.createSymbolicLink(inbox.toPath(), savedInbox.toPath());
        check(PackImport.inbox().isEmpty(), "linked inbox followed");
        try { PackImport.install(token); throw new AssertionError("linked inbox imported"); } catch (java.io.IOException expected) {}
        Files.delete(inbox.toPath()); Files.move(savedInbox.toPath(), inbox.toPath());
        File savedRuby = new File(files, "saved-ruby"); Files.move(ruby.toPath(), savedRuby.toPath());
        Files.createSymbolicLink(ruby.toPath(), savedRuby.toPath());
        check(!SnowyHome.enabled() && SnowyHome.icon(mail, original) == original && !SnowySettings.action(ACTION + "labels"), "linked ruby directory enabled appearance");
        check(java.util.Arrays.equals(saved, Files.readAllBytes(new File(savedRuby, "snowyhome/preferences.json").toPath())), "linked ruby changed preferences");
        System.out.println("SnowyHome: native Settings/import, verified icons, alpha/dimensions/corners/labels, immutable badges, tamper/Safe Mode and child-link refusal passed at " + files.getName());
    }
}
