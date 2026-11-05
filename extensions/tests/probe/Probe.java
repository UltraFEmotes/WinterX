package me.fixture;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import winterx.extension.NativeRuntime;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

/** Executed by the real child classloader only, in disposable test roots. */
public final class Probe implements NativeTweak {
    private TweakContext context;
    public void start(TweakContext context) throws Exception {
        this.context = context;
        if (context.id().endsWith("bad-start")) throw new IllegalStateException("fixture start failure");
        if (context.id().endsWith("a-child") && !NativeRuntime.enabled("me.fixture.z-base"))
            throw new IllegalStateException("dependency was not started first");
        mark("started.txt");
    }
    public Object call(String point, Object[] arguments) {
        if (!"fixture.value".equals(point)) return null;
        if (context.id().endsWith("bad-call")) throw new IllegalStateException("fixture hook failure");
        if (context.id().endsWith("bad-type")) return "wrong type";
        return Integer.valueOf(7);
    }
    public void stop() throws Exception { mark("stopped.txt"); }
    private void mark(String name) throws Exception {
        File file = context.data(name);
        file.getParentFile().mkdirs();
        Files.write(file.toPath(), "yes\n".getBytes(StandardCharsets.UTF_8));
    }
}
