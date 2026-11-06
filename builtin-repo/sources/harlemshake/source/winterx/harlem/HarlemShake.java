package winterx.harlem;

import android.graphics.Canvas;
import android.media.MediaPlayer;
import android.os.SystemClock;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import winterx.extension.TweakContext;

/**
 * The 2013 Harlem Shake tweak, for Spring. One icon dances alone; at the drop every icon joins in with a random
 * move until the song ends. Timings and the three moves follow FilippoBiga's original (VLMHarlemShake): the drop is
 * 15.5 s in, each icon gets style rand() % 3 with a random seed, and the loner uses the third style.
 */
final class HarlemShake {
    static final long DROP_MS = 15500, DEFAULT_SONG_MS = 30563;
    static final float TWO_PI = (float)(Math.PI * 2);

    /** One dancing icon: its move, its seed in [0, 1), and when it started. */
    static final class Dancer { final int style; final float seed; final long start; Dancer(int s, float r, long t) { style = s; seed = r; start = t; } }

    private final TweakContext context;
    private final SpringFrames frames = new SpringFrames(this::tick);
    private final Map<Long, Dancer> dancers = new HashMap<>();
    private final List<Long> seen = new ArrayList<>();
    private final Random random = new Random();
    private MediaPlayer player;
    private volatile boolean wanted, dancing;
    private long started, songMs = DEFAULT_SONG_MS;
    private Long loner;
    private boolean dropped;

    HarlemShake(TweakContext context) { this.context = context; }

    void start() { SpringFrames.install(context); }
    void stop() { finish(); frames.stop(); }
    boolean busy() { return wanted || dancing; }

    File song() { return context.data("song.mp3"); }

    /** Starts on the next Home frame (like the original's Activator event), or stops a dance in progress. */
    synchronized void toggle() {
        if (busy()) { finish(); return; }
        wanted = true; seen.clear(); dancers.clear(); loner = null; dropped = false;
        frames.start();
    }

    private synchronized void begin(long now) {
        wanted = false; dancing = true; started = now;
        loner = seen.isEmpty() ? null : seen.get(random.nextInt(seen.size()));
        if (loner != null) dancers.put(loner, new Dancer(2, random.nextFloat(), now));
        songMs = DEFAULT_SONG_MS;
        try {
            File song = song();
            if (song.isFile()) {
                player = new MediaPlayer();
                player.setDataSource(song.getPath());
                player.prepare();
                songMs = player.getDuration() > 0 ? player.getDuration() : DEFAULT_SONG_MS;
                player.start();
            }
        } catch (Exception noSong) { releasePlayer(); }               // dance in silence
    }

    private synchronized void tick() {
        long now = SystemClock.uptimeMillis();
        if (wanted && !seen.isEmpty()) begin(now);
        if (!dancing) { if (!wanted) frames.stop(); return; }
        long t = now - started;
        if (!dropped && t >= DROP_MS) {
            dropped = true;
            for (Long key : seen) dancers.put(key, new Dancer(random.nextInt(3), random.nextFloat(), now));
        }
        if (t >= songMs) finish();
    }

    private synchronized void finish() {
        wanted = false; dancing = false; dancers.clear(); seen.clear();
        releasePlayer();
    }

    private void releasePlayer() {
        if (player == null) return;
        try { player.stop(); } catch (RuntimeException ignored) {}
        player.release(); player = null;
    }

    // ----- drawing (render.icon.begin) -----

    synchronized Integer beginIcon(Canvas canvas, E1.i6 profile, int x, int y) {
        if (!wanted && !dancing) return null;
        long key = ((long)x << 32) ^ (y & 0xffffffffL);
        if (wanted && !seen.contains(key)) seen.add(key);
        Dancer dancer = dancers.get(key);
        if (dancer == null) return null;
        float size = profile.e, cx = x + size / 2f, cy = y + size / 2f, unit = size / 57f;   // the original's moves are in 57-pt icon units
        float t = (SystemClock.uptimeMillis() - dancer.start) / 1000f;
        int saved = canvas.save();
        switch (dancer.style) {
            case 0: styleOne(canvas, t, dancer.seed, cx, cy); break;
            case 1: styleTwo(canvas, t, dancer.seed, cx, cy); break;
            default: styleThree(canvas, t, dancer.seed, unit); break;
        }
        return saved;
    }

    /** Style one: a full spin (direction from the seed) over 1 + seed s, then a 1 → 1.2 pulse of 0.5 + seed s that reverses. */
    static void styleOne(Canvas canvas, float t, float seed, float cx, float cy) {
        float spin = 1 + seed, pulse = 0.5f + seed, period = spin + 2 * pulse, local = t % period;
        if (local < spin) {
            float turn = TWO_PI * local / spin;
            canvas.rotate((float)Math.toDegrees(seed < 0.5f ? TWO_PI - turn : turn), cx, cy);
        } else {
            float u = (local - spin) / pulse, scale = 1 + 0.2f * (u <= 1 ? u : 2 - u);
            canvas.scale(scale, scale, cx, cy);
        }
    }

    /** Style two: squash and stretch keyframes at 0, 0.4, 0.7, 1 of a 1 + seed s loop, eased. */
    static void styleTwo(Canvas canvas, float t, float seed, float cx, float cy) {
        float duration = 1 + seed, u = (t % duration) / duration, amount = 0.15f + 0.3f * seed;
        float[] times = {0, 0.4f, 0.7f, 1};
        float[][] scales = {{1, 1}, {1 + amount, 1 - amount}, {1 - amount, 1 + amount}, {1, 1}};
        float[] s = keyframe(times, scales, u);
        canvas.scale(s[0], s[1], cx, cy);
    }

    /** Style three: a ±(10 + 20·seed)-point jiggle through keyframes at 0, .1, .3, .4, .5, .7, .8, 1 of a 1 + seed s loop. */
    static void styleThree(Canvas canvas, float t, float seed, float unit) {
        float duration = 1 + seed, u = (t % duration) / duration, m = (10 + 20 * seed) * unit;
        float[] times = {0, 0.1f, 0.3f, 0.4f, 0.5f, 0.7f, 0.8f, 1};
        float[][] offsets = {{0, 0}, {m, 0}, {-m, 0}, {m, 0}, {0, 0}, {0, m}, {0, -m}, {0, 0}};
        float[] d = keyframe(times, offsets, u);
        canvas.translate(d[0], d[1]);
    }

    /** Linear-in-time keyframes with ease-in-out between each pair, like CAKeyframeAnimation with ease timing. */
    static float[] keyframe(float[] times, float[][] values, float u) {
        for (int i = 1; i < times.length; i++) {
            if (u > times[i]) continue;
            float span = times[i] - times[i - 1], f = span <= 0 ? 1 : (u - times[i - 1]) / span;
            f = f * f * (3 - 2 * f);
            return new float[]{values[i - 1][0] + (values[i][0] - values[i - 1][0]) * f, values[i - 1][1] + (values[i][1] - values[i - 1][1]) * f};
        }
        return values[values.length - 1];
    }
}
