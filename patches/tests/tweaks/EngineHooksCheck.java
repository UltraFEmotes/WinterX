import java.io.File;
import java.lang.reflect.Field;
import java.util.ArrayList;
import E1.T6;
import E1.V6;
import E1.W6;
import sun.misc.Unsafe;

/** Verify actual converted APK hooks without creating a launcher or JNI context. */
public final class EngineHooksCheck {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static V6 find(T6 page, String id) {
        for (Object section : page.c) for (Object row : ((W6) section).c)
            if (id.equals(((V6) row).a)) return (V6) row;
        return null;
    }
    public static void main(String[] args) throws Exception {
        ClassLoader loader = EngineHooksCheck.class.getClassLoader();
        for (String name : new String[]{"I1.T0", "I1.S0", "I1.N0", "x1.i1", "E1.B0", "E1.b4", "ruby.RubyHooks",
                "com.guille.spring.sapp.QuickJs", "winterx.tweaks.TweakHost", "winterx.coloredbar.ColoredBar",
                "winterx.appearance.BarArtwork", "winterx.appearance.RubyAppearance"})
            Class.forName(name, false, loader).getDeclaredMethods();
        Class<?> quickjs = Class.forName("com.guille.spring.sapp.QuickJs", false, loader);
        check(quickjs.getMethod("winterxCreate", ArrayList.class, C0.a.class).getReturnType() == quickjs,
              "bounded QuickJS factory absent");
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby"); ruby.mkdirs();
        new File(ruby, "coloredbar.enabled").createNewFile();
        Field field = Unsafe.class.getDeclaredField("theUnsafe"); field.setAccessible(true);
        Unsafe unsafe = (Unsafe) field.get(null);
        for (String name : new String[]{"E1.B0", "E1.b4"}) {
            Class<?> controller = Class.forName(name);
            Object instance = unsafe.allocateInstance(controller);
            T6 main = (T6) controller.getMethod("a", String.class).invoke(instance, "winterx-cb-page");
            check("ColoredBar".equals(main.b), "native controller missed ColoredBar");
            V6 digit = find(main, "winterx-cb-page/digit/0");
            check(digit != null && digit.e.equals(digit.a), "native page navigation field wrong");
            T6 nested = (T6) controller.getMethod("a", String.class).invoke(instance, digit.e);
            check(nested != null && nested.c.size() == 1, "native hex digit page missing");
        }
        System.out.println("Packaged engine: renderer/controller JVM verification, bounded factory and native ColoredBar page routing passed (no JNI)");
    }
}
