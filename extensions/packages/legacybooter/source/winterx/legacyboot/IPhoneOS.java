package winterx.legacyboot;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;

/**
 * iPhone OS 1 running full screen on top of Spring. The phone has no buttons on screen; Android's keys are its buttons:
 * Back (Esc on Mac.APK) presses Home, holding it holds Sleep/Wake (keep holding for "slide to power off"), and the
 * volume keys are the volume buttons. Powering the phone off, or holding Back for 8 seconds, goes back to the boot menu.
 */
final class IPhoneOS {
    static final int SLEEP = 0, HOME = 1, VOLUME_UP = 2, VOLUME_DOWN = 3;
    static final long HOLD_MS = 600, LEAVE_MS = 8000;

    private final Activity activity;
    private final LocalServer server;
    interface Leave { void left(String reason); }
    private final Leave leave;
    private String reason;
    private final Handler main = new Handler(Looper.getMainLooper());
    private FrameLayout frame;
    private Overlay overlay;
    private View springView;
    private final View.OnLayoutChangeListener follow = (v, l, t, r, b, ol, ot, or, ob) -> v.post(this::fit);
    private WebView web;
    private boolean sleepHeld;
    private final Runnable holdSleep = () -> { sleepHeld = true; button(SLEEP, true); };
    private final Runnable forceLeave = this::close;

    IPhoneOS(Activity activity, LocalServer server, Leave leave) { this.activity = activity; this.server = server; this.leave = leave; }

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    void open() {
        frame = new FrameLayout(activity);
        frame.setBackgroundColor(Color.BLACK);
        frame.setClickable(true);                            // nothing reaches Spring underneath
        overlay = new Overlay(activity, frame);
        overlay.show();
        // Only Spring's screen: with Spring's frame on, the frame (and its Home button) stays around iPhone OS.
        // The WebView comes after: Mac.APK sizes its native web view once, when the WebView is attached.
        frame.post(this::fit);
    }

    private void startWeb() {
        if (frame == null || web != null) return;
        web = new WebView(activity);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setSupportZoom(false);
        web.setBackgroundColor(Color.BLACK);
        web.setVerticalScrollBarEnabled(false); web.setHorizontalScrollBarEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setWebViewClient(new WebViewClient() {           // keep every page inside this view
            // Android: the page lives at a secure https address and this tweak answers its requests (Spring doesn't
            // allow plain http, not even to 127.0.0.1). Mac.APK never calls this and uses the local server instead.
            @Override public android.webkit.WebResourceResponse shouldInterceptRequest(WebView view, android.webkit.WebResourceRequest request) {
                android.net.Uri url = request.getUrl();
                if (!ASSETS.equals(url.getHost())) return null;
                String path = url.getPath() == null ? "" : url.getPath().replaceFirst("^/+", "");
                Engine.Reply reply = server.engine().reply(path);
                android.webkit.WebResourceResponse response = new android.webkit.WebResourceResponse(
                    reply.type.split(";")[0], reply.type.contains("charset") ? "utf-8" : null, new java.io.ByteArrayInputStream(reply.body));
                if (reply.status != 200) response.setStatusCodeAndReasonPhrase(reply.status, "Error");
                java.util.Map<String, String> headers = new java.util.HashMap<>();
                headers.put("Access-Control-Allow-Origin", "*"); headers.put("Cache-Control", "no-cache");
                response.setResponseHeaders(headers);
                return response;
            }
            // Android kills the page's renderer when memory runs out; without this Spring itself would be closed.
            @Override public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {
                reason = "iPhone OS ran out of memory on this device";
                main.post(IPhoneOS.this::close);
                return true;
            }
        });
        web.addJavascriptInterface(new Object() {
            @JavascriptInterface public void ready() {}
            @JavascriptInterface public void stopped(String message) { reason = "iPhone OS stopped: " + message; main.postDelayed(IPhoneOS.this::close, 4000); }
        }, "LegacyBoot");
        web.setOnKeyListener((view, code, event) -> key(code, event));
        frame.addView(web, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        web.setFocusable(true); web.setFocusableInTouchMode(true); web.requestFocus();
        String page = "https://" + ASSETS + "/";
        if (macApk()) {
            try { page = server.start(); }
            catch (java.io.IOException busy) { reason = "iPhone OS couldn't start its local server"; close(); return; }
        }
        web.loadUrl(page);
    }

    boolean running() { return frame != null; }

    static final String ASSETS = "appassets.androidplatform.net";

    /** Mac.APK's WebView is Safari's engine behind this bridge; it allows http to 127.0.0.1 but can't intercept requests. */
    private static boolean macApk() {
        try { Class.forName("android.webkit.MacApkWebViewBridge"); return true; }
        catch (ClassNotFoundException | LinkageError android) { return false; }
    }

    private int fitTries;

    /** Cover Spring's screen; until Spring's view is laid out, keep trying (10 s) and use the whole window meanwhile. */
    private void fit() {
        if (overlay == null) return;
        if (springView == null) {
            springView = SpringScreen.main(activity);
            if (springView != null) springView.addOnLayoutChangeListener(follow);
        }
        android.graphics.Rect screen = SpringScreen.rect(activity);
        overlay.place(screen);
        if (screen == null && ++fitTries < 20) { main.postDelayed(this::fit, 500); return; }
        if (web == null) main.postDelayed(this::startWeb, 100);   // once the frame has its size
    }

    void home() { button(HOME, true); main.postDelayed(() -> button(HOME, false), 120); }


    /** Back is Home (tap) or Sleep/Wake (hold); the volume keys are the volume buttons. */
    private boolean key(int code, KeyEvent event) {
        boolean down = event.getAction() == KeyEvent.ACTION_DOWN;
        switch (code) {
            case KeyEvent.KEYCODE_BACK: case KeyEvent.KEYCODE_ESCAPE:
                if (down && event.getRepeatCount() == 0) { main.postDelayed(holdSleep, HOLD_MS); main.postDelayed(forceLeave, LEAVE_MS); }
                else if (!down) {
                    main.removeCallbacks(holdSleep); main.removeCallbacks(forceLeave);
                    if (sleepHeld) { sleepHeld = false; button(SLEEP, false); }
                    else home();
                }
                return true;
            case KeyEvent.KEYCODE_VOLUME_UP: if (event.getRepeatCount() == 0) button(VOLUME_UP, down); return true;
            case KeyEvent.KEYCODE_VOLUME_DOWN: if (event.getRepeatCount() == 0) button(VOLUME_DOWN, down); return true;
            default: return false;
        }
    }

    private void button(int which, boolean pressed) {
        if (web != null) web.evaluateJavascript("button(" + which + "," + pressed + ")", null);
    }

    /** Shut the phone down and hand the screen back (to the boot menu). */
    void close() {
        main.removeCallbacks(holdSleep); main.removeCallbacks(forceLeave);
        if (frame == null) return;
        if (springView != null) springView.removeOnLayoutChangeListener(follow);
        overlay.dismiss();
        if (web != null) web.destroy();
        web = null; frame = null; fitTries = 0;
        String why = reason != null ? reason : "iPhone OS was shut down";
        reason = null;
        leave.left(why);
    }
}
