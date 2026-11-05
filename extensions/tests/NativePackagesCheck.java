import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import sun.misc.Unsafe;
import winterx.extension.NativeHooks;
import winterx.extension.NativeRuntime;

/** Real core-only APK classes + packages installed through the Ruby registry; no launcher or live data. */
public final class NativePackagesCheck {
    private static final Unsafe UNSAFE;
    static { try { Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true); UNSAFE = (Unsafe)field.get(null); } catch (Exception failure) { throw new ExceptionInInitializerError(failure); } }
    static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
    static <T> T allocate(Class<T> type) throws Exception { return type.cast(UNSAFE.allocateInstance(type)); }
    static void set(Object target, String name, Object value) throws Exception { Field field = target.getClass().getDeclaredField(name); field.setAccessible(true); field.set(target, value); }
    static float[] matrix(Canvas canvas) { float[] values = new float[9]; canvas.getMatrix().getValues(values); return values; }
    private static boolean row(E1.T6 page, String id) {
        for (Object section : page.c) for (Object entry : ((E1.W6)section).c) if (id.equals(((E1.V6)entry).a)) return true;
        return false;
    }
    public static void main(String[] args) throws Exception {
        boolean installed = Boolean.parseBoolean(args[0]); E1.t.j = Boolean.parseBoolean(args[1]);
        File root = new File(System.getProperty("ruby.test.dir")), ruby = new File(root, "ruby"); ruby.mkdirs();
        Files.writeString(new File(ruby, "animaper.mode").toPath(), "orbit\n");
        // Old marker files alone are not executable packages in the new engine.
        for (String name : List.of("animaper.enabled", "snowyhome.enabled", "freeme.enabled", "dockin.enabled", "coloredbar.enabled", "ssh.enabled", "messageplus.enabled"))
            Files.writeString(new File(ruby, name).toPath(), "legacy marker\n");
        File savedLayout = new File(root, "ios6_pages.json"); Files.writeString(savedLayout.toPath(), "protected native layout");
        byte[] before = Files.readAllBytes(savedLayout.toPath());
        NativeRuntime.initialize(root);
        check(NativeRuntime.manifests().size() == (installed ? 7 : 0), "wrong independently installed package count");
        for (String name : List.of("winterx.animaper.Animaper", "winterx.ssh.SshServerEngine", "winterx.layout.FreeMe", "winterx.coloredbar.ColoredBar")) {
            try { Class.forName(name, false, NativeRuntime.class.getClassLoader()); throw new AssertionError("tweak is bundled in the engine: " + name); }
            catch (ClassNotFoundException expected) {}
        }
        List<E1.T6> roots = new ArrayList<>(); roots.add(E1.Z3.c);
        for (Object value : E1.Z3.s) if ("root".equals(((E1.T6)value).a)) roots.add((E1.T6)value);
        for (E1.T6 stock : roots) {
            E1.T6 decorated = winterx.tweaks.TweakSettings.decorate(stock);
            int matching = 0;
            for (Object section : decorated.c) {
                E1.W6 value = (E1.W6)section;
                for (Field field : E1.W6.class.getDeclaredFields()) if (field.getType() == String.class && "WINTERX TWEAKS".equals(field.get(value))) matching++;
            }
            check(matching == (installed ? 1 : 0), "native packages did not share one WINTERX TWEAKS section");
            check(row(decorated, "winterx-tw-p/me.weirdmm.animaper") == installed, "Animaper missing from shared tweak section");
            check(winterx.tweaks.TweakSettings.decorate(decorated) == decorated, "repeat decoration duplicated native packages");
        }
        E1.i6 profile = allocate(E1.i6.class); set(profile, "b", 640); set(profile, "c", E1.t.j ? 1136 : 960);
        set(profile, "d", 40); set(profile, "e", E1.t.D()); set(profile, "j", E1.t.j ? 112 : 110);
        set(profile, "k", new E1.k0(4, 4, 34, 74, 38, 52, 0, 24, List.of(34, 186, 338, 490)));
        set(profile, "l", new E1.r(0, 0, 178, 0, List.of(), "", List.of(), 0, 0));
        E1.a app = allocate(E1.a.class); set(app, "a", "mail"); set(app, "b", "Mail"); set(app, "c", "fixture/mail");
        E1.c entry = new E1.c(app, 1, 2); E1.q6 state = allocate(E1.q6.class);
        for (Field field : E1.q6.class.getDeclaredFields()) {
            if (Map.class.isAssignableFrom(field.getType())) set(state, field.getName(), new LinkedHashMap<>());
            else if (List.class.isAssignableFrom(field.getType())) set(state, field.getName(), new ArrayList<>());
            else if (field.getType() == String.class) set(state, field.getName(), "");
        }
        set(state, "a", profile); set(state, "b", List.of(entry)); set(state, "o0", 160f); set(state, "r", E1.r7.T); set(state, "s", E1.P6.w);
        I1.I0 fonts = allocate(I1.I0.class);
        for (Field field : I1.I0.class.getDeclaredFields()) if (field.getType() == Typeface.class) set(fonts, field.getName(), Typeface.DEFAULT);
        Canvas canvas = new Canvas(Bitmap.createBitmap(640, 1136, Bitmap.Config.ARGB_8888)); canvas.translate(7, 11);
        float[] original = matrix(canvas); int saved = canvas.getSaveCount();
        ConcurrentHashMap<String, Bitmap> icons = new ConcurrentHashMap<>(); Bitmap icon = Bitmap.createBitmap(profile.e, profile.e, Bitmap.Config.ARGB_8888); icon.eraseColor(0xff226699); icons.put(app.c, icon);
        I1.h0.k(state, -1, profile, 0f, 40, I1.d0.h, null, null, null, fonts, Map.of(), icons, new Paint(), 0f, canvas);
        check(canvas.getSaveCount() == saved && Arrays.equals(original, matrix(canvas)), "core native drawing leaked Canvas state");
        check(NativeRuntime.manifests().size() == (installed ? 7 : 0), "a package failed during native rendering");
        if (installed) {
            E1.T6 page = winterx.tweaks.TweakSettings.page("winterx-tw-p/me.weirdmm.animaper");
            check(page != null && ((E1.W6)page.c.get(0)).c.size() == 9, "external Animaper Settings does not expose nine effects");
            check(Files.readString(new File(ruby, "animaper.mode").toPath()).equals("orbit\n"), "package install selected an effect automatically");
            NativeHooks.settings_action("winterx-animaper-mode-barrel");
            check(Files.readString(new File(ruby, "animaper.mode").toPath()).equals("barrel\n"), "external code action failed");
            NativeHooks.settings_action("winterx-layout-a/messageplus/photo/95");
            check(NativeHooks.media_photo_quality(85) == 95, "photo logic was not loaded from the code package");
            Object frame = NativeHooks.render_home_begin(canvas, -1L, null, null);
            NativeHooks.render_home_icon_context(state, new I1.b0(entry, 18, 200, false, 0));
            int scope = NativeHooks.render_icon_begin(canvas, profile, 18, 200);
            check(matrix(canvas)[0] < 1f && matrix(canvas)[4] < 1f, "Barrel is not executing from its external code");
            Files.delete(new File(root, "winterx-tweaks/me.weirdmm.animaper/enabled").toPath());
            NativeHooks.render_icon_end(canvas, scope); NativeHooks.render_home_end(frame);
            check(canvas.getSaveCount() == saved && Arrays.equals(original, matrix(canvas)), "removed package did not release its existing Canvas lease");
            check(!NativeRuntime.enabled("me.weirdmm.animaper"), "removed package still active");
        } else {
            check(NativeHooks.cache_tiles_allowed() && !NativeHooks.home_custom_grid_enabled() && !NativeHooks.render_custom_icons_enabled(), "legacy markers enabled uninstalled tweaks");
            check(NativeHooks.media_photo_quality(85) == 85, "uninstalled photo tweak changed output");
        }
        check(Arrays.equals(before, Files.readAllBytes(savedLayout.toPath())) && entry.b == 1 && entry.c == 2, "core/package loading changed saved/native layouts");
        System.out.println("Core-only native packages passed: installed=" + installed + "; no bundled providers; one Settings group; real drawing/lease cleanup; saved data preserved");
    }
}
