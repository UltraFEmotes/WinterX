package winterx.extension;

import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Cydia-style hooks for any instrumented Spring method. The build gives every hookable method a check against
 * {@link #table}; a hooked method calls {@link #call}, which runs the tweaks' hooks in load order. Each hook may read
 * or change the arguments, call {@link Call#proceed()} to run the next hook and finally the original, change the
 * result, or skip the original entirely.
 */
public final class MethodHooks {
    /** Null until something is hooked; then table[id] is true for hooked methods. Read by instrumented code. */
    public static volatile boolean[] table;
    /** Returned to instrumented code when the original body should run. */
    public static final Object PASS = new Object();

    /** A tweak's hook. Return the method's result (ignored for void methods). */
    public interface Hook { Object call(Call call) throws Throwable; }

    private static final class Entry {
        final String owner; final Hook hook;
        Entry(String owner, Hook hook) { this.owner = owner; this.hook = hook; }
    }
    private static final Map<Integer, Entry[]> HOOKS = new HashMap<>();
    private static final Map<Integer, Method> METHODS = new HashMap<>();
    private static final Map<Integer, MethodHandle> HANDLES = new HashMap<>();
    private static final ThreadLocal<Integer> BYPASS = new ThreadLocal<>();
    private static String[] signatures;
    private static Map<String, Integer> ids;

    private MethodHooks() {}

    /** One hooked invocation, shared along the chain. */
    public static final class Call {
        /** Smali-style signature, e.g. {@code Lx1/K;->a(I)V}. */
        public final String method;
        /** The receiver, or null for a static method. */
        public final Object self;
        /** The arguments, boxed. Hooks may replace elements before calling {@link #proceed()}. */
        public final Object[] args;
        private final int id; private final Entry[] chain; private int next;
        Call(int id, String method, Object self, Object[] args, Entry[] chain) {
            this.id = id; this.method = method; this.self = self; this.args = args; this.chain = chain;
        }
        /** Run the next hook in the chain, or the original method when none are left. */
        public Object proceed() throws Throwable {
            while (next < chain.length) {
                Entry entry = chain[next++];
                if (entry.owner != null && !NativeRuntime.live(entry.owner)) continue;
                try { return entry.hook.call(this); }
                catch (OriginalFailure original) { throw original; }
                catch (Throwable failure) {
                    // The tweak's own hook failed: switch that tweak off and carry on without it.
                    if (entry.owner != null) NativeRuntime.fail(entry.owner, failure);
                    else android.util.Log.w("WinterX", "core hook failed: " + method, failure);
                }
            }
            return original(args);
        }
        /** Call the original method directly with the given arguments, skipping any remaining hooks. */
        public Object original(Object... arguments) throws Throwable {
            MethodHandle target = handle(id);
            Object[] all = arguments;
            if (!Modifier.isStatic(method(id).getModifiers())) {
                all = new Object[arguments.length + 1]; all[0] = self; System.arraycopy(arguments, 0, all, 1, arguments.length);
            }
            BYPASS.set(id);
            // A method handle rethrows exactly what the original threw (reflection may rewrap it).
            try { return target.invokeWithArguments(all); }
            catch (Throwable thrown) { throw new OriginalFailure(thrown); }
            finally { BYPASS.remove(); }
        }
    }

    /** Wraps an exception thrown by the original body so it is rethrown unchanged rather than blamed on a hook. */
    static final class OriginalFailure extends RuntimeException {
        OriginalFailure(Throwable cause) { super(cause); }
    }

    /** Entry point for instrumented methods. */
    public static Object call(int id, Object self, Object[] args) throws Throwable {
        Integer bypass = BYPASS.get();
        if (bypass != null && bypass == id) { BYPASS.remove(); return PASS; }
        Entry[] chain;
        synchronized (MethodHooks.class) { chain = HOOKS.get(id); }
        if (chain == null || chain.length == 0) return PASS;
        Call call = new Call(id, signature(id), self, args, chain);
        Object result;
        try { result = call.proceed(); }
        catch (OriginalFailure original) { throw original.getCause(); }
        return checked(id, result, call);
    }

    /** A hook must return the method's type; a wrong or null primitive result falls back to the original. */
    private static Object checked(int id, Object result, Call call) throws Throwable {
        String signature = signature(id);
        char kind = signature.charAt(signature.lastIndexOf(')') + 1);
        if (kind == 'V') return null;
        Class<?> expected = method(id).getReturnType();
        boolean ok;
        switch (kind) {
            case 'Z': ok = result instanceof Boolean; break;
            case 'C': ok = result instanceof Character; break;
            case 'B': case 'S': case 'I': case 'J': case 'F': case 'D': ok = result instanceof Number; break;
            default: ok = result == null || expected.isInstance(result);
        }
        if (ok) return result;
        try { return call.original(call.args); }
        catch (OriginalFailure original) { throw original.getCause(); }
    }

    // ----- registration -----

    static synchronized String signature(int id) { load(); return signatures[id]; }

    private static void load() {
        if (signatures != null) return;
        signatures = MethodTable.signatures();
        ids = new HashMap<>(signatures.length * 2);
        for (int i = 0; i < signatures.length; i++) ids.put(signatures[i], i);
    }

    /** All hookable methods, in hook-ID order. */
    public static synchronized List<String> hookable() { load(); return Arrays.asList(signatures.clone()); }

    /** True if the signature can be hooked in this core. */
    public static synchronized boolean hookable(String signature) { load(); return ids.containsKey(normalize(signature)); }

    /** Accepts {@code Lx1/K;->a(I)V} or {@code x1.K.a(I)V}. */
    static String normalize(String signature) {
        if (signature == null) return "";
        if (signature.startsWith("L") && signature.contains(";->")) return signature;
        int paren = signature.indexOf('('), dot = paren < 0 ? -1 : signature.lastIndexOf('.', paren);
        if (dot < 0) return signature;
        return "L" + signature.substring(0, dot).replace('.', '/') + ";->" + signature.substring(dot + 1);
    }

    static synchronized void register(String owner, String signature, Hook hook) {
        if (hook == null) throw new IllegalArgumentException("Missing hook");
        load();
        Integer id = ids.get(normalize(signature));
        if (id == null) throw new IllegalArgumentException("Not a hookable Spring method: " + signature);
        Entry[] old = HOOKS.get(id), chain = old == null ? new Entry[1] : Arrays.copyOf(old, old.length + 1);
        chain[chain.length - 1] = new Entry(owner, hook);
        HOOKS.put(id, chain);
        publish();
    }

    /** Remove every hook a package registered (it was disabled, removed or failed). */
    static synchronized void unregister(String owner) {
        boolean changed = false;
        for (Map.Entry<Integer, Entry[]> item : new ArrayList<>(HOOKS.entrySet())) {
            List<Entry> kept = new ArrayList<>();
            for (Entry entry : item.getValue()) if (entry.owner == null || !entry.owner.equals(owner)) kept.add(entry);
            if (kept.size() == item.getValue().length) continue;
            changed = true;
            if (kept.isEmpty()) HOOKS.remove(item.getKey()); else HOOKS.put(item.getKey(), kept.toArray(new Entry[0]));
        }
        if (changed) publish();
    }

    private static void publish() {
        if (HOOKS.isEmpty()) { table = null; return; }
        boolean[] next = new boolean[signatures.length];
        for (Integer id : HOOKS.keySet()) next[id] = true;
        table = next;
    }

    private static synchronized MethodHandle handle(int id) throws Exception {
        MethodHandle cached = HANDLES.get(id);
        if (cached == null) { cached = MethodHandles.lookup().unreflect(method(id)); HANDLES.put(id, cached); }
        return cached;
    }

    private static synchronized Method method(int id) throws Exception {
        Method cached = METHODS.get(id);
        if (cached != null) return cached;
        String signature = signature(id);
        int arrow = signature.indexOf(";->"), paren = signature.indexOf('(', arrow), close = signature.lastIndexOf(')');
        ClassLoader loader = MethodHooks.class.getClassLoader();
        Class<?> owner = Class.forName(signature.substring(1, arrow).replace('/', '.'), false, loader);
        List<Class<?>> types = new ArrayList<>();
        String params = signature.substring(paren + 1, close);
        for (int at = 0; at < params.length();) {
            int start = at;
            while (params.charAt(at) == '[') at++;
            if (params.charAt(at) == 'L') at = params.indexOf(';', at);
            at++;
            types.add(type(params.substring(start, at), loader));
        }
        Method method = owner.getDeclaredMethod(signature.substring(arrow + 3, paren), types.toArray(new Class<?>[0]));
        method.setAccessible(true);
        METHODS.put(id, method);
        return method;
    }

    private static Class<?> type(String descriptor, ClassLoader loader) throws ClassNotFoundException {
        switch (descriptor) {
            case "Z": return boolean.class; case "B": return byte.class; case "S": return short.class; case "C": return char.class;
            case "I": return int.class; case "J": return long.class; case "F": return float.class; case "D": return double.class;
        }
        if (descriptor.startsWith("[")) return Class.forName(descriptor.replace('/', '.'), false, loader);
        return Class.forName(descriptor.substring(1, descriptor.length() - 1).replace('/', '.'), false, loader);
    }
}
