package me.fixture.hooks;

import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

/** Fixture tweak: hooks real Spring methods in start(), behaviour chosen by its package ID. */
public final class HookProbe implements NativeTweak {
    static final String DIGIT = "Lorg/mozilla/javascript/TokenStream;->isDigit(I)Z";
    public void start(TweakContext context) {
        String id = context.id();
        if (id.endsWith("a-digits")) {
            // Replace the result for one input, otherwise run the rest of the chain and the original.
            context.hook(DIGIT, call -> ((Integer)call.args[0]) == 'x' ? Boolean.TRUE : call.proceed());
            // Skip a void original (Kotlin's null check) for one message.
            context.hook("a2.g.e(Ljava/lang/Object;Ljava/lang/String;)V", call -> "skip".equals(call.args[1]) ? null : call.proceed());
        } else if (id.endsWith("b-more")) {
            context.hook(DIGIT, call -> ((Integer)call.args[0]) == 'y' ? Boolean.TRUE : call.proceed());
        } else if (id.endsWith("c-bad")) {
            context.hook(DIGIT, call -> {
                if (((Integer)call.args[0]) == 'z') throw new IllegalStateException("fixture hook failure");
                return call.proceed();
            });
        } else if (id.endsWith("d-args")) {
            // Change an argument before the original runs.
            context.hook("Lorg/mozilla/javascript/TokenStream;->isAlpha(I)Z", call -> { call.args[0] = (int)'a'; return call.proceed(); });
            // Change the original's result afterwards.
            context.hook("Lorg/mozilla/javascript/TokenStream;->isHexDigit(I)Z", call -> !((Boolean)call.proceed()));
            if (context.canHook("Lnot/a/Real;->method()V")) throw new IllegalStateException("unknown method reported hookable");
        }
    }
    public Object call(String point, Object[] arguments) { return null; }
}
