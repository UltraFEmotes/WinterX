import java.io.File;
import java.util.List;
import winterx.layout.GridSlots;
public class PatchedFreeMePersistenceCheck {
    public static void main(String[] args) throws Exception {
        GridSlots grid = GridSlots.load(new File(args[0], "ruby/freeme-slots-v1.json"));
        if (grid.get(2, "one") != 12 || grid.get(1, "one") != null || grid.get(0, "two") != 1)
            throw new AssertionError("FreeMe grid did not survive a fresh process");
        if (grid.resolve(0, List.of("two", "three"), 16).get("two") != 1)
            throw new AssertionError("gap collapsed after reload");
        System.out.println("FreeMe fresh-process sparse-grid reload passed");
    }
}
