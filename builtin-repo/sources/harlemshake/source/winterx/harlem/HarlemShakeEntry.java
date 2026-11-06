package winterx.harlem;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import android.app.ActivityThread;
import android.app.Application;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.util.Arrays;
import java.util.Collections;
import java.util.Locale;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

public final class HarlemShakeEntry implements NativeTweak {
    static final long MAX_SONG = 20L * 1024 * 1024;
    private TweakContext context;
    private HarlemShake shake;
    private String note;

    @Override public void start(TweakContext context) {
        this.context = context;
        shake = new HarlemShake(context);
        shake.start();
        FilePicker.install(context);
    }

    @Override public void stop() { if (shake != null) shake.stop(); }

    @Override public Object call(String point, Object[] a) {
        if (!context.active()) return null;
        switch (point) {
            case "render.icon.begin": return shake.beginIcon((android.graphics.Canvas)a[0], (E1.i6)a[1], ((Number)a[2]).intValue(), ((Number)a[3]).intValue());
            case "render.icon.end": return null;                   // the engine restores the canvas it saved
            case "cache.tiles-allowed": return !shake.busy();        // every icon draws separately while dancing
            case "settings.page": return "main".equals(a[0]) ? page() : null;   // only our own page, never Spring's
            case "settings.tap":
                if ("dance".equals(a[1])) { boolean starting = !shake.busy(); shake.toggle(); if (starting) SpringFrames.home(); }
                else if ("song".equals(a[1])) pickSong();
                return null;
            default: return null;
        }
    }

    private T6 page() {
        String row = "winterx-tw-r/" + context.id() + "/main/";
        V6 dance = Z3.g(Z3.a, row + "dance", shake.busy() ? "Stop dancing" : "Do the Harlem Shake", null, null, null, 0x18);
        String songTitle = note != null ? note : shake.song().isFile() ? "✓ Song ready" : "Import song";
        V6 song = Z3.g(Z3.a, row + "song", songTitle, null, null, null, 0x18);
        W6 section = new W6("HARLEM SHAKE", null,
            "Tap Do the Harlem Shake and Settings closes to start the dance on your Home screen. Tap the song row to choose a different song.",
            null, Arrays.asList(dance, song));
        return new T6("winterx-tw-p/" + context.id(), "Harlem Shake", Collections.singletonList(section));
    }

    /** Choose a song with the system file picker; without one, fall back to the harlemshake folder. */
    private void pickSong() {
        boolean opened = FilePicker.open("audio/*", file -> new Thread(() -> note = copySong(file), "harlem-import").start());
        if (!opened) note = importSong();
    }

    private String copySong(android.net.Uri file) {
        Application app = ActivityThread.currentApplication();
        if (app == null) return "Couldn't import the song";
        String name = "song";
        try (android.database.Cursor row = app.getContentResolver().query(file, new String[]{android.provider.OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (row != null && row.moveToFirst() && row.getString(0) != null) name = row.getString(0);
        } catch (RuntimeException unnamed) {}
        try (java.io.InputStream in = app.getContentResolver().openInputStream(file)) {
            if (in == null) return "Couldn't open that file";
            return save(in, name);
        } catch (Exception failure) { return "Couldn't import: " + failure.getClass().getSimpleName(); }
    }

    /** Write a song to this tweak's data atomically, refusing anything over 20 MB. */
    private String save(java.io.InputStream in, String name) throws java.io.IOException {
        File target = shake.song(), temporary = new File(target.getPath() + ".tmp");
        target.getParentFile().mkdirs();
        long total = 0;
        try (FileOutputStream out = new FileOutputStream(temporary)) {
            byte[] buffer = new byte[65536];
            for (int n; (n = in.read(buffer)) > 0;) {
                if ((total += n) > MAX_SONG) { out.close(); temporary.delete(); return "That song is over 20 MB"; }
                out.write(buffer, 0, n);
            }
            out.getFD().sync();
        }
        if (!temporary.renameTo(target)) return "Couldn't save the song";
        return "✓ Imported " + name;
    }

    /** Copy the first MP3 found in Spring's external harlemshake folder into this tweak's own data. */
    private String importSong() {
        try {
            Application app = ActivityThread.currentApplication();
            File folder = app == null ? null : app.getExternalFilesDir("harlemshake");
            File[] files = folder == null ? null : folder.listFiles();
            File found = null;
            if (files != null) for (File file : files)
                if (file.isFile() && file.getName().toLowerCase(Locale.ROOT).endsWith(".mp3") && file.length() <= MAX_SONG) { found = file; break; }
            if (found == null) return "No MP3 in the harlemshake folder";
            try (FileInputStream in = new FileInputStream(found)) { return save(in, found.getName()); }
        } catch (Exception failure) { return "Couldn't import: " + failure.getClass().getSimpleName(); }
    }
}
