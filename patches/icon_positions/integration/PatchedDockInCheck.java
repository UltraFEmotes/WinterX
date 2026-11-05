import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.DockIn;
import winterx.layout.DockGeometry;
import winterx.layout.DockMotion;
import winterx.layout.LayoutSettings;

/** Real converted Spring classes, no launcher, imports, process control or user data. */
public final class PatchedDockInCheck {
    static Unsafe unsafe() throws Exception { Field f = Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o, String name, Object v) throws Exception { Field f = o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o, v); }
    static void check(boolean ok, String why) { if (!ok) throw new AssertionError(why); }
    static E1.a app(String id) throws Exception {
        E1.a a = (E1.a)unsafe().allocateInstance(E1.a.class);
        set(a, "a", id); set(a, "b", id); set(a, "c", "spring-icon/" + id); return a;
    }
    static final class RecordingCanvas extends android.graphics.Canvas {
        float tx, ty, sx, sy; int restores;
        public int save() { return 12; }
        public void translate(float x, float y) { tx = x; ty = y; }
        public void scale(float x, float y) { sx = x; sy = y; }
        public void scale(float x, float y, float px, float py) { sx = x; sy = y; tx = px * (1f - x); ty = py * (1f - y); }
        public void restoreToCount(int saved) { check(saved == 12, "wrong canvas restore count"); restores++; }
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); System.setProperty("ruby.test.dir", root.toString());
        E1.t.j = Boolean.parseBoolean(args[1]);
        File dir = new File(root, "ruby"); dir.mkdirs();
        for (String name : List.of("ios4_pages.json", "ios6_pages.json", "ios7_pages.json")) Files.writeString(new File(root, name).toPath(), "protected " + name);
        E1.i6 profile = (E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile, "b", 640); set(profile, "c", E1.t.j ? 1136 : 960); set(profile, "d", 40); set(profile, "e", 114);
        set(profile, "k", new E1.k0(4, 4, 34, 27, 38, 62, 0, 0, List.of(34, 186, 338, 490)));
        set(profile, "l", new E1.r(178, 0, 34, 0, List.of(), null, List.of(), 0, 0));
        E1.t.f = profile.c / 2f;
        x1.i1 host = (x1.i1)unsafe().allocateInstance(x1.i1.class);
        set(host, "e", profile); set(host, "b", E1.r7.T); set(host, "L6", 0f);
        set(host, "L1", new ArrayList<>()); set(host, "S1", new ArrayList<>());
        x1.P0 callback = x1.P0.class.getDeclaredConstructor(x1.i1.class, int.class).newInstance(host, 0);
        new File(dir, "dockin.enabled").createNewFile();
        check(DockIn.capacity() == 4, "default/minimum not 4");
        for (int count = 5; count <= 7; count++) {
            ArrayList<String> ids = new ArrayList<>(); ArrayList<E1.a> icons = new ArrayList<>(); LinkedHashMap<String, E1.a> available = new LinkedHashMap<>();
            for (int i = 0; i < count; i++) { String id = "android:dock-" + i; ids.add(id); E1.a a = app(id); icons.add(a); available.put(id, a); }
            set(host, "M1", icons);
            check(DockIn.select(count, count), "valid preference refused");
            check(!DockIn.select(count - 1, count), "unsafe shrink accepted");
            E1.q6 frame = (E1.q6)unsafe().allocateInstance(E1.q6.class); set(frame, "a", profile); set(frame, "c", icons);
            RecordingCanvas canvas = (RecordingCanvas)unsafe().allocateInstance(RecordingCanvas.class);
            int right = 0;
            for (int i = 0; i < count; i++) {
                DockGeometry.Cell cell = DockIn.cell(profile, i, count);
                check(cell.left >= right && cell.left + cell.size <= 640, "overlapping/outside bounds"); right = cell.left + cell.size;
                E1.A0 hit = host.o1(cell.left + cell.size / 2f, cell.top + cell.size / 2f);
                check(hit != null && hit.a == E1.z0.w && hit.b == i, "native touch targeted wrong slot");
                M1.b launch = host.n4(hit);
                check(((Number)launch.h).intValue() == cell.left && ((Number)launch.w).intValue() == cell.top, "native launch origin disagrees");
                check(DockIn.launchSize(host, icons.get(i).a) == cell.size, "launch size not the actual dock rectangle");
                set(host, "b", E1.r7.x); set(icons.get(i), "d", "test-app");
                host.R2(hit, icons.get(i));
                check(host.B.c == cell.left && host.B.d == cell.top && host.B.e == cell.size, "native H6 app launch rectangle disagrees");
                set(host, "b", E1.r7.T); set(host, "B", null);
                M1.b stock = I1.h0.j(profile, i, count);
                int saved = DockIn.beginNative(canvas, frame, i);
                check(Math.abs(((Number)stock.h).floatValue() * canvas.sx + canvas.tx - cell.left) < 0.01f &&
                      Math.abs(((Number)stock.w).floatValue() * canvas.sy + canvas.ty - cell.top) < 0.01f && canvas.sx == canvas.sy, "native renderer transform disagrees with hit bounds");
                DockIn.endIcon(canvas, saved);
                check(host.I(cell.left + 2f, cell.top + 2f) != null, "scaled native delete badge not tappable");
            }
            check(canvas.restores == count, "unbalanced icon transforms");
            check(host.o1(0f, DockIn.cell(profile, 0, count).top) == null, "empty dock margin tappable");
            available.put("home", app("home"));
            E1.i2 model = new E1.i2(ids, new ArrayList<>(List.of(new ArrayList<>(List.of("home")))), new LinkedHashMap<>());
            E1.i2 normalized = E1.t.R(model, model, available, 16);
            check(normalized.a.equals(ids), "native normalizer relocated extra icons");
            E1.O1 edit = new E1.O1(model, 16, 4, callback);
            check(DockIn.editCapacity(edit) == count, "controller capacity wrong");
            M1.b editPoint = edit.v(-1, count - 1);
            check(Math.abs(((Number)editPoint.h).floatValue() * 2f - DockIn.cell(profile, count - 1, count).left) < 0.1f, "native edit coordinate wrong");
            edit.y.put(ids.get(0), new M1.b(12f, 13f));
            M1.b cached = edit.w(-1, 0, 1000, ids.get(0));
            check(((Number)cached.h).floatValue() == 12f, "DockIn bypassed native position-animation cache");
            edit.y.clear();
            set(host, "W1", edit);
            DockMotion.begin(edit, profile);
            E1.G1 moving = new E1.G1(icons.get(0), -2, 30f, 400f, 0f, 1f, 1f, 0f, -1, 1f, 1f, 0f, 0f, 0);
            edit.o(-1, 0, 40f, 420f, 900);
            DockMotion.frame(host, List.of(moving), 1000);
            float small = DockIn.cell(profile, 0, count).size / (float)profile.e;
            check(Math.abs(DockMotion.scale(frame, moving) - small) < .001f, "dock pickup grew to stock size immediately");
            edit.f.remove("\u0000hole"); ((List<String>)edit.e.get(0)).add("\u0000hole"); edit.n = 0; edit.o = 1;
            DockMotion.frame(host, List.of(moving), 1100);
            DockMotion.frame(host, List.of(moving), 1175);
            float halfway = DockMotion.scale(frame, moving);
            check(halfway > small && halfway < 1f, "dock-to-home size did not interpolate");
            DockMotion.frame(host, List.of(moving), 1250);
            check(DockMotion.scale(frame, moving) == 1f, "home destination retained dock size");
            edit.x(1260);
            check(edit.r().a.size() == count - 1 && ((List<?>)edit.r().b.get(0)).contains(ids.get(0)), "native settling lost transferred icon");
            check(DockIn.liveCount(host) == -1, "capacity changed during settling");
            set(host, "W1", null);
            edit = new E1.O1(model, 16, 4, callback);
            edit.o(0, 0, 40f, 100f, 1000);
            DockGeometry.Cell last = DockIn.cell(profile, count - 1, count);
            E1.I1 hover = edit.p((last.left + last.size / 2f) / 2f, (last.top + last.size / 2f) / 2f, 0);
            check(hover != null && hover.a == -1 && ((E1.j2)hover.d).a == count - 1 && !hover.b, "full dock admission/hover wrong");
            set(host, "W1", edit);
            check(DockIn.liveCount(host) == -1, "capacity change during drag allowed");
            LayoutSettings.action(LayoutSettings.ACTION + "dockin-4", host);
            check(DockIn.capacity() == count, "settings shrank active drag");
            set(host, "W1", null);
            new File(dir, "safe-mode.enabled").createNewFile();
            check(DockIn.capacity() == 4 && E1.t.R(model, model, available, 16).a.equals(ids), "Safe Mode lost existing dock membership");
            check(host.o1(last.left + 2f, last.top + 2f) != null, "Safe Mode made existing extra icon inaccessible");
            new File(dir, "safe-mode.enabled").delete();
            new File(dir, "dockin.enabled").delete();
            check(E1.t.R(model, model, available, 16).a.equals(ids), "removal relocated existing extra icons");
            new File(dir, "dockin.enabled").createNewFile();
        }
        set(host, "M1", new ArrayList<E1.a>());
        check(DockIn.cell(profile, 0, 4) == null, "four-icon stock geometry replaced");
        check(DockIn.launchSize(host, "not-in-dock") == profile.e, "home launch size changed");
        RecordingCanvas errors = (RecordingCanvas)unsafe().allocateInstance(RecordingCanvas.class);
        for (int path = 0; path < 3; path++) {
            int beforeRestore = errors.restores;
            try {
                if (path == 0) I1.j1.e(errors, null, null, null, null, null, null, null);
                else if (path == 1) I1.h0.p(errors, null, null, null, null, null, 0f, 0f, 0f);
                else ((I1.h0)unsafe().allocateInstance(I1.h0.class)).r(errors, null, null, null, null, null, null, null, false, 0f);
                throw new AssertionError("renderer exception swallowed");
            } catch (NullPointerException expected) {
                check(errors.restores == beforeRestore + 1, "renderer exception leaked Canvas state");
            }
        }
        for (String name : List.of("ios4_pages.json", "ios6_pages.json", "ios7_pages.json")) check(Files.readString(new File(root, name).toPath()).equals("protected " + name), "native layout file overwritten");
        System.out.println("DockIn packaged geometry/touch/H6 launch sizing/native position caches/size interpolation/settling/hover/normalizer and exception restoration passed; live UI remains unverified");
    }
}
