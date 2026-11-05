package winterx.animaper;

import android.graphics.Canvas;
import java.io.File;

/** Spring 0.8.1 rendering adapter for Animaper. */
public final class Animaper {
    public static final String BARREL_ABI = "animaper-barrel-v1";
    private static volatile Boolean barrelSupport;
    private static String cachedMode = "wave";
    private static long lastRead = -500;
    private static File cachedRoot;
    private static final ThreadLocal<Icon> currentIcon = new ThreadLocal<>();
    private static final ThreadLocal<Frame> currentFrame = new ThreadLocal<>();
    private static final class Frame {
        final Canvas canvas;
        final int saved;
        final boolean eligible;
        final Icon previousIcon;
        final Frame previousFrame;
        Frame(Canvas canvas, int saved, boolean eligible, Icon previousIcon, Frame previousFrame) {
            this.canvas = canvas; this.saved = saved; this.eligible = eligible;
            this.previousIcon = previousIcon; this.previousFrame = previousFrame;
        }
    }
    private static final class Icon {
        final E1.i6 profile;
        final Effects.Barrel transform;
        Icon(E1.i6 profile, Effects.Barrel transform) { this.profile = profile; this.transform = transform; }
    }
    private Animaper() {}
    private static synchronized String mode() {
        try {
            if (!AnimaperSettings.enabled()) return null;
            File dir = AnimaperSettings.folder();
            long now = android.os.SystemClock.elapsedRealtime();
            if (!dir.equals(cachedRoot) || now - lastRead >= 500 || now < lastRead) {
                cachedMode = AnimaperSettings.current(); lastRead = now; cachedRoot = dir;
            }
            return cachedMode;
        } catch (Exception ignored) { return null; }
    }
    static synchronized void invalidate() { cachedRoot = null; }
    public static boolean barrelSupported() {
        Boolean supported = barrelSupport;
        if (supported != null) return supported;
        try {
            I1.h0.class.getDeclaredMethod("winterxStockK", E1.q6.class, long.class, E1.i6.class, float.class, int.class,
                I1.d0.class, E1.S1.class, E1.l4.class, A.o.class, I1.I0.class, java.util.Map.class,
                java.util.concurrent.ConcurrentHashMap.class, android.graphics.Paint.class, float.class, Canvas.class);
            I1.h0.class.getDeclaredMethod("winterxStockArtwork", Canvas.class, android.graphics.Paint.class, E1.i6.class,
                I1.I0.class, java.util.Map.class, android.graphics.Bitmap.class, String.class, int.class, int.class,
                boolean.class, boolean.class, I1.Z.class, String.class);
            barrelSupport = Boolean.TRUE;
        } catch (Exception | LinkageError unavailable) { barrelSupport = Boolean.FALSE; }
        return barrelSupport;
    }
    public static boolean barrelEnabled() { return barrelSupported() && "barrel".equals(mode()); }
    public static M1.b location(E1.i6 profile, E1.c entry, int page, int pageOffset) {
        M1.b point = winterx.layout.SpringHooks.location(profile, entry, page);
        String mode = mode();
        if (mode == null || "barrel".equals(mode) || profile.b <= 0 || pageOffset == 0) return point;
        int[] delta = Effects.offset(mode, (float)pageOffset / profile.b, entry.b, entry.c, profile.b, profile.e);
        return new M1.b(Integer.valueOf(((Number)point.h).intValue() + delta[0]),
                         Integer.valueOf(((Number)point.w).intValue() + delta[1]));
    }
    /** Normal home rendering only; nested frames restore the previous context. */
    public static Object beginFrame(Canvas canvas, long nativeTime, E1.S1 folderMotion, E1.l4 launchMotion) {
        int saved = canvas.save();
        try {
            Frame frame = new Frame(canvas, saved, nativeTime < 0 && folderMotion == null && launchMotion == null,
                currentIcon.get(), currentFrame.get());
            currentFrame.set(frame); currentIcon.remove(); return frame;
        } catch (RuntimeException | Error failure) { canvas.restoreToCount(saved); throw failure; }
    }
    public static void endFrame(Object token) {
        if (!(token instanceof Frame)) { currentIcon.remove(); currentFrame.remove(); return; }
        Frame frame = (Frame)token;
        try { frame.canvas.restoreToCount(frame.saved); }
        finally {
            if (frame.previousIcon == null) currentIcon.remove(); else currentIcon.set(frame.previousIcon);
            if (frame.previousFrame == null) currentFrame.remove(); else currentFrame.set(frame.previousFrame);
        }
    }
    public static void context(E1.q6 state, I1.b0 entry) {
        currentIcon.remove();
        Frame frame = currentFrame.get();
        if (frame == null || !frame.eligible || !barrelEnabled() || state == null || entry == null || state.a == null || state.a.b <= 0 || state.a.e <= 0 ||
            entry.e < 0 || state.f0 != null || state.u != null || !Float.isFinite(state.o0)) return;
        E1.i6 profile = state.a;
        // Match Spring i0's point-to-pixel page offset, leaving its linear scroll intact.
        int offset = Math.round((entry.e * 320f - state.o0) * I1.G0.p(profile));
        float progress = (float)offset / profile.b;
        if (progress == 0 || Math.abs(progress) >= 1f) return;
        currentIcon.set(new Icon(profile, Effects.barrel(progress, (float)entry.b - offset + profile.e * .5f, profile.b)));
    }
    /** Affine tangent/depth approximation; icon, label, shadow and badge move together. */
    public static int beginIcon(Canvas canvas, E1.i6 profile, int x, int y) {
        int saved = canvas.save();
        try {
            Icon icon = currentIcon.get();
            Frame frame = currentFrame.get();
            if (icon != null && frame != null && frame.canvas == canvas && icon.profile == profile && barrelEnabled()) {
                Effects.Barrel transform = icon.transform;
                canvas.translate(transform.shiftX, 0f);
                canvas.scale(transform.scaleX, transform.scaleY, x + profile.e * .5f, y + profile.e * .5f);
            }
        } catch (RuntimeException | Error failure) { canvas.restoreToCount(saved); throw failure; }
        return saved;
    }
    public static void endIcon(Canvas canvas, int saved) { canvas.restoreToCount(saved); }
}
