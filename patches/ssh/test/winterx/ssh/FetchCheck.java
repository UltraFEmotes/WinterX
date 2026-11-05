package winterx.ssh;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.apache.sshd.server.command.Command;

/** In-memory SSH command lifecycle only: no listener, authenticated connection or shell. */
public final class FetchCheck {
    static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
    static String run(Command command, int expected) throws Exception {
        check(command != null, "built-in command not recognized");
        ByteArrayOutputStream out = new ByteArrayOutputStream(), err = new ByteArrayOutputStream();
        AtomicInteger exits = new AtomicInteger(), code = new AtomicInteger(-1);
        command.setInputStream(new InputStream() {
            @Override public int read() { throw new AssertionError("info command read client input"); }
        });
        command.setOutputStream(out); command.setErrorStream(err);
        command.setExitCallback((status, message, close) -> { exits.incrementAndGet(); code.set(status); });
        command.start(null, null); command.start(null, null); command.destroy(null);
        check(exits.get() == 1 && code.get() == expected, "wrong/repeated exit callback");
        check(expected == 0 ? err.size() == 0 : out.size() == 0, "wrong output stream");
        return new String((expected == 0 ? out : err).toByteArray(), StandardCharsets.UTF_8);
    }
    public static void main(String[] arguments) throws Exception {
        Map<String, String> facts = WinterXFetch.facts();
        check(facts.get("Spring").equals("0.8.1"), "package version not read from the fixture app");
        check(facts.get("Reported device").equals("Fixture Spring Phone"), "reported device metadata lost");
        check(facts.get("Reported Android").equals("15 / API 35"), "Android release/API invented or lost");
        check(facts.get("Reported display").equals("640 x 960 / 320 dpi"), "reported display lost");
        check(facts.get("Device uptime").equals("1d 10h 17m"), "uptime formatted incorrectly");
        check(facts.get("Host OS").startsWith(System.getProperty("os.name") + " "), "host OS confused with reported Android");
        String plain = run(FetchCommand.create("neofetch --no-color"), 0);
        check(plain.contains("WinterX") && plain.contains("Spring Phone") && !plain.contains("\u001b"), "plain report/branding incorrect");
        check(!plain.contains("private-serial") && !plain.contains("private-host"), "unique/private identifiers printed");
        check(run(FetchCommand.create("winterx-info"), 0).contains("\u001b[1;31m"), "alias/red logo missing");
        for (String line : plain.split("\n")) check(line.length() <= 80, "report does not fit an 80-column terminal");
        AtomicInteger probes = new AtomicInteger();
        FetchCommand.Reporter spy = color -> { probes.incrementAndGet(); return "fixture output\n"; };
        check(run(FetchCommand.create("neofetch --help", spy), 0).contains("Usage:"), "help missing");
        check(run(FetchCommand.create("neofetch --all", spy), 2).contains("Unsupported"), "unknown arguments accepted");
        run(FetchCommand.create("winterx-info --no-color extra", spy), 2);
        check(probes.get() == 0, "help/invalid arguments collected metadata");
        check(FetchCommand.create("uname") == null && FetchCommand.create("neofetch-other") == null && FetchCommand.create(null) == null,
            "unrelated exec commands hijacked");
        Map<String, String> hostile = new LinkedHashMap<>();
        hostile.put("Device\u001b[2J", "Phone\r\nspoof\u001b[31m\u202e\u2066");
        StringBuilder longValue = new StringBuilder(); for (int i = 0; i < 10000; i++) longValue.append('x');
        for (int i = 0; i < 100; i++) hostile.put("field" + i, longValue.toString());
        String safe = WinterXFetch.render(hostile, false);
        check(!safe.contains("\u001b") && !safe.contains("\r") && !safe.contains("\u202e") && !safe.contains("\u2066"), "terminal controls not filtered");
        check(safe.split("\n").length <= 18 && safe.getBytes(StandardCharsets.UTF_8).length < 8192, "metadata/rows not bounded");
        for (String line : safe.split("\n")) check(line.length() <= 80, "long metadata widened the report");
        check(run(FetchCommand.create("neofetch", color -> { throw new IllegalStateException("private failure details"); }), 1)
            .equals("WinterX information unavailable.\n"), "provider failure leaked internal details");
        check(run(FetchCommand.create("neofetch", color -> longValue.toString()), 1).contains("unavailable"), "oversized report accepted");
        FetchCommand cancelled = FetchCommand.create("neofetch", spy);
        cancelled.destroy(null); cancelled.start(null, null); check(probes.get() == 0, "cancelled command collected metadata");
        FetchCommand broken = FetchCommand.create("neofetch --no-color"); AtomicInteger brokenExit = new AtomicInteger(-1);
        broken.setOutputStream(new OutputStream() { @Override public void write(int value) throws IOException { throw new IOException("closed fixture"); } });
        broken.setExitCallback((status, message, close) -> brokenExit.set(status));
        try { broken.start(null, null); throw new AssertionError("failed output accepted"); } catch (IOException expected) {}
        check(brokenExit.get() == 1, "failed output did not signal exit");
        android.app.ActivityThread.application.resources.metrics.widthPixels = 0;
        check(WinterXFetch.facts().get("Reported display").equals("unavailable"), "invalid display presented as real data");
        android.app.ActivityThread.application = null;
        check(WinterXFetch.facts().get("Spring").equals("unavailable") && WinterXFetch.facts().get("Runtime").equals("Host JVM (no Android app)"),
            "missing app metadata invented");
        System.out.println("WinterX fetch: branding/aliases/plain/help, reported-vs-host metadata, bounded control-safe output, privacy, exit/cancellation/error lifecycle passed (fixtures; no socket or shell)");
    }
}
