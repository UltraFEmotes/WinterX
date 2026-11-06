package winterx.legacyboot;

import E1.T6;
import E1.V6;
import E1.W6;
import android.app.Activity;
import android.os.Handler;
import android.os.Looper;
import java.util.Collections;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

/**
 * Runs iPhone OS 1 as an app inside Spring. The bundled "iPhone OS 1" app is only a black screen; when Spring starts it,
 * this tweak shows the emulator over Spring's screen, and Spring's Home shuts it down again (a fresh start each time).
 */
public final class LegacyBooterEntry implements NativeTweak {
    static final String APP = "com.winterx.iphoneos1";
    // Spring evaluates an app's main.js every time the app opens; ours carries this line.
    static final String EVAL = "Lcom/guille/spring/sapp/QuickJs;->u(Ljava/lang/String;Ljava/lang/String;)V";
    static final String MARK = "LegacyBooter draws iPhone OS 1 over this app";
    static final String HOME = "Lcom/guille/spring/LauncherActivity;->onHomePressed()V";
    static final String LOOP = "Lcom/guille/spring/LauncherActivity;->startAnimationLoop()V";
    private final Handler main = new Handler(Looper.getMainLooper());
    private TweakContext context;
    private Engine engine;
    private LocalServer server;
    private volatile Activity activity;
    private IPhoneOS phone;

    @Override public void start(TweakContext context) {
        this.context = context;
        engine = new Engine(context.data("engine"));
        server = new LocalServer(engine);
        context.hook(LOOP, call -> { activity = (Activity)call.self; return call.proceed(); });
        context.hook(EVAL, call -> {
            Object source = call.args[0];
            if (context.active() && "main.js".equals(call.args[1]) && source instanceof String && ((String)source).contains(MARK)) main.post(this::open);
            return call.proceed();
        });
        context.hook(HOME, call -> {
            if (phone != null && phone.running()) phone.close();   // leaving the app shuts iPhone OS down
            return call.proceed();
        });
    }

    @Override public void stop() { if (phone != null) phone.close(); server.stop(); }

    private void open() {
        Activity current = activity;
        if (current == null || (phone != null && phone.running())) return;
        phone = new IPhoneOS(current, server, reason -> {});
        phone.open();
    }

    @Override public Object call(String point, Object[] a) {
        if (!context.active()) return null;
        return "settings.page".equals(point) && "main".equals(a[0]) ? page() : null;   // only our own page
    }

    private T6 page() {
        long engineMB = engine.size() / 1048576;
        W6 section = new W6("IPHONE OS 1", null,
            "Open the iPhone OS 1 app on your Home screen to start the original iPhone. Use the round Home button under "
            + "its screen for the iPhone's Home, and Spring's Home to close it; each launch starts fresh. The first launch "
            + "downloads kelindi's iphone-1-emulator " + (engineMB > 0 ? "(" + engineMB + " MB here now) " : "")
            + "and about 190 MB of iPhone OS 1.0.",
            null, Collections.<V6>emptyList());
        return new T6("winterx-tw-p/" + context.id(), "LegacyBooter", Collections.singletonList(section));
    }
}
