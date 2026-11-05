package winterx.render;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import winterx.animaper.Animaper;
import winterx.animaper.AnimaperSettings;
import static winterx.render.RendererTransitionsCheck.allocate;
import static winterx.render.RendererTransitionsCheck.check;
import static winterx.render.RendererTransitionsCheck.set;

/** Packaged native k/E delegation, real Canvas state, and isolated thread/context boundaries. */
public final class AnimaperCanvasCheck {
    private static final RuntimeException FAILURE = new IllegalStateException("isolated Canvas failure");
    private static final class Spy extends Canvas {
        boolean failBitmap, failScale;
        final List<float[]> seen = new ArrayList<>();
        Spy() { super(Bitmap.createBitmap(640, 1136, Bitmap.Config.ARGB_8888)); }
        private void bitmap() { seen.add(matrix(this)); if (failBitmap) throw FAILURE; }
        @Override public void drawBitmap(Bitmap image, float x, float y, Paint paint) { bitmap(); super.drawBitmap(image, x, y, paint); }
        @Override public void drawBitmap(Bitmap image, Rect from, Rect to, Paint paint) { bitmap(); super.drawBitmap(image, from, to, paint); }
        @Override public void drawBitmap(Bitmap image, Rect from, RectF to, Paint paint) { bitmap(); super.drawBitmap(image, from, to, paint); }
        @Override public void scale(float x, float y, float px, float py) { super.scale(x, y, px, py); if (failScale) throw FAILURE; }
    }
    private static float[] matrix(Canvas canvas) { float[] values = new float[9]; canvas.getMatrix().getValues(values); return values; }
    private static Object context(String name) throws Exception {
        Field field = Animaper.class.getDeclaredField(name); field.setAccessible(true); return ((ThreadLocal<?>)field.get(null)).get();
    }
    private static void restored(Canvas canvas, int saved, float[] before, String reason) {
        check(canvas.getSaveCount() == saved && Arrays.equals(before, matrix(canvas)), reason);
    }
    private static void icon(Canvas canvas, E1.i6 profile, I1.I0 fonts, Bitmap image) {
        I1.h0.E(canvas, new Paint(), profile, fonts, Map.of(), image, "Fixture", 120, 220, false, false, I1.Z.f, null);
    }
    private static void home(Canvas canvas, E1.q6 state, I1.I0 fonts, ConcurrentHashMap<String, Bitmap> images, float motion) {
        I1.h0.k(state, -1, state.a, motion, 40, I1.d0.h, null, null, null, fonts, Map.of(), images, new Paint(), 0f, canvas);
    }
    public static void main(String[] args) throws Exception {
        E1.t.j = args.length > 0 && Boolean.parseBoolean(args[0]);
        File files = new File(System.getProperty("ruby.test.dir")), ruby = new File(files, "ruby"); ruby.mkdirs();
        Map<File, byte[]> protectedFiles = new LinkedHashMap<>();
        for (String name : List.of("ios4_pages.json", "ios6_pages.json", "ruby/freeme-slots-v1.json", "ruby/icon-positions-v1.json")) {
            File file = new File(files, name); Files.writeString(file.toPath(), "protected " + name); protectedFiles.put(file, Files.readAllBytes(file.toPath()));
        }
        Files.writeString(new File(ruby, "animaper.mode").toPath(), "orbit\n");
        Files.writeString(new File(ruby, "animaper.enabled").toPath(), "1");
        AnimaperSettings.select(AnimaperSettings.PREFIX + "barrel"); check(Animaper.barrelEnabled(), "Barrel selection unavailable");
        protectedFiles.put(new File(ruby, "animaper.mode"), Files.readAllBytes(new File(ruby, "animaper.mode").toPath()));
        E1.i6 profile = allocate(E1.i6.class); set(profile, "b", 640); set(profile, "c", E1.t.j ? 1136 : 960);
        set(profile, "A", "solid"); set(profile, "B", 0L); set(profile, "E", new E1.j("solid", new E1.k(0, 0, 0L), new E1.k(0, 0, 0L)));
        set(profile, "d", 40); set(profile, "e", E1.t.D()); set(profile, "j", E1.t.j ? 112 : 110);
        set(profile, "k", new E1.k0(4, 4, 34, 74, 38, 52, 0, 24, List.of(34, 186, 338, 490)));
        set(profile, "l", new E1.r(0, 0, 178, 0, List.of(), "", List.of(), 0, 0));
        I1.I0 fonts = allocate(I1.I0.class);
        for (Field field : I1.I0.class.getDeclaredFields()) if (field.getType() == Typeface.class) set(fonts, field.getName(), Typeface.DEFAULT);
        E1.a app = allocate(E1.a.class); set(app, "a", "phone"); set(app, "b", "Fixture"); set(app, "c", "fixture/phone");
        E1.c entry = new E1.c(app, 1, 2); E1.q6 state = allocate(E1.q6.class);
        for (Field field : E1.q6.class.getDeclaredFields()) {
            if (Map.class.isAssignableFrom(field.getType())) set(state, field.getName(), new LinkedHashMap<>());
            else if (List.class.isAssignableFrom(field.getType())) set(state, field.getName(), new ArrayList<>());
            else if (field.getType() == String.class) set(state, field.getName(), "");
        }
        List<E1.c> nativePage = List.of(entry); set(state, "a", profile); set(state, "b", nativePage); set(state, "o0", 160f);
        Bitmap image = Bitmap.createBitmap(profile.e, profile.e, Bitmap.Config.ARGB_8888); image.eraseColor(0xff336699);
        ConcurrentHashMap<String, Bitmap> images = new ConcurrentHashMap<>(); images.put(app.c, image);
        int[] originalPixels = RendererTransitionsCheck.pixels(image);
        Spy canvas = new Spy(); canvas.translate(7f, 11f); canvas.save();
        int saved = canvas.getSaveCount(); float[] original = matrix(canvas);
        home(canvas, state, fonts, images, 0f);
        check(!canvas.seen.isEmpty() && canvas.seen.get(0)[Matrix.MSCALE_X] < 1f && canvas.seen.get(0)[Matrix.MSCALE_Y] < 1f, "normal native home did not foreshorten Barrel");
        restored(canvas, saved, original, "normal home leaked Canvas state");
        check(context("currentIcon") == null && context("currentFrame") == null, "normal native home leaked frame/icon context");
        for (boolean scaleFailure : new boolean[]{false, true}) {
            canvas.failBitmap = !scaleFailure; canvas.failScale = scaleFailure;
            try { home(canvas, state, fonts, images, scaleFailure ? 0f : .45f); throw new AssertionError("native failure swallowed"); }
            catch (RuntimeException failure) { check(failure == FAILURE, "native failure replaced"); }
            canvas.failBitmap = false; canvas.failScale = false;
            restored(canvas, saved, original, "RENDER_REGRESSION: barrel-canvas (exception leaked outer/native Canvas state)");
            check(context("currentIcon") == null && context("currentFrame") == null, "exception leaked frame/icon context");
        }
        I1.b0 drawn = (I1.b0)I1.h0.i0(state).get(0);
        Object outer = Animaper.beginFrame(canvas, -1, null, null); Animaper.context(state, drawn); Object outerIcon = context("currentIcon");
        check(outerIcon != null, "normal frame context missing");
        int within = canvas.getSaveCount(); float[] withinMatrix = matrix(canvas);
        canvas.failBitmap = true;
        try { icon(canvas, profile, fonts, image); throw new AssertionError("artwork failure swallowed"); }
        catch (RuntimeException failure) { check(failure == FAILURE, "artwork failure replaced"); }
        canvas.failBitmap = false; restored(canvas, within, withinMatrix, "artwork exception leaked per-icon state");
        Spy foreign = new Spy(); icon(foreign, profile, fonts, image);
        check(!foreign.seen.isEmpty() && Arrays.equals(foreign.seen.get(0), matrix(foreign)), "frame context leaked into cache/dock Canvas");
        Object inner = Animaper.beginFrame(canvas, -1, null, null);
        check(context("currentIcon") == null, "nested frame reused outer icon"); Animaper.context(state, drawn);
        Animaper.endFrame(inner); check(context("currentIcon") == outerIcon, "nested frame did not restore outer icon");
        restored(canvas, within, withinMatrix, "nested frame leaked Canvas state");
        final Throwable[] threadFailure = new Throwable[1];
        Thread isolated = new Thread(() -> {
            try {
                Spy own = new Spy(); int count = Animaper.beginIcon(own, profile, 120, 220); Animaper.endIcon(own, count);
                check(own.getMatrix().isIdentity() && context("currentIcon") == null && context("currentFrame") == null, "Barrel context leaked between threads");
            } catch (Throwable failure) { threadFailure[0] = failure; }
        }); isolated.start(); isolated.join(); if (threadFailure[0] != null) throw new AssertionError(threadFailure[0]);
        Animaper.endFrame(outer); restored(canvas, saved, original, "outer frame did not restore original Canvas");
        for (int kind = 0; kind < 7; kind++) {
            Object frame = Animaper.beginFrame(canvas, kind == 0 ? 0 : -1,
                kind == 1 ? new E1.S1(0f, 0f, 1f, 1f, 0) : null, kind == 2 ? allocate(E1.l4.class) : null);
            try {
                if (kind == 3) set(state, "f0", allocate(E1.U1.class));
                if (kind == 4) set(state, "u", allocate(E1.q6.class.getDeclaredField("u").getType()));
                if (kind == 5) set(state, "o0", 0f);
                if (kind == 6) set(state, "o0", Float.NaN);
                Animaper.context(state, drawn); int count = Animaper.beginIcon(canvas, profile, 120, 220);
                check(Arrays.equals(withinMatrix, matrix(canvas)), "Barrel changed edit/folder/launch/settled/invalid geometry"); Animaper.endIcon(canvas, count);
            } finally { set(state, "f0", null); set(state, "u", null); set(state, "o0", 160f); Animaper.endFrame(frame); }
        }
        Object frame = Animaper.beginFrame(canvas, -1, null, null); Animaper.context(state, drawn);
        Files.writeString(new File(ruby, "safe-mode.enabled").toPath(), "1");
        int count = Animaper.beginIcon(canvas, profile, 120, 220); restored(canvas, count + 1, original, "Safe Mode applied pending Barrel transform"); Animaper.endIcon(canvas, count);
        Files.delete(new File(ruby, "safe-mode.enabled").toPath()); Files.delete(new File(ruby, "animaper.enabled").toPath());
        count = Animaper.beginIcon(canvas, profile, 120, 220); check(Arrays.equals(original, matrix(canvas)), "removal applied pending Barrel transform"); Animaper.endIcon(canvas, count); Animaper.endFrame(frame);
        for (Map.Entry<File, byte[]> value : protectedFiles.entrySet()) check(Arrays.equals(value.getValue(), Files.readAllBytes(value.getKey().toPath())), "drawing changed saved mode/layout");
        check(state.b == nativePage && entry.b == 1 && entry.c == 2 && Arrays.equals(originalPixels, RendererTransitionsCheck.pixels(image)) && !image.isRecycled(), "drawing mutated native cells/artwork");
        check(context("currentIcon") == null && context("currentFrame") == null, "final context not cleared");
        System.out.println("Packaged Barrel Canvas: native pixels, exception restoration, nested/foreign/thread isolation, edit/folder/launch/settled guards, Safe Mode/removal and preservation passed");
    }
}
