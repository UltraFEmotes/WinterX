package android.os;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
/** Explicitly drained dispatch queue. Never starts an app, UI loop, timer or process. */
public final class Handler {
    public static final BlockingQueue<Runnable> queue = new LinkedBlockingQueue<>();
    public static boolean reject;
    public Handler(Looper looper) {}
    public boolean post(Runnable run) { if (reject) return false; queue.add(run); return true; }
    public boolean postDelayed(Runnable run, long delay) { return post(run); }
    public static void next() throws Exception {
        Runnable run = queue.poll(5, TimeUnit.SECONDS);
        if (run == null) throw new AssertionError("fixture main dispatch did not arrive");
        run.run();
    }
}
