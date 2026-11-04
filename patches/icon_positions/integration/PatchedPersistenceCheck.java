import java.io.File;
import winterx.layout.IconRuntime;
public class PatchedPersistenceCheck {
    public static void main(String[] args) {
        System.setProperty("ruby.test.dir", args[0]);
        int[] p = IconRuntime.position(0, "one", 320, 479, 60, 60);
        if (p == null || p[0] != 180 || p[1] != 240) throw new AssertionError("Position was not preserved across restart");
        if (!"one".equals(IconRuntime.hit(0, 190, 250, 320, 479, 60, 60))) throw new AssertionError("Restored icon was not hittable");
        System.out.println("Free icon position survives a fresh process");
    }
}
