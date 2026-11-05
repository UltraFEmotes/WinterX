package winterx.extension;

import android.graphics.Canvas;
import java.util.ArrayDeque;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/** Engine-owned Canvas leases. A disabled/updated provider still releases the scope it opened. */
public final class NativeScopes {
    private NativeScopes() {}
    private static final class Scope {
        final Canvas canvas;
        final int saved;
        final NativeRuntime.Lease lease;
        final List<NativeRuntime.Lease> leases;
        Scope(Canvas canvas, int saved, NativeRuntime.Lease lease) { this(canvas, saved, lease, Collections.<NativeRuntime.Lease>emptyList()); }
        Scope(Canvas canvas, int saved, NativeRuntime.Lease lease, List<NativeRuntime.Lease> leases) { this.canvas = canvas; this.saved = saved; this.lease = lease; this.leases = leases; }
    }
    private static final ThreadLocal<Map<Canvas, ArrayDeque<Scope>>> ICONS = ThreadLocal.withInitial(IdentityHashMap::new);
    public static Object frame(String point, Object[] arguments) {
        Canvas canvas = (Canvas)arguments[0]; int saved = canvas.save();
        try {
            NativeRuntime.Lease lease = NativeRuntime.open(point, arguments, null);
            if (lease == null) { canvas.restoreToCount(saved); saved = canvas.save(); }
            return new Scope(canvas, saved, lease);
        }
        catch (RuntimeException | Error failure) { canvas.restoreToCount(saved); throw failure; }
    }
    public static void frameEnd(String point, Object token) {
        if (!(token instanceof Scope)) return;
        Scope scope = (Scope)token;
        try { if (scope.lease != null) NativeRuntime.release(scope.lease, point, new Object[]{scope.lease.value}); }
        finally { scope.canvas.restoreToCount(scope.saved); }
    }
    /** Every exporting package may transform the icon canvas in load order; the engine's own save undoes them all. */
    public static int icon(String point, Object[] arguments) {
        Canvas canvas = (Canvas)arguments[0]; int saved = canvas.save();
        try {
            List<NativeRuntime.Lease> leases = NativeRuntime.openAll(point, arguments, Number.class, lease -> {
                int value = ((Number)lease.value).intValue();
                return value >= -1 && value <= canvas.getSaveCount();
            }, () -> { canvas.restoreToCount(saved); canvas.save(); });
            Map<Canvas, ArrayDeque<Scope>> scopes = ICONS.get();
            scopes.computeIfAbsent(canvas, key -> new ArrayDeque<>()).push(new Scope(canvas, saved, null, leases));
            return saved;
        } catch (RuntimeException | Error failure) { canvas.restoreToCount(saved); throw failure; }
    }
    public static void iconEnd(String point, Canvas canvas, int saved) {
        Map<Canvas, ArrayDeque<Scope>> scopes = ICONS.get(); ArrayDeque<Scope> stack = scopes.get(canvas);
        if (stack == null || stack.isEmpty() || stack.peek().saved != saved) throw new IllegalStateException("Unpaired native drawing scope");
        Scope scope = stack.pop(); if (stack.isEmpty()) scopes.remove(canvas); if (scopes.isEmpty()) ICONS.remove();
        try {
            for (int i = scope.leases.size() - 1; i >= 0; i--) {
                NativeRuntime.Lease lease = scope.leases.get(i);
                NativeRuntime.release(lease, point, new Object[]{canvas, lease.value});
            }
        } finally { canvas.restoreToCount(saved); }
    }
}
