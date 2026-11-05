package me.example.hookdemo;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

/** Hooks Spring's device-status builder and renames the network shown in Settings → General → About. */
public final class HookDemo implements NativeTweak {
    /** x1.c2.h() builds the status Spring's apps read; "about-network" is the carrier shown in About. */
    static final String STATUS = "Lx1/c2;->h()LE1/o;";

    @Override public void start(TweakContext context) throws Exception {
        context.hook(STATUS, call -> {
            Object status = call.proceed();          // run Spring's original first ("after" hook)
            for (Field field : status.getClass().getDeclaredFields()) {
                if (!Map.class.isAssignableFrom(field.getType())) continue;
                field.setAccessible(true);
                @SuppressWarnings("unchecked") Map<String, Object> values = (Map<String, Object>)field.get(status);
                if (values != null && values.containsKey("about-network")) values.put("about-network", "WinterX ❄");
            }
            return status;
        });
        selfTest(context);
    }

    /** Records that hooks really run on this device: replace a result, then let the original through. */
    private void selfTest(TweakContext context) throws Exception {
        context.hook("Lorg/mozilla/javascript/TokenStream;->isDigit(I)Z",
            call -> ((Integer)call.args[0]) == 'w' ? Boolean.TRUE : call.proceed());
        Method digit = Class.forName("org.mozilla.javascript.TokenStream").getDeclaredMethod("isDigit", int.class);
        digit.setAccessible(true);
        String report = "replaced=" + digit.invoke(null, (int)'w') + " original7=" + digit.invoke(null, (int)'7')
            + " originalQ=" + digit.invoke(null, (int)'q') + "\n";
        File file = context.data("self-test.txt");
        file.getParentFile().mkdirs();
        try (FileOutputStream out = new FileOutputStream(file)) { out.write(report.getBytes(StandardCharsets.UTF_8)); }
    }

    @Override public Object call(String point, Object[] arguments) { return null; }
}
