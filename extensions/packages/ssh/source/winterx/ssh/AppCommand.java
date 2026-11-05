package winterx.ssh;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Future;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.apache.sshd.server.Environment;
import org.apache.sshd.server.ExitCallback;
import org.apache.sshd.server.channel.ChannelSession;
import org.apache.sshd.server.command.Command;

/** Bounded in-process Spring-app exec requests. Never reads stdin or launches a shell/process. */
final class AppCommand implements Command {
    interface Backend {
        CompletableFuture<String[]> submit(String verb, String target, String sha256, AtomicBoolean cancelled) throws Exception;
    }
    private static final String NAME = "winterx-app";
    private static final String USAGE = "WinterX guarded Spring-app actions\n"
        + "Usage: winterx-app list\n"
        + "       winterx-app open sapp:com.example.app\n"
        + "       winterx-app close sapp:com.example.app\n"
        + "       winterx-app install example.sapp --sha256 <64 lowercase hex> --confirm\n"
        + "Upload installs to ruby/ssh/inbox first. New apps only; native Developer Mode is required.\n"
        + "No Android APK/system-app control, root, Spring restart or automatic retry.\n";
    private static final ThreadPoolExecutor WORKER = new ThreadPoolExecutor(0, 2, 30, TimeUnit.SECONDS,
        new ArrayBlockingQueue<Runnable>(4), run -> {
            Thread thread = new Thread(run, "WinterX-SSH-app-command"); thread.setDaemon(true); return thread;
        }, new ThreadPoolExecutor.AbortPolicy());
    private final Backend backend;
    private final String verb, target, sha256;
    private final boolean help, invalid;
    private final AtomicBoolean started = new AtomicBoolean(), completed = new AtomicBoolean(), cancelled = new AtomicBoolean();
    private volatile Future<?> task;
    private volatile CompletableFuture<String[]> pending;
    private OutputStream output, error;
    private ExitCallback callback;

    private AppCommand(Backend backend, String verb, String target, String sha256, boolean help, boolean invalid) {
        this.backend = backend; this.verb = verb; this.target = target; this.sha256 = sha256; this.help = help; this.invalid = invalid;
    }
    @SuppressWarnings("unchecked")
    private static CompletableFuture<String[]> nativeSubmit(String verb, String target, String sha256, AtomicBoolean cancelled) throws Exception {
        Class<?> type = Class.forName("winterx.ssh.SshActions");
        return (CompletableFuture<String[]>)type.getMethod("submit", String.class, String.class, String.class, AtomicBoolean.class)
            .invoke(null, verb, target, sha256, cancelled);
    }
    static AppCommand create(String command) { return create(command, AppCommand::nativeSubmit); }
    static AppCommand create(String command, Backend backend) {
        if (command == null) return null;
        String value = command.trim();
        if (!value.startsWith(NAME)) return null;
        if (value.length() > NAME.length()) {
            char next = value.charAt(NAME.length());
            if (Character.isLetterOrDigit(next) || next == '-' || next == '_' || next == '.') return null;
        }
        boolean unsafe = command.length() > 512;
        for (int i = 0; i < command.length(); i++) {
            char c = command.charAt(i); if ((c < 32 && c != '\t') || c > 126) unsafe = true;
        }
        String[] tokens = unsafe ? new String[]{NAME} : value.split("[ \\t]+", 7);
        String verb = tokens.length > 1 ? tokens[1] : "", target = tokens.length > 2 ? tokens[2] : "", sha = "";
        boolean help = !unsafe && tokens.length == 2 && verb.equals("--help");
        boolean valid = !unsafe && tokens[0].equals(NAME) && (help || tokens.length == 2 && verb.equals("list") ||
            tokens.length == 3 && (verb.equals("open") || verb.equals("close")) && target.length() <= 125 &&
                target.matches("sapp:[a-z0-9]+(?:[.-][a-z0-9]+)+") ||
            tokens.length == 6 && verb.equals("install") && target.length() <= 64 &&
                target.matches("[A-Za-z0-9][A-Za-z0-9._-]*\\.sapp") && !target.contains("..") &&
                tokens[3].equals("--sha256") && tokens[4].matches("[0-9a-f]{64}") && tokens[5].equals("--confirm"));
        if (valid && verb.equals("install")) sha = tokens[4];
        return new AppCommand(backend, verb, target, sha, help, !valid);
    }
    @Override public void setInputStream(InputStream input) { /* No stdin, interactive input, or shell. */ }
    @Override public void setOutputStream(OutputStream output) { this.output = output; }
    @Override public void setErrorStream(OutputStream error) { this.error = error; }
    @Override public void setExitCallback(ExitCallback callback) { this.callback = callback; }
    @Override public void start(ChannelSession channel, Environment environment) throws IOException {
        if (cancelled.get() || !started.compareAndSet(false, true)) return;
        if (output == null || callback == null) throw new IOException("SSH output/callback unavailable");
        if (invalid || help) { finish(invalid ? 2 : 0, (invalid ? "Unsupported Spring-app arguments.\n" : "") + USAGE); return; }
        try { task = WORKER.submit(this::run); }
        catch (java.util.concurrent.RejectedExecutionException busy) { finish(4, "Spring-app command queue is full. No automatic retry.\n"); }
        if (cancelled.get() && task != null) task.cancel(true);
    }
    private void run() {
        if (cancelled.get()) return;
        try {
            pending = backend.submit(verb, target, sha256, cancelled);
            if (pending == null) throw new IOException("No action result");
            if (cancelled.get()) { pending.cancel(false); return; }
            String[] result = pending.get(8, TimeUnit.SECONDS);
            if (result == null || result.length != 2 || result[0] == null || !result[0].matches("[0-9]{1,3}") ||
                Integer.parseInt(result[0]) > 255 || result[1] == null || result[1].length() > 16384)
                throw new IOException("Invalid bounded action response");
            if (!cancelled.get()) finish(Integer.parseInt(result[0]), result[1]);
        } catch (java.util.concurrent.TimeoutException timeout) {
            cancelled.set(true); if (pending != null) pending.cancel(false);
            finish(5, "Spring-app action timed out; a committed action may still be in progress. Check native state before retrying.\n");
        } catch (InterruptedException interrupted) {
            cancelled.set(true); Thread.currentThread().interrupt(); finish(130, "Spring-app command cancelled.\n");
        } catch (Exception unavailable) { finish(3, "Spring-app actions unavailable or refused. Use a compatible engine and explicit SSH Start.\n"); }
    }
    private void finish(int status, String text) {
        if (!completed.compareAndSet(false, true)) return;
        try {
            StringBuilder safe = new StringBuilder();
            for (int i = 0; i < text.length(); i++) {
                char c = text.charAt(i);
                if (c == '\n' || c == '\t' || c >= 32 && c <= 126) safe.append(c);
                else if (c > 126) safe.append('?');
            }
            byte[] bytes = safe.toString().getBytes(StandardCharsets.UTF_8);
            if (bytes.length > 16384) { status = 3; bytes = "Spring-app response exceeded its limit.\n".getBytes(StandardCharsets.UTF_8); }
            OutputStream destination = status != 0 && error != null ? error : output;
            if (destination != null) { destination.write(bytes); destination.flush(); }
        } catch (IOException failure) { status = 1; }
        finally { if (callback != null) callback.onExit(status, status == 0 ? "" : "WinterX app command failed", false); }
    }
    @Override public void destroy(ChannelSession channel) {
        cancelled.set(true); if (pending != null) pending.cancel(false); if (task != null) task.cancel(true);
        if (started.get()) finish(130, "Spring-app command cancelled; committed actions are not rolled back.\n");
        else completed.set(true);
    }
}
