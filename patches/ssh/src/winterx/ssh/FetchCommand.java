package winterx.ssh;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;
import org.apache.sshd.server.Environment;
import org.apache.sshd.server.ExitCallback;
import org.apache.sshd.server.channel.ChannelSession;
import org.apache.sshd.server.command.Command;

/** An SSH exec response, not a process or interactive shell. */
final class FetchCommand implements Command {
    interface Reporter { String report(boolean color); }
    private static final String USAGE = "WinterX built-in system information\n"
        + "Usage: neofetch [--no-color | --help]\nAlias: winterx-info\n"
        + "Runs in-process; no shell, packages or root required.\n";
    private final Reporter reporter;
    private final boolean color, help, invalid;
    private final AtomicBoolean finished = new AtomicBoolean();
    private OutputStream output, error;
    private ExitCallback callback;
    private FetchCommand(Reporter reporter, boolean color, boolean help, boolean invalid) {
        this.reporter = reporter; this.color = color; this.help = help; this.invalid = invalid;
    }
    static FetchCommand create(String command) { return create(command, WinterXFetch::report); }
    static FetchCommand create(String command, Reporter reporter) {
        if (command == null || command.length() > 8192) return null;
        String[] tokens = command.trim().split("\\s+", 3);
        if (!tokens[0].equals("neofetch") && !tokens[0].equals("winterx-info")) return null;
        boolean help = tokens.length == 2 && tokens[1].equals("--help");
        boolean plain = tokens.length == 2 && tokens[1].equals("--no-color");
        return new FetchCommand(reporter, !plain, help, tokens.length > 1 && !help && !plain);
    }
    @Override public void setInputStream(InputStream input) { /* This command never reads client input. */ }
    @Override public void setOutputStream(OutputStream output) { this.output = output; }
    @Override public void setErrorStream(OutputStream error) { this.error = error; }
    @Override public void setExitCallback(ExitCallback callback) { this.callback = callback; }
    @Override public void start(ChannelSession channel, Environment environment) throws IOException {
        if (!finished.compareAndSet(false, true)) return;
        if (output == null || callback == null) throw new IOException("SSH output/callback unavailable");
        int status = 0;
        try {
            String response;
            if (invalid) { status = 2; response = "Unsupported WinterX info arguments.\n" + USAGE; }
            else if (help) response = USAGE;
            else {
                try { response = reporter.report(color); }
                catch (RuntimeException failure) { status = 1; response = "WinterX information unavailable.\n"; }
            }
            byte[] bytes = response.getBytes(StandardCharsets.UTF_8);
            if (bytes.length > 8192) { status = 1; bytes = "WinterX information unavailable.\n".getBytes(StandardCharsets.UTF_8); }
            OutputStream destination = status != 0 && error != null ? error : output;
            destination.write(bytes); destination.flush();
        } catch (IOException failure) { status = 1; throw failure; }
        finally { callback.onExit(status, status == 0 ? "" : "WinterX info command failed", false); }
    }
    @Override public void destroy(ChannelSession channel) { finished.set(true); }
}
