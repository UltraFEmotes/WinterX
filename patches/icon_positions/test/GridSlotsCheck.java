import java.nio.file.*;
import java.util.*;
import winterx.layout.GridSlots;
public class GridSlotsCheck {
    static void check(boolean ok, String why) { if (!ok) throw new AssertionError(why); }
    interface Attempt { void run() throws Exception; }
    static void rejects(Attempt attempt) throws Exception {
        boolean rejected = false;
        try { attempt.run(); } catch (Exception ex) { rejected = true; }
        check(rejected, "invalid grid accepted");
    }
    public static void main(String[] args) throws Exception {
        Path root = Paths.get(args[0]); GridSlots grid = new GridSlots();
        grid.put(0, "one", 15); grid.put(0, "two", 1); grid.put(1, "three", 11);
        check(grid.resolve(0, List.of("one", "two"), 16).get("one") == 15, "gap collapsed");
        Map<String, Integer> live = grid.resolve(0, List.of("two", "new", "another"), 16);
        check(live.get("two") == 1 && new HashSet<>(live.values()).size() == 3, "stale/new entries overlap");
        check(grid.resolve(0, List.of("one", "two"), 12).get("one") == 0, "profile capacity fallback lost icon");
        rejects(() -> grid.put(-1, "one", 0)); rejects(() -> grid.put(0, "\u0000hole", 0));
        rejects(() -> grid.put(0, "three", 1)); rejects(() -> grid.put(0, "three", 100));
        rejects(() -> grid.resolve(0, List.of("one", "one"), 16)); rejects(() -> grid.resolve(0, List.of("one", "two"), 1));
        Path file = root.resolve("slots.json"); grid.save(file.toFile());
        check(GridSlots.load(file.toFile()).get(1, "three") == 11, "reload failed");
        String good = Files.readString(file);
        for (String bad : List.of("{}", "{\"version\":2,\"slots\":[]}", "{\"version\":1,\"slots\":[{\"page\":0,\"id\":\"one\",\"slot\":0},{\"page\":0,\"id\":\"two\",\"slot\":0}]}", "{\"version\":1,\"slots\":[{\"page\":0,\"id\":\"one\",\"slot\":0},{\"page\":0,\"id\":\"one\",\"slot\":1}]}")) {
            Files.writeString(file, bad); rejects(() -> GridSlots.load(file.toFile()));
        }
        Files.writeString(file, good);
        Path link = root.resolve("link.json"); Files.createSymbolicLink(link, file);
        rejects(() -> grid.save(link.toFile())); rejects(() -> GridSlots.load(link.toFile()));
        check(Files.readString(file).equals(good), "link write changed target");
        System.out.println("FreeMe grid: sparse resolution, new/stale icons, capacity fallback, validation, atomic persistence and link rejection passed");
    }
}
