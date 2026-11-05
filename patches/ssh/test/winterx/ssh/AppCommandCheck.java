package winterx.ssh;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Parser/SSH lifecycle with in-memory dispatch spies only. No listener, process or app action. */
public final class AppCommandCheck {
    private static final String ID = "sapp:me.example.fixture", SHA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    static void check(boolean ok, String reason) { if (!ok) throw new AssertionError(reason); }
    private static final class Capture {
        final AppCommand command;
        final ByteArrayOutputStream output = new ByteArrayOutputStream(), error = new ByteArrayOutputStream();
        final AtomicInteger exits = new AtomicInteger(), status = new AtomicInteger(-1);
        final CountDownLatch exited = new CountDownLatch(1);
        Capture(AppCommand command) {
            this.command = command; check(command != null, "reserved action command not recognized");
            command.setInputStream(new InputStream() { @Override public int read() { throw new AssertionError("action read stdin"); } });
            command.setOutputStream(output); command.setErrorStream(error);
            command.setExitCallback((code, message, close) -> { status.set(code); exits.incrementAndGet(); exited.countDown(); });
        }
        void start() throws Exception { command.start(null, null); command.start(null, null); }
        String await(int code) throws Exception {
            check(exited.await(12, TimeUnit.SECONDS), "command did not signal exit"); command.destroy(null);
            check(status.get() == code && exits.get() == 1, "wrong/duplicate exit callback: " + status.get());
            check(code == 0 ? error.size() == 0 : output.size() == 0, "wrong SSH response stream");
            return new String((code == 0 ? output : error).toByteArray(), StandardCharsets.UTF_8);
        }
    }
    static String run(String text, AppCommand.Backend backend, int expected) throws Exception {
        Capture capture = new Capture(AppCommand.create(text, backend)); capture.start(); return capture.await(expected);
    }
    public static void main(String[] args) throws Exception {
        AtomicInteger dispatches = new AtomicInteger();
        AppCommand.Backend spy = (verb, target, checksum, cancel) -> {
            dispatches.incrementAndGet(); check(!cancel.get(), "cancelled action dispatched");
            return CompletableFuture.completedFuture(new String[]{"0", verb + "|" + target + "|" + checksum + "\n"});
        };
        check(run("winterx-app list", spy, 0).equals("list||\n"), "list parsing changed");
        check(run("winterx-app open " + ID, spy, 0).equals("open|" + ID + "|\n"), "open parsing changed");
        check(run("winterx-app close " + ID, spy, 0).equals("close|" + ID + "|\n"), "close parsing changed");
        check(run("winterx-app install Example.sapp --sha256 " + SHA + " --confirm", spy, 0).equals("install|Example.sapp|" + SHA + "\n"), "checksum-pinned install parsing changed");
        int before = dispatches.get();
        check(run("winterx-app --help", spy, 0).contains("No Android"), "scope/help missing");
        for (String invalid : new String[]{"winterx-app", "winterx-app list extra", "winterx-app --help extra",
            "winterx-app open mail", "winterx-app open android:com.android.settings", "winterx-app open '" + ID + "'",
            "winterx-app close sapp:../escape", "winterx-app open " + ID + ";rm -rf anywhere", "winterx-app; echo bad",
            "winterx-app list\n", "winterx-app list\u001b[2J", "winterx-app open sapp:me.example.\u202eapp",
            "winterx-app install ../Example.sapp --sha256 " + SHA + " --confirm",
            "winterx-app install Example.sapp --sha256 " + SHA,
            "winterx-app install Example.sapp --sha256 " + SHA.toUpperCase() + " --confirm",
            "winterx-app install Example.sapp --confirm --sha256 " + SHA,
            "winterx-app install Example.apk --sha256 " + SHA + " --confirm",
            "winterx-app install Example.sapp --sha256 " + SHA + " --confirm extra"})
            check(run(invalid, spy, 2).contains("Unsupported"), "invalid arguments accepted: " + invalid);
        StringBuilder longCommand = new StringBuilder("winterx-app open sapp:"); for (int i = 0; i < 9000; i++) longCommand.append('x');
        run(longCommand.toString(), spy, 2);
        check(dispatches.get() == before, "help/invalid requests reached app backend");
        check(AppCommand.create("neofetch", spy) == null && AppCommand.create("winterx-app-other", spy) == null && AppCommand.create(null, spy) == null, "unrelated commands hijacked");
        check(run("winterx-app list", (verb, target, sha, cancel) -> { throw new IOException("private/path/key/details"); }, 3).contains("unavailable"), "backend failure not bounded");
        String safe = run("winterx-app list", (verb, target, sha, cancel) -> CompletableFuture.completedFuture(new String[]{"0", "fixture\u001b[2J\r\u202e\n"}), 0);
        check(!safe.contains("\u001b") && !safe.contains("\r") && !safe.contains("\u202e"), "terminal controls not removed");
        StringBuilder huge = new StringBuilder(); for (int i = 0; i < 20000; i++) huge.append('x');
        run("winterx-app list", (verb, target, sha, cancel) -> CompletableFuture.completedFuture(new String[]{"0", huge.toString()}), 3);
        run("winterx-app list", (verb, target, sha, cancel) -> CompletableFuture.completedFuture(new String[]{"999", "bad"}), 3);
        Capture cancelledBefore = new Capture(AppCommand.create("winterx-app open " + ID, spy));
        cancelledBefore.command.destroy(null); cancelledBefore.start();
        check(cancelledBefore.exits.get() == 0 && dispatches.get() == before, "destroy-before-start dispatched work");
        CountDownLatch queued = new CountDownLatch(1); AtomicReference<AtomicBoolean> token = new AtomicReference<>();
        AtomicInteger acted = new AtomicInteger(); CompletableFuture<String[]> pending = new CompletableFuture<>();
        Capture cancelled = new Capture(AppCommand.create("winterx-app close " + ID, (verb, target, sha, cancel) -> { token.set(cancel); queued.countDown(); return pending; }));
        cancelled.start(); check(queued.await(5, TimeUnit.SECONDS), "cancellation spy did not queue"); cancelled.command.destroy(null);
        if (!token.get().get()) acted.incrementAndGet();
        check(cancelled.await(130).contains("not rolled back") && pending.isCancelled() && acted.get() == 0, "queued cancellation performed an action");
        CountDownLatch timeoutQueued = new CountDownLatch(1); CompletableFuture<String[]> never = new CompletableFuture<>(); AtomicReference<AtomicBoolean> timedToken = new AtomicReference<>();
        Capture timed = new Capture(AppCommand.create("winterx-app open " + ID, (verb, target, sha, cancel) -> { timedToken.set(cancel); timeoutQueued.countDown(); return never; }));
        timed.start(); check(timeoutQueued.await(5, TimeUnit.SECONDS), "timeout spy did not queue");
        check(timed.await(5).contains("may still be in progress") && timedToken.get().get() && never.isCancelled(), "timeout did not cancel queued work or misreported rollback");
        Capture broken = new Capture(AppCommand.create("winterx-app --help", spy));
        broken.command.setOutputStream(new OutputStream() { @Override public void write(int value) throws IOException { throw new IOException("closed fixture stream"); } });
        broken.start(); check(broken.exited.await(5, TimeUnit.SECONDS) && broken.status.get() == 1 && broken.exits.get() == 1, "output failure did not exit once"); broken.command.destroy(null);
        CountDownLatch workers = new CountDownLatch(2); List<Capture> occupied = new ArrayList<>();
        for (int i = 0; i < 6; i++) {
            Capture entry = new Capture(AppCommand.create("winterx-app list", (verb, target, sha, cancel) -> { workers.countDown(); return new CompletableFuture<>(); }));
            occupied.add(entry); entry.start();
        }
        check(workers.await(5, TimeUnit.SECONDS), "bounded worker fixture did not occupy two workers");
        check(run("winterx-app list", spy, 4).contains("queue is full"), "unbounded action queue");
        for (Capture entry : occupied) { entry.command.destroy(null); entry.await(130); }
        System.out.println("SSH app commands: bounded parsing/IDs/checksums/confirmation, no stdin/shell, scoped help, control-safe output, at-most-once exit, failure/cancel/timeout/queue limits passed (backend spies; no app action or listener)");
    }
}
