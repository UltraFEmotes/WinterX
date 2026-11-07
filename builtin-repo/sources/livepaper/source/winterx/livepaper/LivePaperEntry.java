package winterx.livepaper;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import android.app.Activity;
import android.app.ActivityThread;
import android.app.Application;
import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

/**
 * A video as Spring's wallpaper. Spring draws its wallpaper through I1.h0.m, which takes an optional custom wallpaper
 * bitmap: LivePaper hands it the current video frame, and asks Spring's view to redraw as each new frame arrives.
 * The video only plays while the wallpaper is actually on screen.
 */
public final class LivePaperEntry implements NativeTweak, Video.Frames {
    static final String VIEW = "Lx1/N1;->onDraw(Landroid/graphics/Canvas;)V";
    static final String WALLPAPER = "LI1/h0;->m(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/i6;Ljava/util/Map;Landroid/graphics/Bitmap;F)V";
    static final String RESULT = "Lcom/guille/spring/LauncherActivity;->onActivityResult(IILandroid/content/Intent;)V";
    static final int REQUEST = 0x4C50;                       // "LP"; Spring's own request codes are small numbers
    static final long MAX_VIDEO = 300L * 1024 * 1024;

    private TweakContext context;
    private volatile View view;
    private volatile boolean playing = true, drawnThisFrame;
    private volatile long wallpaperSeen;
    private volatile String note;
    private Video video;

    @Override public void start(TweakContext context) {
        this.context = context;
        playing = !"off".equals(read("playing.txt"));
        context.hook(VIEW, call -> {
            view = (View)call.self;
            drawnThisFrame = false;
            return call.proceed();
        });
        context.hook(WALLPAPER, call -> {
            wallpaperSeen = System.currentTimeMillis();
            drawnThisFrame = true;
            Video current = video;
            Bitmap frame = current == null ? null : current.frame();
            if (frame == null || !context.active() || !playing) return call.proceed();
            draw((android.graphics.Canvas)call.args[0], (E1.i6)call.args[2], frame, ((Number)call.args[5]).floatValue());
            return null;
        });
        context.hook(RESULT, call -> {
            if (((Number)call.args[0]).intValue() != REQUEST) return call.proceed();
            Intent data = (Intent)call.args[2];
            if (((Number)call.args[1]).intValue() == Activity.RESULT_OK && data != null && data.getData() != null) {
                Uri file = data.getData();
                note = "Importing…";
                new Thread(() -> { note = importVideo(file); restart(); }, "livepaper-import").start();
            }
            return null;                                     // ours alone; Spring never sees this request
        });
        restart();
    }

    @Override public void stop() { if (video != null) video.stop(); video = null; }

    /** (Re)start playback of the saved video, if there is one. */
    private synchronized void restart() {
        if (video != null) video.stop();
        video = null;
        File file = context.data("wallpaper.mp4");
        if (playing && file.isFile()) { video = new Video(file, this); video.start(); }
        redraw();
    }

    private final android.graphics.Paint paint = new android.graphics.Paint(android.graphics.Paint.FILTER_BITMAP_FLAG);
    private final android.graphics.Rect crop = new android.graphics.Rect();
    private final android.graphics.RectF screen = new android.graphics.RectF();

    /**
     * The frame filling the whole screen, cropped to its shape (like a photo wallpaper), with Spring's zoom: zoom is
     * the scale Spring animates around the centre when apps open and close (1 at rest).
     */
    private void draw(android.graphics.Canvas canvas, E1.i6 profile, Bitmap frame, float zoom) {
        float w = profile.b, h = profile.c;                  // the screen in Spring points
        screen.set(0, 0, w, h);
        float fw = frame.getWidth(), fh = frame.getHeight();
        if (fw / fh > w / h) { int cw = Math.round(fh * w / h); crop.set((int)((fw - cw) / 2), 0, (int)((fw + cw) / 2), (int)fh); }
        else { int ch = Math.round(fw * h / w); crop.set(0, (int)((fh - ch) / 2), (int)fw, (int)((fh + ch) / 2)); }
        int saved = canvas.save();
        if (zoom != 1f) canvas.scale(zoom, zoom, w / 2, h / 2);
        canvas.drawBitmap(frame, crop, screen, paint);
        canvas.restoreToCount(saved);
    }

    // ----- Video.Frames -----

    @Override public void frame() { redraw(); }

    /** Decode only while Spring is on screen and the wallpaper was part of the last frames it drew. */
    @Override public boolean wanted() {
        View v = view;
        if (!context.active() || !playing || v == null || !v.isShown() || !v.hasWindowFocus()) return false;
        return System.currentTimeMillis() - wallpaperSeen < 1000;
    }

    private void redraw() { View v = view; if (v != null) v.postInvalidate(); }

    // ----- Settings -----

    @Override public Object call(String point, Object[] a) {
        if (!context.active()) return null;
        switch (point) {
            case "settings.page": return "main".equals(a[0]) ? page() : null;   // only our own page, never Spring's
            case "settings.tap": tap(String.valueOf(a[1])); return null;
            default: return null;
        }
    }

    private void tap(String row) {
        switch (row) {
            case "choose": choose(); break;
            case "play":
                playing = !playing; write("playing.txt", playing ? "on" : "off"); restart(); break;
            case "remove":
                if (video != null) video.stop();
                video = null;
                context.data("wallpaper.mp4").delete();
                write("name.txt", "");
                note = "Video removed; your normal wallpaper is back";
                redraw();
                break;
            default:
        }
    }

    private void choose() {
        View v = view;
        Activity activity = v != null && v.getContext() instanceof Activity ? (Activity)v.getContext() : null;
        if (activity == null) { note = "Open Spring's Home screen first, then try again"; return; }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("video/*");
        new Handler(Looper.getMainLooper()).post(() -> {
            try { activity.startActivityForResult(intent, REQUEST); }
            catch (RuntimeException noPicker) { note = "This device has no file picker"; }
        });
    }

    private T6 page() {
        String row = "winterx-tw-r/" + context.id() + "/main/";
        boolean has = context.data("wallpaper.mp4").isFile();
        String name = read("name.txt");
        List<V6> rows = new ArrayList<>();
        rows.add(Z3.g(Z3.a, row + "choose", has ? "Choose a Different Video…" : "Choose a Video…", null, null, null, 0x18));
        if (has) {
            rows.add(Z3.g(Z3.a, row + "play", (playing ? "✓ " : "") + "Play Live Wallpaper", null, null, null, 0x18));
            rows.add(Z3.g(Z3.a, row + "remove", "Remove Video", null, null, null, 0x18));
        }
        String footer = note != null ? note
            : has ? "Playing " + (name == null || name.isEmpty() ? "your video" : name) + ", muted and on a loop. It pauses while an app is open."
            : "Pick any video to make it your Home and Lock screen wallpaper. It plays muted, on a loop, and only while the wallpaper is showing.";
        W6 section = new W6("LIVE WALLPAPER", null, footer, null, rows);
        return new T6("winterx-tw-p/" + context.id(), "LivePaper", Collections.singletonList(section));
    }

    /** Copy the picked video into this tweak's own data, atomically, refusing anything over 300 MB. */
    private String importVideo(Uri file) {
        Application app = ActivityThread.currentApplication();
        if (app == null) return "Couldn't import the video";
        String name = "video";
        try (android.database.Cursor row = app.getContentResolver().query(file, new String[]{android.provider.OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (row != null && row.moveToFirst() && row.getString(0) != null) name = row.getString(0);
        } catch (RuntimeException unnamed) {}
        File target = context.data("wallpaper.mp4"), temporary = context.data("wallpaper.mp4.tmp");
        target.getParentFile().mkdirs();
        try (java.io.InputStream in = app.getContentResolver().openInputStream(file)) {
            if (in == null) return "Couldn't open that file";
            long total = 0;
            try (FileOutputStream out = new FileOutputStream(temporary)) {
                byte[] buffer = new byte[256 * 1024];
                for (int n; (n = in.read(buffer)) > 0;) {
                    if ((total += n) > MAX_VIDEO) { out.close(); temporary.delete(); return "That video is over 300 MB"; }
                    out.write(buffer, 0, n);
                }
                out.getFD().sync();
            }
        } catch (Exception failure) { temporary.delete(); return "Couldn't import: " + failure.getClass().getSimpleName(); }
        if (!temporary.renameTo(target)) { temporary.delete(); return "Couldn't save the video"; }
        write("name.txt", name);
        return "✓ " + name + " is your wallpaper now";
    }

    private String read(String name) {
        try { File file = context.data(name); return file.isFile() ? new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8).trim() : null; }
        catch (Exception unavailable) { return null; }
    }
    private void write(String name, String value) {
        try { File file = context.data(name); file.getParentFile().mkdirs(); Files.write(file.toPath(), value.getBytes(StandardCharsets.UTF_8)); }
        catch (Exception ignored) {}
    }
}
