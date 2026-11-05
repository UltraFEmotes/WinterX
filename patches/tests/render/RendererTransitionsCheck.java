package winterx.render;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import sun.misc.Unsafe;
import winterx.layout.FreeMe;
import winterx.layout.GridSlots;
import winterx.snowy.PackImport;
import winterx.snowy.SnowyHome;
import winterx.snowy.SnowySettings;

/** Real packaged h0/j1/Y/T0/A.o drawing. Only the application/files boundary is a fixture. */
public final class RendererTransitionsCheck {
    private static final String ACTION = "winterx-layout-a/snowy/";
    private static final String FOLDER = "folder:render-fixture";
    private static final Unsafe UNSAFE;
    static {
        try { Field f = Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); UNSAFE = (Unsafe)f.get(null); }
        catch (Exception failure) { throw new ExceptionInInitializerError(failure); }
    }
    private final File files = new File(System.getProperty("ruby.test.dir"));
    private final File ruby = new File(files, "ruby");
    private final Map<String, byte[]> protectedFiles = new LinkedHashMap<>();
    private final Map<Bitmap, int[]> protectedImages = new LinkedHashMap<>();
    private final ConcurrentHashMap<String, Bitmap> icons = new ConcurrentHashMap<>();
    private final Map<String, Bitmap> chrome = new LinkedHashMap<>();
    private final E1.i6 profile;
    private final I1.I0 fonts;
    private final E1.a mail, phone, safari, folder;
    private final List<E1.c> home;
    private final E1.q6 state;
    private final String caseName, revision, token;
    private final File artifacts;

    static void check(boolean condition, String reason) { if (!condition) throw new AssertionError(reason); }
    static <T> T allocate(Class<T> type) throws Exception { return type.cast(UNSAFE.allocateInstance(type)); }
    static void set(Object object, String name, Object value) throws Exception {
        Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); field.set(object, value);
    }
    static int[] pixels(Bitmap bitmap) {
        int[] result = new int[bitmap.getWidth() * bitmap.getHeight()];
        bitmap.getPixels(result, 0, bitmap.getWidth(), 0, 0, bitmap.getWidth(), bitmap.getHeight());
        return result;
    }
    static Bitmap solid(int width, int height, int color) {
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888); bitmap.eraseColor(color); return bitmap;
    }
    private E1.a app(String id, int color) throws Exception {
        E1.a app = allocate(E1.a.class); set(app, "a", id); set(app, "b", "Label " + id); set(app, "c", "spring-icon/" + id);
        Bitmap image = solid(E1.t.D(), E1.t.C(), color); icons.put(app.c, image); protectedImages.put(image, pixels(image));
        return app;
    }
    private E1.q6 model(List<E1.c> entries, int page) throws Exception {
        E1.q6 model = allocate(E1.q6.class);
        for (Field field : E1.q6.class.getDeclaredFields()) {
            if (Map.class.isAssignableFrom(field.getType())) set(model, field.getName(), new LinkedHashMap<>());
            else if (List.class.isAssignableFrom(field.getType())) set(model, field.getName(), new ArrayList<>());
            else if (field.getType() == String.class) set(model, field.getName(), "");
        }
        set(model, "a", profile); set(model, "b", page == 0 ? entries : home);
        set(model, "n0", page == 0 ? new ArrayList<>() : List.of(entries)); set(model, "o0", page * 320f);
        set(model, "c", List.of(phone, safari)); set(model, "r", E1.r7.T); set(model, "s", E1.P6.w); set(model, "d", "12:34");
        set(model, "H", allocate(E1.Y3.class)); set(model, "h0", allocate(E1.Q1.class)); set(model, "Z", allocate(E1.i.class));
        set(model, "c0", allocate(E1.o6.class));
        set(model, "q0", new E1.Y4(0, 100, false));
        set(model, "N0", new LinkedHashMap<>(Map.of("mail", "!", "phone", "!")));
        O1.c members = new O1.c(2); members.add(mail); members.add(safari);
        set(model, "g0", new LinkedHashMap<>(Map.of(FOLDER, new E1.V1("Fixture folder", members, java.util.Set.of()))));
        return model;
    }
    private RendererTransitionsCheck(String[] args) throws Exception {
        caseName = args[0]; E1.t.j = Boolean.parseBoolean(args[1]); revision = args[2]; token = args[3];
        artifacts = args.length > 4 ? new File(args[4]) : null;
        profile = allocate(E1.i6.class); set(profile, "b", 640); set(profile, "c", E1.t.j ? 1136 : 960);
        set(profile, "A", "solid"); set(profile, "B", 0L);
        set(profile, "E", new E1.j("solid", new E1.k(0, 0, 0L), new E1.k(0, 0, 0L)));
        set(profile, "d", 40); set(profile, "e", E1.t.D()); set(profile, "j", E1.t.j ? 112 : 110);
        set(profile, "k", new E1.k0(4, 4, 34, 74, 38, 52, 0, 24, List.of(34, 186, 338, 490)));
        set(profile, "l", new E1.r(0, 0, 178, 0, List.of(), "", List.of(), 0, 0));
        fonts = allocate(I1.I0.class);
        for (Field field : I1.I0.class.getDeclaredFields()) if (field.getType() == Typeface.class) set(fonts, field.getName(), Typeface.DEFAULT);
        mail = app("mail", 0xffd02020); phone = app("phone", 0xffa04020); safari = app("safari", 0xffb02080);
        folder = app(FOLDER, 0xff804080);
        Bitmap badge = solid(42, 40, 0xffff0000); chrome.put("ios4/chrome/badge_bg.png", badge);
        chrome.put("ios4/chrome/badge_exclamation.png", badge); protectedImages.put(badge, pixels(badge));
        home = List.of(new E1.c(mail, 0, 0), new E1.c(folder, 0, 1), new E1.c(safari, 0, 2));
        state = model(home, 0);
        for (String path : List.of("ios4_pages.json", "ios6_pages.json", "ios7_pages.json", "ruby/icon-positions-v1.json", "ruby/dockin.capacity")) {
            File file = new File(files, path); Files.writeString(file.toPath(), "protected " + path); protectedFiles.put(path, Files.readAllBytes(file.toPath()));
        }
    }
    private void enableSnowy() throws Exception {
        Files.writeString(new File(ruby, "snowyhome.enabled").toPath(), "1");
        check(PackImport.install(token).equals(revision), "fixture pack import failed");
        check(SnowySettings.action(ACTION + "pack/" + revision), "fixture pack selection failed");
        check(SnowySettings.action(ACTION + "corners/5"), "fixture corners failed");
        check(SnowySettings.action(ACTION + "labels"), "fixture labels failed");
        check(SnowySettings.action(ACTION + "badge/2"), "fixture badge failed");
        check(SnowyHome.hiddenLabels() && SnowyHome.icon(mail, icons.get(mail.c)) != icons.get(mail.c), "fixture theme not active");
    }
    private void enableFreeMe(int page) throws Exception {
        GridSlots slots = new GridSlots(); slots.put(page, "mail", 13); slots.put(page, FOLDER, 6); slots.put(page, "safari", 3);
        File file = new File(ruby, "freeme-slots-v1.json"); slots.save(file);
        protectedFiles.put("ruby/freeme-slots-v1.json", Files.readAllBytes(file.toPath()));
        Files.writeString(new File(ruby, "freeme.enabled").toPath(), "1");
        check(FreeMe.entries(home, profile, page).get(0).b == 3, "fixture sparse grid not active");
    }
    private Bitmap canvasBitmap() { return Bitmap.createBitmap(profile.b, profile.c, Bitmap.Config.ARGB_8888); }
    private Bitmap drawHome(E1.q6 model, A.o tiles, float progress) {
        Bitmap image = canvasBitmap(); Canvas canvas = new Canvas(image); int save = canvas.getSaveCount();
        I1.h0.k(model, -1, profile, progress, 40, I1.d0.h, null, null, tiles, fonts, chrome, icons, new Paint(), 0f, canvas);
        check(canvas.getSaveCount() == save, "home renderer leaked Canvas state"); return image;
    }
    private void save(String name, Bitmap image) throws Exception {
        if (artifacts != null) try (FileOutputStream output = new FileOutputStream(new File(artifacts, name + ".png"))) {
            check(image.compress(Bitmap.CompressFormat.PNG, 100, output), "could not save fixture image");
        }
    }
    private void equal(Bitmap actual, Bitmap expected) throws Exception {
        save("actual", actual); save("expected", expected);
        int[] a = pixels(actual), b = pixels(expected); long mismatch = 0;
        for (int i = 0; i < a.length; i++) if (a[i] != b[i]) mismatch++;
        preserve(); check(mismatch == 0, "RENDER_REGRESSION: " + caseName + " (" + mismatch + " differing pixels)");
    }
    private void preserve() throws Exception {
        for (Map.Entry<String, byte[]> entry : protectedFiles.entrySet())
            check(Arrays.equals(entry.getValue(), Files.readAllBytes(new File(files, entry.getKey()).toPath())), "protected file changed: " + entry.getKey());
        for (Map.Entry<Bitmap, int[]> entry : protectedImages.entrySet())
            check(!entry.getKey().isRecycled() && Arrays.equals(entry.getValue(), pixels(entry.getKey())), "shared source artwork changed");
        check(home.get(0).b == 0 && home.get(0).c == 0 && home.get(1).c == 1, "native home cells mutated");
        check(I1.h0.V(state, FOLDER).equals(((E1.V1)state.g0.get(FOLDER)).b), "native folder members changed");
    }
    private void scrollK() throws Exception {
        A.o tiles = new A.o(0); tiles.v(state, fonts, icons, chrome, new Paint());
        check(!((Map)tiles.w).isEmpty(), "stock tile warm-up did not run");
        enableSnowy(); equal(drawHome(state, tiles, .45f), drawHome(state, null, .45f));
    }
    private void scrollO() throws Exception {
        A.o tiles = new A.o(0); tiles.v(state, fonts, icons, chrome, new Paint()); enableSnowy();
        Bitmap actual = canvasBitmap(); Canvas canvas = new Canvas(actual); int save = canvas.getSaveCount();
        boolean drawn = I1.h0.o(canvas, state, fonts, icons, chrome, tiles, null, null, 0f, 0f, 0f, I1.d0.h, 1f, -1, 1f, null, 0);
        check(canvas.getSaveCount() == save, "fast path leaked Canvas state");
        preserve(); check(!drawn && Arrays.stream(pixels(actual)).allMatch(p -> p == 0), "RENDER_REGRESSION: " + caseName + " (themed frame admitted native fast cache)");
        equal(drawHome(state, tiles, .45f), drawHome(state, null, .45f));
    }
    private E1.q6 openFolder(int page) throws Exception {
        E1.q6 opened = model(home, page); set(opened, "f0", new E1.U1(1, false, 0, 0f, 0f, -1, page, FOLDER, false)); return opened;
    }
    private I1.X expectedGeometry(E1.q6 opened, E1.S1 motion) {
        int row = 1, column = 2, rows = 1;
        float split = E1.t.k(row) + 74f, height = 125f, lift = E1.t.i0(row, rows), gap = height - lift;
        float[] notch = {(float)Math.floor(E1.t.E() / 2f + E1.t.j(column) - 12f), (float)Math.floor(split - 12f), 24f, 12f};
        return new I1.X(profile.b, profile.c, 1, split, split * 2f, height, notch,
            Math.round(-lift * motion.a * 2f), Math.round(gap * motion.a * 2f), Math.round((gap + 12f) * motion.a * 2f), lift);
    }
    private Bitmap drawHalf(E1.q6 opened, I1.X geometry, boolean upper, boolean reference) {
        Bitmap image = canvasBitmap(); Canvas canvas = new Canvas(image); Paint paint = new Paint();
        if (reference) {
            if (!upper) I1.h0.a.m(canvas, paint, profile, chrome, null, 1f);
            int index = 0;
            for (E1.c original : (List<E1.c>)opened.d(opened.f0.g)) {
                int slot = index == 0 ? 13 : index == 1 ? 6 : 3;
                int row = slot / 4, column = slot % 4;
                if ((E1.t.k(row) < geometry.d) == upper) {
                    M1.b point = E1.d4.w(profile, row, column); E1.a app = original.a;
                    I1.h0.E(canvas, paint, profile, fonts, chrome, I1.h0.c(app, opened, fonts, icons), app.b,
                        ((Number)point.h).intValue(), ((Number)point.w).intValue(), false, false, I1.Z.f, I1.h0.f(app, opened));
                }
                index++;
            }
            if (!upper) I1.h0.p(canvas, paint, opened, fonts, icons, chrome, 0f, 1f, 1f);
        } else if (upper) I1.h0.B(canvas, paint, opened, fonts, icons, chrome, geometry, I1.Z.f, 1f);
        else I1.h0.a.x(canvas, paint, opened, fonts, icons, chrome, null, geometry, I1.Z.f, 0f);
        check(canvas.getSaveCount() == 1, "folder half leaked Canvas state"); return image;
    }
    private void folderHalf(boolean upper) throws Exception {
        enableFreeMe(1); E1.q6 opened = openFolder(1); I1.X geometry = expectedGeometry(opened, I1.Y.i);
        equal(drawHalf(opened, geometry, upper, false), drawHalf(opened, geometry, upper, true));
    }
    private void folderAnchor() throws Exception {
        enableFreeMe(1); E1.q6 opened = openFolder(1);
        for (float amount : new float[]{0f, .4f, 1f}) {
            E1.S1 motion = new E1.S1(amount, 0f, 1f, 1f, 0);
            I1.X actual = I1.j1.p(opened, motion), expected = expectedGeometry(opened, motion);
            preserve(); check(actual != null && actual.c == expected.c && actual.d == expected.d && actual.e == expected.e &&
                actual.h == expected.h && actual.i == expected.i && actual.j == expected.j && Arrays.equals(actual.g, expected.g),
                "RENDER_REGRESSION: " + caseName + " (native-index folder notch ignored saved cell)");
        }
    }
    private void folderRetained() throws Exception {
        E1.q6 opened = openFolder(0); I1.Y layers = new I1.Y();
        check(layers.c(opened, fonts, icons, chrome, null), "stock folder layers did not build");
        Bitmap retained = layers.a; int[] before = pixels(retained); List key = layers.e;
        enableFreeMe(0); boolean allowed = layers.c(opened, fonts, icons, chrome, null);
        preserve(); check(!allowed, "RENDER_REGRESSION: " + caseName + " (retained dense folder cache admitted)");
        check(layers.a == retained && layers.e == key && !retained.isRecycled() && Arrays.equals(before, pixels(retained)), "retained folder cache destroyed");
    }
    private void folderContent() throws Exception {
        enableSnowy(); E1.q6 opened = openFolder(0); I1.X geometry = I1.j1.p(opened, I1.Y.i);
        Bitmap actual = canvasBitmap(), expected = canvasBitmap();
        I1.h0.a.C(new Canvas(actual), new Paint(), opened, fonts, icons, chrome, null, geometry, -1);
        // The folder chrome/title is the same. Only replace its icon lookup in an independent map.
        ConcurrentHashMap<String, Bitmap> themed = new ConcurrentHashMap<>(icons);
        for (E1.a app : List.of(mail, safari)) themed.put(app.c, I1.h0.c(app, opened, fonts, icons));
        I1.h0.a.C(new Canvas(expected), new Paint(), opened, fonts, themed, chrome, null, geometry, -1);
        equal(actual, expected);
    }
    private void warmTiles() throws Exception {
        A.o tiles = new A.o(0); enableSnowy(); tiles.v(state, fonts, icons, chrome, new Paint());
        Files.delete(new File(ruby, "snowyhome.enabled").toPath());
        Bitmap actual = drawHome(state, tiles, .45f), expected = drawHome(state, null, .45f);
        equal(actual, expected);
    }
    private void warmDock() throws Exception {
        A.o tiles = new A.o(0); enableSnowy(); tiles.v(state, fonts, icons, chrome, new Paint());
        preserve(); check(tiles.T == null && ((Map)tiles.w).isEmpty(), "RENDER_REGRESSION: " + caseName + " (themed native dock/tile caches were warmed)");
    }
    private I1.T0 controller() throws Exception {
        I1.T0 renderer = allocate(I1.T0.class);
        for (Field field : I1.T0.class.getDeclaredFields()) {
            Class<?> type = field.getType();
            if (type == Paint.class) set(renderer, field.getName(), new Paint());
            else if (type == ConcurrentHashMap.class) set(renderer, field.getName(), new ConcurrentHashMap<>());
            else if (type == java.util.HashMap.class) set(renderer, field.getName(), new java.util.HashMap<>());
            else if (type == Map.class || type == LinkedHashMap.class) set(renderer, field.getName(), new LinkedHashMap<>());
        }
        set(renderer, "a", fonts); set(renderer, "b", icons); set(renderer, "p", chrome);
        set(renderer, "Z", new A.o(0)); set(renderer, "F", new I1.Y());
        renderer.T.put(new M1.b(100, false), canvasBitmap()); return renderer;
    }
    private void dockScroll() throws Exception {
        I1.T0 renderer = controller(); renderer.Z.v(state, fonts, icons, chrome, new Paint()); enableSnowy();
        Bitmap actual = canvasBitmap();
        check(I1.T0.o(renderer, new Canvas(actual), state, fonts, 0f, .4f, I1.d0.h, null, 0f, 1f, null, -1, 1f, 0), "native full renderer rejected fixture");
        // The full native path has a cached dock branch only after a vertical dock offset.
        Bitmap expected = canvasBitmap(); set(renderer, "Z", null);
        check(I1.T0.o(renderer, new Canvas(expected), state, fonts, 0f, .4f, I1.d0.h, null, 0f, 1f, null, -1, 1f, 0), "uncached full renderer rejected fixture");
        equal(actual, expected);
    }
    private void folderPrewarm() throws Exception {
        I1.T0 renderer = controller(); set(renderer, "G", FOLDER); set(renderer, "R", true);
        enableFreeMe(0); renderer.P(state); preserve();
        check(renderer.Q == null && renderer.F.a == null, "RENDER_REGRESSION: " + caseName + " (sparse folder prewarm queued obsolete native layers)");
    }
    private Map<String, Object> retainLayers(I1.Y layers) throws Exception {
        Map<String, Object> retained = new LinkedHashMap<>();
        for (Field field : I1.Y.class.getDeclaredFields()) {
            if (java.lang.reflect.Modifier.isStatic(field.getModifiers())) continue;
            Object value = field.get(layers); retained.put(field.getName(), value);
            if (value instanceof Bitmap) protectedImages.put((Bitmap)value, pixels((Bitmap)value));
            else if (value instanceof Bitmap[]) for (Bitmap image : (Bitmap[])value)
                if (image != null) protectedImages.put(image, pixels(image));
        }
        return retained;
    }
    private void layersUnchanged(I1.Y layers, Map<String, Object> retained) throws Exception {
        for (Map.Entry<String, Object> entry : retained.entrySet()) {
            Field field = I1.Y.class.getDeclaredField(entry.getKey()); Object value = field.get(layers);
            boolean same = field.getType().isPrimitive() ? java.util.Objects.equals(value, entry.getValue()) : value == entry.getValue();
            check(same, "RENDER_REGRESSION: " + caseName + " (retained folder state changed: " + entry.getKey() + ")");
        }
    }
    private I1.R0 queued(I1.T0 renderer) throws Exception {
        I1.R0 work = allocate(I1.R0.class); set(work, "h", 0); set(work, "w", renderer); return work;
    }
    private void folderQueued() throws Exception {
        I1.T0 renderer = controller(); E1.q6 opened = openFolder(0);
        check(renderer.F.c(opened, fonts, icons, chrome, null), "stock queued-layer fixture did not warm");
        // A pending final chunk must not consume retained bitmaps after a tweak changes.
        set(renderer.F, "g", I1.Y.d(opened, fonts, icons, renderer.B(opened))); set(renderer.F, "e", null); set(renderer.F, "h", 10);
        Map<String, Object> retained = retainLayers(renderer.F);
        set(renderer, "Q", opened); set(renderer, "R", true); enableFreeMe(0);
        queued(renderer).run();
        check(!renderer.R && renderer.Q == null, "RENDER_REGRESSION: " + caseName + " (queued sparse layers not cancelled)");
        layersUnchanged(renderer.F, retained);
        check(I1.Y.d(opened, fonts, icons, null) == null, "RENDER_REGRESSION: " + caseName + " (sparse layer keys admitted)");
        renderer.F.b(0, opened, fonts, icons, chrome, null, I1.j1.p(opened, I1.Y.i));
        layersUnchanged(renderer.F, retained);
        Files.delete(new File(ruby, "freeme.enabled").toPath());
        check(I1.Y.d(opened, fonts, icons, null) != null, "native layer keys did not resume after removal");
        enableSnowy(); set(renderer, "Q", opened); set(renderer, "R", true);
        queued(renderer).run(); layersUnchanged(renderer.F, retained);
        check(!renderer.R && renderer.Q == null, "queued themed layers not cancelled");
        Files.writeString(new File(ruby, "safe-mode.enabled").toPath(), "1");
        check(I1.Y.d(opened, fonts, icons, null) != null, "Safe Mode did not resume native layer eligibility");
    }
    private void folderBookkeeping() throws Exception {
        I1.T0 renderer = controller(); enableFreeMe(1); E1.q6 opened = openFolder(1);
        set(renderer, "G", "previous-folder"); renderer.P(opened);
        check(FOLDER.equals(renderer.G) && renderer.Q == null, "open-folder G bookkeeping was bypassed");
        check(opened.f0.a == 1 && opened.d(1).get(1) == home.get(1), "native folder list index/order changed");
        check(FreeMe.entries((List<E1.c>)opened.d(1), profile, 1).get(1).a == folder, "sparse folder copies changed native index");
        check(FreeMe.entries(home, profile, -1) == home, "negative page was treated as a home grid");
        enableSnowy(); set(renderer, "G", "previous-folder"); renderer.P(opened);
        check(FOLDER.equals(renderer.G) && renderer.Q == null, "themed open-folder bookkeeping changed");
    }
    private void cacheLifecycle() throws Exception {
        A.o tiles = new A.o(0); tiles.v(state, fonts, icons, chrome, new Paint());
        Map<Object, Object> retained = new LinkedHashMap<>((Map)tiles.w); Object dock = tiles.T;
        check(!retained.isEmpty() && dock != null, "stock lifecycle caches did not warm");
        for (Object value : retained.values()) if (value instanceof I1.e0)
            protectedImages.put(((I1.e0)value).a, pixels(((I1.e0)value).a));
        if (dock instanceof C1.D1 && ((C1.D1)dock).w instanceof Bitmap) {
            Bitmap image = (Bitmap)((C1.D1)dock).w; protectedImages.put(image, pixels(image));
        }
        enableSnowy();
        check(tiles.m(profile, fonts, chrome, icons.get(mail.c), mail.c, mail.b, false, false, "!") == null,
            "RENDER_REGRESSION: " + caseName + " (direct themed tile producer admitted)");
        check(tiles.i(profile, fonts, state, chrome, null) == null,
            "RENDER_REGRESSION: " + caseName + " (direct themed dock producer admitted)");
        tiles.v(state, fonts, icons, chrome, new Paint());
        check(retained.equals(tiles.w) && tiles.T == dock, "retained stock cache contents replaced");
        equal(drawHome(state, tiles, .45f), drawHome(state, null, .45f));
        check(SnowySettings.action(ACTION + "labels") && SnowySettings.action(ACTION + "corners/1") &&
            SnowySettings.action(ACTION + "badge/1"), "fixture appearance changes failed");
        equal(drawHome(state, tiles, .45f), drawHome(state, null, .45f));
        Files.writeString(new File(ruby, "safe-mode.enabled").toPath(), "1");
        equal(drawHome(state, tiles, .45f), drawHome(state, null, .45f));
        Files.delete(new File(ruby, "safe-mode.enabled").toPath()); Files.delete(new File(ruby, "snowyhome.enabled").toPath());
        equal(drawHome(state, tiles, .45f), drawHome(state, null, .45f));
        check(retained.equals(tiles.w) && tiles.T == dock, "removal discarded retained native cache contents");
    }
    private Bitmap barrelReference(E1.q6 model) {
        Bitmap image = canvasBitmap(); Canvas canvas = new Canvas(image); Paint paint = new Paint();
        for (int page = 0; page < model.c(); page++) {
            int offset = Math.round((page * 320f - model.o0) * I1.G0.p(profile));
            if (offset <= -profile.b || offset >= profile.b) continue;
            float progress = (float)offset / profile.b;
            for (E1.c entry : FreeMe.entries((List<E1.c>)model.d(page), profile, page)) {
                M1.b point = E1.d4.w(profile, entry.b, entry.c);
                int x = ((Number)point.h).intValue() + offset, y = ((Number)point.w).intValue();
                float center = x - (float)offset + profile.e * .5f;
                double radius = profile.b * .65, camera = profile.b * 2.8;
                double angle = Math.asin((center - profile.b * .5) / radius) + progress * Math.PI * .75;
                double perspective = camera / (camera - radius * (Math.cos(angle) - 1));
                double blend = Math.sin(Math.PI * Math.abs(progress));
                float dx = (float)((profile.b * .5 + radius * Math.sin(angle) * perspective - center - progress * profile.b) * blend);
                float sx = (float)(1 + blend * (Math.max(.14, Math.cos(angle)) * perspective - 1));
                float sy = (float)(1 + blend * (perspective - 1));
                int save = canvas.save(); canvas.translate(dx, 0f); canvas.scale(sx, sy, x + profile.e * .5f, y + profile.e * .5f);
                E1.a app = entry.a;
                I1.h0.E(canvas, paint, profile, fonts, chrome, I1.h0.c(app, model, fonts, icons), app.b,
                    x, y, false, false, I1.Z.f, I1.h0.f(app, model));
                canvas.restoreToCount(save);
            }
        }
        check(canvas.getSaveCount() == 1, "reference Barrel renderer leaked Canvas state"); return image;
    }
    private void barrelRender(boolean sixColumns) throws Exception {
        if (sixColumns) set(profile, "k", new E1.k0(4, 6, 34, 74, 38, 52, 0, 24, List.of(16, 116, 216, 316, 416, 516)));
        A.o tiles = new A.o(0); tiles.v(state, fonts, icons, chrome, new Paint());
        enableSnowy();
        GridSlots slots = new GridSlots();
        for (int page = 0; page <= 1; page++) {
            slots.put(page, "mail", sixColumns ? 19 : 13); slots.put(page, FOLDER, sixColumns ? 10 : 6); slots.put(page, "safari", sixColumns ? 5 : 3);
        }
        slots.save(new File(ruby, "freeme-slots-v1.json"));
        protectedFiles.put("ruby/freeme-slots-v1.json", Files.readAllBytes(new File(ruby, "freeme-slots-v1.json").toPath()));
        Files.writeString(new File(ruby, "freeme.enabled").toPath(), "1");
        Files.writeString(new File(ruby, "animaper.enabled").toPath(), "1");
        Files.writeString(new File(ruby, "animaper.mode").toPath(), "barrel\n");
        winterx.animaper.AnimaperSettings.select(winterx.animaper.AnimaperSettings.PREFIX + "barrel");
        Field lastRead = winterx.animaper.Animaper.class.getDeclaredField("lastRead"); lastRead.setAccessible(true); lastRead.setLong(null, -500);
        protectedFiles.put("ruby/animaper.mode", Files.readAllBytes(new File(ruby, "animaper.mode").toPath()));
        List<E1.c> second = List.of(home.get(2), home.get(0), home.get(1)); set(state, "n0", List.of(second));
        for (float points : new float[]{80f, 160f, 240f, 0f, 320f, -80f, 640f}) {
            set(state, "o0", points); equal(drawHome(state, tiles, 0f), barrelReference(state));
        }
        check(state.d(0) == home && state.d(1) == second, "Barrel reordered native pages");
    }
    private void run() throws Exception {
        switch (caseName) {
            case "scroll-k": scrollK(); break;
            case "scroll-o": scrollO(); break;
            case "folder-upper": folderHalf(true); break;
            case "folder-lower": folderHalf(false); break;
            case "folder-anchor": folderAnchor(); break;
            case "folder-retained": folderRetained(); break;
            case "folder-content": folderContent(); break;
            case "warm-tiles": warmTiles(); break;
            case "warm-dock": warmDock(); break;
            case "dock-scroll": dockScroll(); break;
            case "folder-prewarm": folderPrewarm(); break;
            case "folder-queued": folderQueued(); break;
            case "folder-bookkeeping": folderBookkeeping(); break;
            case "cache-lifecycle": cacheLifecycle(); break;
            case "barrel-render": barrelRender(false); break;
            case "barrel-sparse": barrelRender(true); break;
            default: throw new IllegalArgumentException(caseName);
        }
        preserve(); System.out.println("Packaged renderer passed: " + caseName + "; original files/artwork/models preserved");
    }
    public static void main(String[] args) throws Exception { new RendererTransitionsCheck(args).run(); }
}
