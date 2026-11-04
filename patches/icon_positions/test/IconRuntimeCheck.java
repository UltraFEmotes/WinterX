import java.io.File;
import winterx.layout.IconRuntime;
public class IconRuntimeCheck {
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); System.setProperty("ruby.test.dir", root.toString());
        File folder = new File(root, "ruby"); folder.mkdirs();
        if (IconRuntime.record(0, "sapp:one", 100, 120, 320, 480, 60, 60)) throw new AssertionError("disabled recorded");
        new File(folder, "free-icons.enabled").createNewFile();
        if (!IconRuntime.record(0, "sapp:one", 130, 210, 320, 480, 60, 60)) throw new AssertionError("record failed");
        int[] p = IconRuntime.position(0, "sapp:one", 320, 480, 60, 60);
        if (p[0] != 130 || p[1] != 210) throw new AssertionError("pixel position");
        int[] resized = IconRuntime.position(0, "sapp:one", 580, 900, 60, 60);
        if (resized[0] != 260 || resized[1] != 420) throw new AssertionError("resize normalization");
        if (!"sapp:one".equals(IconRuntime.hit(0, 140, 220, 320, 480, 60, 60))) throw new AssertionError("hit");
        if (IconRuntime.hit(1, 140, 220, 320, 480, 60, 60) != null) throw new AssertionError("wrong page hit");
        if (IconRuntime.record(0, "bad", Float.NaN, 0, 320, 480, 60, 60)) throw new AssertionError("invalid accepted");
        if (IconRuntime.position(0, "sapp:one", 320, 480, 60, 60) == null) throw new AssertionError("failed write lost existing layout");
        new File(folder, "safe-mode.enabled").createNewFile();
        if (IconRuntime.position(0, "sapp:one", 320, 480, 60, 60) != null) throw new AssertionError("Safe Mode did not disable");
        System.out.println("Icon runtime gating, positions, resize and touch mapping passed");
    }
}
