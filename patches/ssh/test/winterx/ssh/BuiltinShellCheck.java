package winterx.ssh;

import java.io.ByteArrayOutputStream;
import java.io.OutputStream;
import java.io.PipedInputStream;
import java.io.PipedOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.sshd.common.channel.PtyMode;
import org.apache.sshd.server.Environment;
import org.apache.sshd.server.Signal;
import org.apache.sshd.server.SignalListener;
import org.apache.sshd.server.command.Command;

/** In-memory interactive sessions. No sockets, OS PTY/shell, app launch or installer. */
public final class BuiltinShellCheck {
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
    private static final class Terminal extends OutputStream {
        final ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        @Override public synchronized void write(int value) { check(bytes.size() < 262144, "unbounded terminal output"); bytes.write(value); notifyAll(); }
        @Override public synchronized void write(byte[] value, int offset, int length) { check(bytes.size() + length < 262144, "unbounded terminal output"); bytes.write(value, offset, length); notifyAll(); }
        synchronized String text() { return new String(bytes.toByteArray(), StandardCharsets.UTF_8); }
        synchronized void await(String value, int count) throws Exception {
            long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
            while (occurrences(text(), value) < count) {
                long left = end - System.nanoTime(); if (left <= 0) throw new AssertionError("terminal output missing: " + value + "\n" + text());
                TimeUnit.NANOSECONDS.timedWait(this, left);
            }
        }
    }
    private static int occurrences(String value, String part) { int count = 0; for (int at = 0; (at = value.indexOf(part, at)) >= 0; at += part.length()) count++; return count; }
    private static final class Env implements Environment {
        final boolean pty;
        SignalListener listener;
        Env(boolean pty) { this.pty = pty; }
        public Map<String, String> getEnv() { return pty ? Collections.singletonMap(ENV_TERM, "xterm-256color") : Collections.emptyMap(); }
        public Map<PtyMode, Integer> getPtyModes() { return Collections.emptyMap(); }
        public void addSignalListener(SignalListener value, Collection<Signal> signals) { listener = value; }
        public void removeSignalListener(SignalListener value) { check(listener == value, "signal listener mismatch"); listener = null; }
    }
    private static final class Session {
        final BuiltinShell shell;
        final PipedOutputStream keyboard = new PipedOutputStream();
        final Terminal terminal = new Terminal();
        final Env environment;
        final CountDownLatch ended = new CountDownLatch(1);
        final AtomicInteger exits = new AtomicInteger();
        Session(boolean pty, BuiltinShell.Factory factory) throws Exception {
            shell = new BuiltinShell(factory); environment = new Env(pty);
            shell.setInputStream(new PipedInputStream(keyboard, 16384)); shell.setOutputStream(terminal); shell.setErrorStream(terminal);
            shell.setExitCallback((code, message, close) -> { exits.incrementAndGet(); ended.countDown(); });
            shell.start(null, environment); shell.start(null, environment); terminal.await("winterx> ", 1);
        }
        void type(String text) throws Exception { keyboard.write(text.getBytes(StandardCharsets.UTF_8)); keyboard.flush(); }
        void end() throws Exception { check(ended.await(10, TimeUnit.SECONDS), "interactive session did not close"); shell.destroy(null); shell.destroy(null); check(exits.get() == 1 && environment.listener == null, "repeated exit or leaked signal listener"); keyboard.close(); }
    }
    public static void main(String[] args) throws Exception {
        AtomicInteger actions = new AtomicInteger(); AtomicReference<AtomicBoolean> cancellation = new AtomicReference<>();
        AtomicReference<CompletableFuture<String[]>> pending = new AtomicReference<>(); CountDownLatch dispatched = new CountDownLatch(1);
        BuiltinShell.Factory factory = line -> {
            Command info = FetchCommand.create(line); if (info != null) return info;
            return AppCommand.create(line, (verb, target, hash, cancelled) -> {
                actions.incrementAndGet();
                if (verb.equals("close")) { cancellation.set(cancelled); CompletableFuture<String[]> value = new CompletableFuture<>(); pending.set(value); dispatched.countDown(); return value; }
                return CompletableFuture.completedFuture(new String[]{"0", "fixture " + verb + "\n"});
            });
        };
        Session session = new Session(true, factory);
        session.type("neofetch\r\n"); session.terminal.await("winterx> ", 2);
        check(session.terminal.text().contains("\u001b[1;94m") && session.terminal.text().contains("----\\---*---/----"), "interactive blue snowflake did not render");
        int mark = session.terminal.text().length();
        session.type("neofetchx\u007f --no-color\r\n"); session.terminal.await("winterx> ", 3);
        String plain = session.terminal.text().substring(mark);
        check(plain.contains("----\\---*---/----") && !plain.contains("\u001b["), "line editing/plain report failed");
        session.type("discard this\u0015help\n"); session.terminal.await("winterx> ", 4); check(session.terminal.text().contains("Ctrl-C"), "Ctrl-U/help failed");
        session.type("winterx-app list\n"); session.terminal.await("winterx> ", 5); check(actions.get() == 1 && session.terminal.text().contains("fixture list"), "interactive app command was not dispatched");
        session.type("winterx-app close sapp:me.example.app\n"); check(dispatched.await(10, TimeUnit.SECONDS), "pending command did not dispatch");
        session.type("\u0003"); session.terminal.await("winterx> ", 6);
        check(cancellation.get().get() && pending.get().isCancelled(), "Ctrl-C did not cancel a queued app action");
        session.type("uname\n"); session.terminal.await("winterx> ", 7); check(session.terminal.text().contains("Unknown WinterX command"), "unknown command reached an OS shell");
        session.type("winterx-app open sapp:me.example.app;bad\n"); session.terminal.await("winterx> ", 8); check(actions.get() == 2, "malformed interactive app command dispatched");
        StringBuilder longLine = new StringBuilder(); for (int i = 0; i < 2000; i++) longLine.append('x');
        session.type(longLine + "\n"); session.terminal.await("winterx> ", 9); check(session.terminal.text().contains("at most 512"), "oversized terminal line accepted");
        session.type("\u001b[Ahelp\n"); session.terminal.await("winterx> ", 10);
        session.type("winterx-app list\u0000\n"); session.terminal.await("winterx> ", 11); check(actions.get() == 2, "terminal control byte dispatched an action");
        session.type("exit\n"); session.end(); check(session.terminal.text().contains("Goodbye."), "exit did not close terminal");
        Session noPty = new Session(false, factory); noPty.type("winterx-info --no-color\n"); noPty.terminal.await("winterx> ", 2);
        check(!noPty.terminal.text().contains("\r") && !noPty.terminal.text().contains("\u001b["), "no-PTY streams got terminal echo/color controls");
        noPty.type("\u0004"); noPty.end();
        Session signal = new Session(true, factory); signal.environment.listener.signal(null, Signal.INT); signal.terminal.await("winterx> ", 2);
        signal.environment.listener.signal(null, Signal.HUP); signal.end();
        System.out.println("Interactive WinterX prompt: blue snowflake/info/app dispatch, PTY/no-PTY streams, editing/CRLF, help/exit, bounded input, control/injection rejection, Ctrl-C cancellation and signal/disconnect cleanup passed (memory streams; no live action/socket/shell)");
    }
}
