import java.io.File;
import java.nio.file.Files;
import winterx.layout.IconPositions;
public class IconPositionsCheck {
    public static void main(String[] args) throws Exception {
        File file = new File(args[0], "positions.json");
        IconPositions positions = new IconPositions();
        positions.put(0, "sapp:one", .1, .2);
        positions.put(0, "sapp:two", .12, .22);
        positions.put(1, "sapp:one", .8, .7);
        if (!positions.hit(0, .15, .25, .2, .2).id.equals("sapp:two")) throw new AssertionError("z order");
        positions.put(0, "sapp:one", .11, .21);
        if (!positions.hit(0, .15, .25, .2, .2).id.equals("sapp:one")) throw new AssertionError("move to front");
        positions.save(file);
        IconPositions restored = IconPositions.load(file);
        if (restored.list().size() != 3 || restored.get(1, "sapp:one").x != .8) throw new AssertionError("round trip");
        restored.remove(0, "sapp:one");
        if (restored.get(1, "sapp:one") == null) throw new AssertionError("page isolation");
        try { restored.put(0, "bad", Double.NaN, 0); throw new AssertionError("NaN accepted"); } catch (IllegalArgumentException expected) { }
        Files.writeString(file.toPath(), "{bad");
        try { IconPositions.load(file); throw new AssertionError("corruption accepted"); } catch (Exception expected) { }
        System.out.println("Icon position persistence, page isolation, overlap and validation passed");
    }
}
