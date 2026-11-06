package winterx.harlem;

import android.os.Handler;
import android.os.Looper;
import android.view.Choreographer;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import winterx.extension.TweakContext;

/** Keeps Spring's own animation loop running (so Home redraws every frame) while this tweak animates icons. */
final class SpringFrames implements Choreographer.FrameCallback {
    static final String LOOP = "Lcom/guille/spring/LauncherActivity;->startAnimationLoop()V";
    private static volatile Object launcher;
    private static Method start;
    private static Field active;
    private final Runnable frame;
    private boolean running;

    SpringFrames(Runnable frame) { this.frame = frame; }

    /** Remember Spring's activity whenever it starts its loop. */
    static void install(TweakContext context) {
        context.hook(LOOP, call -> { launcher = call.self; return call.proceed(); });
    }

    void start() {
        new Handler(Looper.getMainLooper()).post(() -> {
            if (running) return;
            running = true;
            Choreographer.getInstance().postFrameCallback(this);
        });
    }

    void stop() { running = false; }

    @Override public void doFrame(long frameTimeNanos) {
        if (!running) return;
        try { frame.run(); } catch (RuntimeException ignored) {}
        kick();
        Choreographer.getInstance().postFrameCallback(this);
    }

    /** Leave whatever is open (Settings) for the Home screen, the same way Spring's Home button does. */
    static void home() {
        Object activity = launcher;
        if (activity == null) return;
        new Handler(Looper.getMainLooper()).post(() -> {
            try {
                Method home = activity.getClass().getDeclaredMethod("onHomePressed"); home.setAccessible(true);
                home.invoke(activity);
            } catch (ReflectiveOperationException ignored) {}
        });
    }

    /** Spring stops its loop when nothing of its own is moving; restart it while we still are. */
    static void kick() {
        Object activity = launcher;
        if (activity == null) return;
        try {
            if (start == null) {
                start = activity.getClass().getDeclaredMethod("startAnimationLoop"); start.setAccessible(true);
                active = activity.getClass().getDeclaredField("animLoopActive"); active.setAccessible(true);
            }
            if (!active.getBoolean(activity)) start.invoke(activity);
        } catch (ReflectiveOperationException ignored) {}
    }
}
