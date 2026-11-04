import java.io.File;
import java.lang.reflect.Field;
import android.graphics.Canvas;
import sun.misc.Unsafe;
public class SafeAppearanceCheck {
  public static void main(String[] args) throws Exception {
    Field f=Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true);
    Unsafe unsafe=(Unsafe)f.get(null);
    E1.i6 profile=(E1.i6)unsafe.allocateInstance(E1.i6.class);
    for (String name : new String[]{"b","c"}) { Field field=E1.i6.class.getDeclaredField(name); field.setAccessible(true); field.setInt(profile,name.equals("b") ? 640 : 960); }
    E1.q6 state=(E1.q6)unsafe.allocateInstance(E1.q6.class);
    Field a=E1.q6.class.getDeclaredField("a"); a.setAccessible(true); a.set(state,profile);
    Canvas canvas=new Canvas();
    if (winterx.safe.SafeAppearance.wallpaper(canvas, profile)) throw new AssertionError("Safe wallpaper enabled without marker");
    winterx.safe.SafeAppearance.status(canvas);
    if (!canvas.text.isEmpty()) throw new AssertionError("Status changed without marker");
    File dir=new File(System.getProperty("ruby.test.dir"),"ruby"); dir.mkdirs(); new File(dir,"safe-mode.enabled").createNewFile();
    if (!winterx.safe.SafeAppearance.wallpaper(canvas,profile)) throw new AssertionError("Safe wallpaper missing");
    if (canvas.lines != 18 || !canvas.text.contains("WinterX") || !canvas.text.contains("SAFE MODE")) throw new AssertionError("Wallpaper elements missing");
    Canvas status=new Canvas(); winterx.safe.SafeAppearance.status(status);
    if (!status.text.contains("SAFE MODE") || status.colors.get(0) != 0xff2d91ff) throw new AssertionError("Blue status text missing");
    System.out.println("Safe wallpaper and blue status indicator passed");
  }
}
