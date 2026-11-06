package winterx.gravity;

import android.app.ActivityThread;
import android.app.Application;
import android.graphics.Canvas;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.SystemClock;
import android.view.MotionEvent;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import winterx.extension.MethodHooks;
import winterx.extension.TweakContext;

/**
 * Gravity: shake the phone and the Home icons fall as solid tiles: they tumble, land on corners, tip over and pile up
 * the way the phone is tilted (rigid-body physics, see Physics). Every page falls, each into its own pile, as you
 * scroll to it. Tap an icon to open its app; drag to grab and throw it. Shake again or press Home to put them back.
 */
final class Gravity implements SensorEventListener {
    static final String TOUCH = "Lx1/N1;->onTouchEvent(Landroid/view/MotionEvent;)Z";
    static final float STEP = 1 / 120f, RETURN_SECONDS = 0.6f, GRAVITY = 30f;   // icon widths per second²
    static final float MAX_DRAG = 25f;                                            // icon widths per second
    static final long TAP_MS = 300; static final float TAP_SLOP = 0.15f;         // icon widths
    static final int DOCK = Integer.MIN_VALUE;

    /** One icon: its physics box, its page, and where Spring would draw it unscrolled (top-left, screen units). */
    static final class Icon {
        final Physics.Box box; final int page; final float homeX, homeY; float fromX, fromY, fromAngle;
        Icon(Physics.Box box, int page, float homeX, float homeY) { this.box = box; this.page = page; this.homeX = homeX; this.homeY = homeY; }
    }
    /** What Spring said about the icon it is about to draw. */
    static final class Drawing { final long key; final int page, offset; Drawing(long k, int p, int o) { key = k; page = p; offset = o; } }

    private final TweakContext context;
    private final SpringFrames frames = new SpringFrames(this::step);
    private final Map<Long, Icon> icons = new LinkedHashMap<>();
    private final Map<Integer, Physics> worlds = new HashMap<>();
    private final Map<Integer, List<Icon>> pending = new HashMap<>();
    private final Map<Integer, Float> shifts = new HashMap<>();
    private final ThreadLocal<Drawing> drawing = new ThreadLocal<>();
    private final Random random = new Random();
    private SensorManager sensors;
    private volatile boolean active, returning;
    volatile boolean shakeEnabled = true;
    private float size = 1, width, height, gx = 0, gy = 9.81f, accumulator;
    private long lastStep, returnStart, lastHomeFrame, lastShake, shakeCooldown;
    private int shakes, settledPage = DOCK;
    private float dockTop = Float.MAX_VALUE;                         // icons land on the dock, which stays put
    // touch
    private Icon held; private float targetX, targetY, grabX, grabY, downX, downY; private long downTime;
    private boolean passing, moved;
    private Field mapping; private Method computeMapping;

    Gravity(TweakContext context) { this.context = context; }

    void start() {
        SpringFrames.install(context);
        context.hook(TOUCH, call -> active ? touch(call) : call.proceed());
        Application app = ActivityThread.currentApplication();
        if (app != null) {
            sensors = (SensorManager)app.getSystemService(android.content.Context.SENSOR_SERVICE);
            Sensor accelerometer = sensors == null ? null : sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            if (accelerometer != null) sensors.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    void stop() {
        if (sensors != null) sensors.unregisterListener(this);
        active = false; returning = false; frames.stop();
    }

    boolean active() { return active || returning; }

    /** Settings and shake both come here. Pages fall as they are shown. */
    synchronized void toggle() {
        if (active) {
            active = false; returning = true; returnStart = SystemClock.uptimeMillis(); held = null; passing = false;
            for (Icon icon : icons.values()) {
                icon.fromX = icon.box.x * size - size / 2; icon.fromY = icon.box.y * size - size / 2; icon.fromAngle = icon.box.angle;
            }
            return;
        }
        if (returning) return;
        icons.clear(); worlds.clear(); pending.clear(); shifts.clear(); dockTop = Float.MAX_VALUE; lastStep = 0;
        active = true;
        frames.start();
    }

    // ----- drawing (render.home.icon-context, render.icon.begin) -----

    /**
     * Spring names each Home icon before drawing it: its page and grid cell, and (from the scroll position) how far
     * that page is currently scrolled, using the same point-to-pixel conversion as Spring's own page renderer.
     */
    void context(E1.q6 state, I1.b0 entry) {
        if (state == null || state.a == null || entry == null || entry.a == null) { drawing.remove(); return; }
        int offset = Math.round((entry.e * 320f - state.o0) * I1.G0.p(state.a));
        drawing.set(new Drawing(((long)(entry.e + 1) << 40) ^ ((long)entry.a.b << 20) ^ entry.a.c, entry.e, offset));
    }

    synchronized Integer beginIcon(Canvas canvas, E1.i6 profile, int x, int y) {
        Drawing named = drawing.get(); drawing.remove();
        if (!active && !returning) return null;
        lastHomeFrame = SystemClock.uptimeMillis();
        size = profile.e; width = profile.b; height = profile.c;
        if (named == null) { dockTop = Math.min(dockTop, y); return null; }   // the dock is the floor, not a falling icon
        int page = named.page;
        float shift = named.offset;                                          // how far this page is scrolled
        if (named != null) { shifts.put(page, shift); if (shift == 0) settledPage = page; }
        long key = named != null ? named.key : ((long)x << 32) ^ (y & 0xffffffffL);   // the dock doesn't scroll
        Icon icon = icons.get(key);
        if (icon == null) {
            if (!active) return null;
            // A page falls once it is fully on screen (not mid-scroll, where page effects also move icons).
            boolean settled = shift == 0 && !worlds.containsKey(page);
            if (!settled || x < 0 || y < 0 || x + size > width || y + size > height) return null;
            int world = page;
            Physics.Box box = new Physics.Box((x + size / 2) / size, (y + size / 2) / size, 1, 1, 1);
            box.vx = (random.nextFloat() - .5f) * 3; box.vy = -random.nextFloat() * 3; box.w = (random.nextFloat() - .5f) * 4;
            icon = new Icon(box, world, x - shift, y);
            icons.put(key, icon);
            pending.computeIfAbsent(world, p -> new ArrayList<>()).add(icon);
        }
        float pageShift = icon.page == page ? shift : shifts.getOrDefault(icon.page, 0f);
        float drawX, drawY, angle;
        if (returning) {
            float t = Math.min(1f, (SystemClock.uptimeMillis() - returnStart) / (RETURN_SECONDS * 1000f)), e = 1 - (1 - t) * (1 - t) * (1 - t);
            drawX = icon.fromX + (icon.homeX - icon.fromX) * e; drawY = icon.fromY + (icon.homeY - icon.fromY) * e; angle = icon.fromAngle * (1 - e);
        } else {
            drawX = icon.box.x * size - size / 2; drawY = icon.box.y * size - size / 2; angle = icon.box.angle;
        }
        int saved = canvas.save();
        canvas.translate(drawX + (named != null ? pageShift : 0) - x, drawY - y);
        canvas.rotate((float)Math.toDegrees(angle), x + size / 2f, y + size / 2f);
        return saved;
    }

    // ----- simulation -----

    private synchronized void step() {
        long now = SystemClock.uptimeMillis();
        if (returning && now - returnStart >= RETURN_SECONDS * 1000) { returning = false; icons.clear(); worlds.clear(); }
        if (!active) { if (!returning) frames.stop(); return; }
        for (Map.Entry<Integer, List<Icon>> page : pending.entrySet()) {
            Physics world = worlds.get(page.getKey());
            if (world == null) { world = walls(); worlds.put(page.getKey(), world); }
            for (Icon icon : page.getValue()) world.add(icon.box);
        }
        pending.clear();
        float dt = lastStep == 0 ? 1 / 60f : Math.min(0.05f, (now - lastStep) / 1000f);
        lastStep = now;
        float norm = (float)Math.max(0.1, Math.hypot(gx, gy));
        accumulator += dt;
        while (accumulator >= STEP) {
            if (held != null) {                              // pull the held icon to the finger; it still pushes others
                Physics.Box box = held.box;
                float vx = (targetX - grabX - box.x) * 18, vy = (targetY - grabY - box.y) * 18, speed = (float)Math.hypot(vx, vy);
                if (speed > MAX_DRAG) { vx *= MAX_DRAG / speed; vy *= MAX_DRAG / speed; }   // strong throws, not explosions
                box.vx = vx; box.vy = vy; box.w *= 0.8f;
            }
            for (Physics world : worlds.values()) { world.gx = gx / norm * GRAVITY; world.gy = gy / norm * GRAVITY; world.step(STEP); }
            accumulator -= STEP;
        }
    }

    /** A page's world: the screen's edges as static walls. */
    private Physics walls() {
        Physics world = new Physics();
        float w = width / size, h = Math.min(height, dockTop) / size, thick = 10;
        world.add(new Physics.Box(w / 2, h + thick / 2, w + 2 * thick, thick, 0));       // floor
        world.add(new Physics.Box(w / 2, -thick / 2, w + 2 * thick, thick, 0));          // ceiling
        world.add(new Physics.Box(-thick / 2, h / 2, thick, h + 2 * thick, 0));          // left
        world.add(new Physics.Box(w + thick / 2, h / 2, thick, h + 2 * thick, 0));       // right
        return world;
    }

    // ----- touch (x1.N1.onTouchEvent) -----

    /**
     * A drag that starts on a loose icon grabs and throws it; a quick tap on one opens its app (replayed to Spring at
     * the icon's real place on the grid); every other touch goes to Spring, so pages still scroll.
     */
    private Object touch(MethodHooks.Call call) throws Throwable {
        MotionEvent event = (MotionEvent)call.args[0];
        float[] tap = null;
        synchronized (this) {
            if (SystemClock.uptimeMillis() - lastHomeFrame > 250) return call.proceed();   // not on Home
            float[] point = springPoint(call.self, event);
            if (point == null) return call.proceed();
            int action = event.getActionMasked();
            boolean onScreen = point[0] >= 0 && point[1] >= 0 && point[0] <= width && point[1] <= height;
            if (!onScreen) {
                if (action == MotionEvent.ACTION_DOWN) toggle();            // Home button: put everything back
                return call.proceed();
            }
            float y = point[1] / size;
            if (action == MotionEvent.ACTION_DOWN) {
                held = null; passing = true;
                for (Icon icon : icons.values()) {
                    float x = (point[0] - (icon.page == DOCK ? 0 : shifts.getOrDefault(icon.page, 0f))) / size;
                    if (icon.page == settledPage && icon.box.contains(x, y)) { held = icon; grabX = x - icon.box.x; grabY = y - icon.box.y; targetX = x; targetY = y; }
                }
                if (held != null) { passing = false; moved = false; downX = point[0]; downY = point[1]; downTime = SystemClock.uptimeMillis(); }
            }
            if (passing) {
                if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) passing = false;
                return call.proceed();
            }
            if (held == null) return Boolean.TRUE;
            float x = (point[0] - shifts.getOrDefault(held.page, 0f)) / size;
            if (Math.hypot(point[0] - downX, point[1] - downY) > TAP_SLOP * size) moved = true;
            targetX = x; targetY = y;
            if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) {
                if (action == MotionEvent.ACTION_UP && !moved && SystemClock.uptimeMillis() - downTime < TAP_MS) {
                    held.box.vx = held.box.vy = 0;
                    tap = rawPoint(call.self, held.homeX + size / 2, held.homeY + size / 2);
                }
                held = null;                                                // otherwise it flies on with the finger's speed
            }
        }
        if (tap != null) {                                                  // Spring opens the app at its grid place
            long now = SystemClock.uptimeMillis();
            MotionEvent down = MotionEvent.obtain(now, now, MotionEvent.ACTION_DOWN, tap[0], tap[1], 0);
            MotionEvent up = MotionEvent.obtain(now, now + 50, MotionEvent.ACTION_UP, tap[0], tap[1], 0);
            try { call.original(down); call.original(up); } finally { down.recycle(); up.recycle(); }
        }
        return Boolean.TRUE;
    }

    private I1.i1 screenMapping(Object screen) {
        try {
            if (mapping == null) {
                mapping = screen.getClass().getDeclaredField("g"); mapping.setAccessible(true);
                computeMapping = screen.getClass().getDeclaredMethod("c"); computeMapping.setAccessible(true);
            }
            Object value = mapping.get(screen);
            if (value == null) value = computeMapping.invoke(screen);
            return value instanceof I1.i1 ? (I1.i1)value : null;
        } catch (ReflectiveOperationException unavailable) { return null; }
    }

    /** Spring maps touches with (event - offset) / scale. */
    private float[] springPoint(Object screen, MotionEvent event) {
        I1.i1 map = screenMapping(screen);
        return map == null ? null : new float[]{(event.getX() - map.b) / map.a, (event.getY() - map.c) / map.a};
    }

    private float[] rawPoint(Object screen, float x, float y) {
        I1.i1 map = screenMapping(screen);
        return map == null ? null : new float[]{x * map.a + map.b, y * map.a + map.c};
    }

    // ----- shake and tilt -----

    @Override public void onSensorChanged(SensorEvent event) {
        float x = event.values[0], y = event.values[1], z = event.values[2];
        gx = -x; gy = y;                                                      // fall the way the phone is tilted
        double force = Math.sqrt(x * x + y * y + z * z) / SensorManager.GRAVITY_EARTH;
        long now = SystemClock.uptimeMillis();
        if (force > 2.3 && now >= shakeCooldown) {
            shakes = now - lastShake < 600 ? shakes + 1 : 1;
            lastShake = now;
            if (shakes >= 2) { shakes = 0; shakeCooldown = now + 1000; if (shakeEnabled) toggle(); }   // two jolts = a shake
        }
    }

    @Override public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
