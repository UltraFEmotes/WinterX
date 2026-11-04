import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.*;

/** Exercises actual 0.8.1 controller and model classes from the converted Spring JAR. */
public class TestSpringHooks {
    static Unsafe unsafe() throws Exception { Field f = Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o, String name, Object v) throws Exception { Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o, v); }
    static void check(boolean value, String message) { if (!value) throw new AssertionError(message); }
    static void drop(E1.O1 edit, int index, float x, float y, long time) {
        SpringHooks.begin(edit, 0, index);
        edit.o(0, index, 40, 100, time);
        check(edit.m != null, "drag did not start");
        edit.m.f = x + edit.m.c + 30;
        edit.m.g = y + edit.m.d + 37;
        edit.w = 0;
        SpringHooks.beforeDrop(edit);
        edit.x(time + 1);
    }
    public static void main(String[] args) throws Exception {
        System.setProperty("ruby.test.dir", args[0]);
        java.io.File folder = new java.io.File(args[0], "ruby"); folder.mkdirs();
        new java.io.File(folder, "free-icons.enabled").createNewFile();
        E1.i6 profile = (E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile, "b", 320); set(profile, "c", 568); set(profile, "d", 20); set(profile, "e", 60);
        set(profile, "k", new E1.k0(4, 4, 0, 0, 10, 10, 0, 0, Arrays.asList(0, 70, 140, 210)));
        x1.i1 host = (x1.i1)unsafe().allocateInstance(x1.i1.class); set(host, "e", profile);
        x1.P0 callback = x1.P0.class.getDeclaredConstructor(x1.i1.class, int.class).newInstance(host, 0);
        E1.i2 model = new E1.i2(new ArrayList<>(), new ArrayList<>(List.of(new ArrayList<>(List.of("one", "two")))), new LinkedHashMap<>());
        E1.O1 edit = new E1.O1(model, 16, 4, callback);
        drop(edit, 0, 180, 240, 1000);
        check(edit.e.toString().equals("[[one, two]]"), "original order changed");
        int[] p = IconRuntime.position(0, "one", 320, 479, 60, 60);
        check(p != null && p[0] == 180 && p[1] == 240, "saved coordinates incorrect");
        check(SpringHooks.editLocation(edit, 0, 0) != null, "edit position missing");
        E1.a app = (E1.a)unsafe().allocateInstance(E1.a.class); set(app, "a", "one");
        E1.c entry = new E1.c(app, 0, 0);
        M1.b position = SpringHooks.location(profile, entry, 0);
        check(((Number)position.h).intValue() == 180 && ((Number)position.w).intValue() == 240, "renderer/hit position mismatch");
        // Drag completion may retain a short animation; test a fresh edit session after respring.
        E1.O1 next = new E1.O1(model, 16, 4, callback);
        drop(next, 0, 70, 20, 2000); // Occupies icon two's grid rectangle.
        p = IconRuntime.position(0, "one", 320, 479, 60, 60);
        check(p[0] == 180 && p[1] == 240, "overlap changed saved position");
        check(next.e.toString().equals("[[one, two]]"), "overlap changed layout");
        new java.io.File(folder, "safe-mode.enabled").createNewFile();
        check(SpringHooks.editLocation(next, 0, 0) == null, "Safe Mode did not restore grid");
        System.out.println("Real Spring controller drop, position, collision and Safe Mode checks passed");
    }
}
