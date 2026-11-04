package winterx.coloredbar;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import java.io.File;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.concurrent.ConcurrentHashMap;
import sun.misc.Unsafe;

/** Uses actual converted Settings loaders and header renderer; no launcher or JNI. */
public final class SettingsArtworkCheck {
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
    static void set(Object object, String name, Object value) throws Exception {
        Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); field.set(object, value);
    }
    public static void main(String[] args) throws Exception {
        Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true);
        Unsafe unsafe = (Unsafe) field.get(null);
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby"); ruby.mkdirs();
        new File(ruby, ColoredBar.ENABLED).createNewFile();
        check(ColoredBar.action(ColoredBar.PREFIX + "139BD7"), "initial colour save failed");
        Bitmap original = Bitmap.createBitmap(2, 1, Bitmap.Config.ARGB_8888);
        original.eraseColor(0xFFD7D7D7);
        String key = "ios4/uikit/UINavigationBarDefaultBackground.png";
        HashMap<String, Bitmap> stock = new HashMap<>(); stock.put(key, original);
        stock.put("wallpaper.png", original);
        I1.T0 renderer = (I1.T0) unsafe.allocateInstance(I1.T0.class);
        set(renderer, "p", stock);
        set(renderer, "V", new ConcurrentHashMap<String, Bitmap>());
        I1.S0 cached = I1.S0.class.getDeclaredConstructor(Object.class, int.class).newInstance(renderer, 0);
        Object view = unsafe.allocateInstance(Class.forName("x1.J"));
        set(view, "m", new HashMap<>(stock));
        I1.S0 nativeView = I1.S0.class.getDeclaredConstructor(Object.class, int.class).newInstance(view, 1);
        for (I1.S0 loader : new I1.S0[]{cached, nativeView}) {
            Bitmap tinted = (Bitmap) loader.get(key);
            check(tinted != original && tinted.getPixel(0, 0) == 0xFF139BD7, "actual Settings loader bypassed tint");
            check(loader.get("wallpaper.png") == original && loader.get(42) == null, "Settings unrelated artwork affected");
            Bitmap canvasImage = Bitmap.createBitmap(320, 100, Bitmap.Config.ARGB_8888);
            I1.N.b(new Canvas(canvasImage), loader);
            check(canvasImage.getPixel(160, 40) == 0xFF139BD7, "actual Settings header renderer drew stock artwork");
        }
        set(renderer, "p", Collections.emptyMap());
        ConcurrentHashMap<String, Bitmap> fallback = new ConcurrentHashMap<>(); fallback.put(key, original);
        set(renderer, "V", fallback);
        check(((Bitmap) cached.get(key)).getPixel(0, 0) == 0xFF139BD7, "Settings fallback cache bypassed tint");
        check(ColoredBar.action(ColoredBar.PREFIX + "34C759"), "live colour change save failed");
        check(((Bitmap) cached.get(key)).getPixel(0, 0) == 0xFF34C759, "Settings cached old colour");
        check(((Bitmap) nativeView.get(key)).getPixel(0, 0) == 0xFF34C759, "native Settings view cached old colour");
        E1.q6 state = (E1.q6) unsafe.allocateInstance(E1.q6.class);
        set(state, "b", Collections.emptyList());
        ColoredBar.observe(state);
        check(ColoredBar.action("winterx-cb-exclude/settings"), "Settings exclusion save failed");
        check(cached.get(key) == original && nativeView.get(key) == original, "Settings loaders ignored exclusion");
        check(ColoredBar.action("winterx-cb-exclude/settings"), "Settings exclusion removal failed");
        new File(ruby, "safe-mode.enabled").createNewFile();
        check(cached.get(key) == original && nativeView.get(key) == original, "Settings loaders ignored Safe Mode");
        new File(ruby, "safe-mode.enabled").delete();
        new File(ruby, ColoredBar.ENABLED).delete();
        check(cached.get(key) == original && nativeView.get(key) == original, "Settings loaders ignored uninstall");
        check(stock.get(key) == original && fallback.get(key) == original && original.getPixel(0, 0) == 0xFFD7D7D7,
              "Settings changed shared caches or original bitmap");
        System.out.println("Packaged Settings: both lazy loaders, fallback cache, actual header draw, colour changes, exclusions and Safe Mode passed (no launcher/JNI)");
    }
}
