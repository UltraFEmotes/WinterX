package winterx.extension;

import java.io.File;

/** Shared author API for trusted native packages. This is not a Java security sandbox. */
public final class TweakContext {
    private final String id;
    private final File files;
    TweakContext(String id, File files) { this.id = id; this.files = files; }
    public String id() { return id; }
    public File files() { return files; }
    public boolean active() { return NativeRuntime.enabled(id); }
    public File data(String name) {
        if (name == null || !name.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,79}") || name.contains(".."))
            throw new IllegalArgumentException("Use a simple tweak-data filename");
        return new File(files, "winterx-tweaks/" + id + "/data/" + name);
    }
    /**
     * Hook any instrumented Spring method, Cydia-style. {@code method} is {@code Lx1/K;->a(I)V} or {@code x1.K.a(I)V}.
     * Hooks from several tweaks chain in load order; call {@code call.proceed()} to run the rest and the original.
     */
    public void hook(String method, MethodHooks.Hook hook) {
        if (!active()) throw new IllegalStateException("Tweak is not active");
        MethodHooks.register(id, method, hook);
    }
    /** True if this core can hook the method. */
    public boolean canHook(String method) { return MethodHooks.hookable(method); }
    public Object call(String point, Object[] arguments, Object fallback) {
        return NativeRuntime.dispatch(point, arguments, fallback, "first", false, null);
    }
}
