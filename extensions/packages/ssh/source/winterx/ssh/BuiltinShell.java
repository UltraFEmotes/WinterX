package winterx.ssh;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;
import org.apache.sshd.server.Environment;
import org.apache.sshd.server.ExitCallback;
import org.apache.sshd.server.Signal;
import org.apache.sshd.server.SignalListener;
import org.apache.sshd.server.channel.ChannelSession;
import org.apache.sshd.server.command.Command;

/** Interactive WinterX built-ins, with a bounded line editor. No OS shell, process or native PTY. */
final class BuiltinShell implements Command {
    interface Factory { Command create(String line); }
    private static final String PROMPT = "winterx> ";
    private static final String HELP = "WinterX interactive commands\n"
        + "  neofetch [--no-color | --help]\n"
        + "  winterx-info [--no-color | --help]\n"
        + "  winterx-app --help\n"
        + "  winterx-app list | open sapp:your.app.id | close sapp:your.app.id\n"
        + "  winterx-app install Example.sapp --sha256 <hash> --confirm\n"
        + "  help, exit, logout\n"
        + "Backspace edits; Ctrl-U clears; Ctrl-C cancels pending work; Ctrl-D exits.\n";
    private final Factory factory;
    private final AtomicBoolean started = new AtomicBoolean(), ended = new AtomicBoolean();
    private final Object lock = new Object();
    private final StringBuilder line = new StringBuilder();
    private InputStream input;
    private OutputStream output;
    private ExitCallback callback;
    private ChannelSession channel;
    private Environment environment;
    private SignalListener signals;
    private Command active;
    private Thread reader;
    private boolean pty, invalid, cr;
    private int escape;
    BuiltinShell() { this(value -> { Command info = FetchCommand.create(value); return info != null ? info : AppCommand.create(value); }); }
    BuiltinShell(Factory factory) { this.factory = factory; }
    @Override public void setInputStream(InputStream input) { this.input = input; }
    @Override public void setOutputStream(OutputStream output) { this.output = output; }
    @Override public void setErrorStream(OutputStream error) { /* Terminal command errors share the terminal output. */ }
    @Override public void setExitCallback(ExitCallback callback) { this.callback = callback; }
    @Override public void start(ChannelSession channel, Environment environment) throws IOException {
        if (ended.get() || !started.compareAndSet(false, true)) return;
        if (input == null || output == null || callback == null) throw new IOException("Interactive SSH streams unavailable");
        this.channel = channel; this.environment = environment;
        pty = environment != null && (environment.getEnv().containsKey(Environment.ENV_TERM) || !environment.getPtyModes().isEmpty());
        signals = (source, signal) -> { if (signal == Signal.INT) cancel(); else finish(130, false); };
        if (environment != null) environment.addSignalListener(signals, Signal.INT, Signal.TERM, Signal.HUP);
        write("WinterX interactive session. Type help for commands.\n" + PROMPT);
        reader = new Thread(() -> {
            try {
                while (!ended.get()) {
                    int value = input.read();
                    if (value < 0) { finish(0, false); return; }
                    accept(value);
                }
            } catch (IOException failure) { finish(1, false); }
            catch (RuntimeException failure) { finish(1, false); }
        }, "WinterX-SSH-prompt");
        reader.setDaemon(true); reader.start();
    }
    private void write(String text) throws IOException { terminal.write(text.getBytes(StandardCharsets.UTF_8)); }
    private final OutputStream terminal = new OutputStream() {
        @Override public void write(int value) throws IOException { write(new byte[]{(byte)value}, 0, 1); }
        @Override public void write(byte[] bytes, int offset, int length) throws IOException {
            synchronized (lock) {
                if (ended.get() || output == null) return;
                if (!pty) output.write(bytes, offset, length);
                else for (int i = offset; i < offset + length; i++) {
                    if (bytes[i] == '\n') output.write('\r');
                    output.write(bytes[i]);
                }
                output.flush();
            }
        }
        @Override public void flush() throws IOException { synchronized (lock) { if (!ended.get() && output != null) output.flush(); } }
    };
    private void accept(int value) throws IOException {
        if (value == 3) { cancel(); return; }
        if (value == 4) { finish(0, true); return; }
        String command = null;
        synchronized (lock) {
            if (ended.get()) return;
            if (value == '\n' && cr) { cr = false; return; }
            cr = value == '\r';
            if (escape > 0) {
                if (escape == 1 && value == '[') escape = 2;
                else if (escape == 1 || value >= 64 && value <= 126 || ++escape > 18) escape = 0;
                return;
            }
            if (value == 27) { escape = 1; return; }
            if (value == 8 || value == 127) {
                if (line.length() > 0 && !invalid) { line.setLength(line.length() - 1); if (pty) write("\b \b"); }
                return;
            }
            if (value == 21) {
                if (pty) for (int i = 0; i < line.length(); i++) write("\b \b");
                line.setLength(0); invalid = false; return;
            }
            if (value == '\r' || value == '\n') {
                if (pty) write("\n");
                if (invalid) { line.setLength(0); invalid = false; write("Command refused: use at most 512 ASCII characters.\n"); if (active == null) write(PROMPT); return; }
                command = line.toString().trim(); line.setLength(0);
            } else if (value >= 32 && value <= 126 || value == '\t') {
                if (line.length() >= 512) invalid = true;
                else if (!invalid) { char character = value == '\t' ? ' ' : (char)value; line.append(character); if (pty) write(String.valueOf(character)); }
            } else invalid = true;
        }
        if (command != null) execute(command);
    }
    private void execute(String command) throws IOException {
        if (command.equals("exit") || command.equals("logout")) { finish(0, true); return; }
        synchronized (lock) {
            if (ended.get()) return;
            if (active != null) { write("A command is still running. Ctrl-C cancels pending work.\n"); return; }
            if (command.isEmpty()) { write(PROMPT); return; }
            if (command.equals("help")) { write(HELP + PROMPT); return; }
            Command child = factory.create(command);
            if (child == null) { write("Unknown WinterX command. Type help.\n" + PROMPT); return; }
            active = child;
            OutputStream response = new OutputStream() {
                @Override public void write(int value) throws IOException { write(new byte[]{(byte)value}, 0, 1); }
                @Override public void write(byte[] bytes, int offset, int length) throws IOException {
                    synchronized (lock) { if (active == child && !ended.get()) terminal.write(bytes, offset, length); }
                }
            };
            child.setInputStream(new ByteArrayInputStream(new byte[0])); child.setOutputStream(response); child.setErrorStream(response);
            child.setExitCallback((code, message, close) -> {
                synchronized (lock) {
                    if (active != child || ended.get()) return;
                    active = null;
                    try { write(PROMPT); } catch (IOException failure) { finish(1, false); }
                }
            });
            try { child.start(channel, environment); }
            catch (Exception failure) {
                active = null; destroy(child); write("WinterX command could not start.\n" + PROMPT);
            }
        }
    }
    private void cancel() {
        synchronized (lock) {
            if (ended.get()) return;
            Command child = active; active = null; line.setLength(0); invalid = false; escape = 0;
            destroy(child);
            try { write("^C\n" + PROMPT); } catch (IOException failure) { finish(1, false); }
        }
    }
    private void destroy(Command child) { if (child != null) try { child.destroy(channel); } catch (Exception ignored) {} }
    private void finish(int code, boolean goodbye) {
        synchronized (lock) {
            if (ended.get()) return;
            if (goodbye) try { write("Goodbye.\n"); } catch (IOException ignored) {}
            if (!ended.compareAndSet(false, true)) return;
            Command child = active; active = null; destroy(child); line.setLength(0);
            if (environment != null && signals != null) environment.removeSignalListener(signals);
            if (input != null) try { input.close(); } catch (IOException ignored) {}
            if (reader != null && reader != Thread.currentThread()) reader.interrupt();
            if (callback != null) callback.onExit(code, "", false);
        }
    }
    @Override public void destroy(ChannelSession channel) { finish(130, false); }
}
