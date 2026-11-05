package winterx.ssh;

import java.nio.file.Path;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Resource/lifecycle spy. Never creates a socket, process, host key or SSH server. */
public final class SshServerEngine {
    public static final String APP_ABI = "winterx-ssh-app-v1";
    public static final String SHELL_ABI = "winterx-ssh-prompt-v1";
    public static volatile int configured, started, stopped;
    public static volatile boolean blockConfigure, blockStart, failStart;
    public static CountDownLatch entered, proceed;
    public final String fingerprint = "fixture-only";
    public static void reset(boolean configure, boolean start, boolean fail) {
        configured = started = stopped = 0;
        blockConfigure = configure; blockStart = start; failStart = fail;
        entered = new CountDownLatch(1); proceed = new CountDownLatch(1);
    }
    private static void pause() throws Exception {
        entered.countDown();
        if (!proceed.await(10, TimeUnit.SECONDS)) throw new AssertionError("test did not release worker");
    }
    public static SshServerEngine configure(Path root, Path keys, Path host, int port, boolean android) throws Exception {
        if (port != 2222 || !android || !keys.startsWith(root) || !host.startsWith(root)) throw new AssertionError("unsafe adapter arguments");
        configured++;
        if (blockConfigure) pause();
        return new SshServerEngine();
    }
    public void start() throws Exception {
        started++;
        if (blockStart) pause();
        if (failStart) throw new java.io.IOException("fixture start failure");
    }
    public void stop() { stopped++; }
    public boolean running() { return started > stopped && !failStart; }
}
