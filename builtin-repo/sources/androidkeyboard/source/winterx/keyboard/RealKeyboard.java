package winterx.keyboard;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.BaseInputConnection;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputConnection;
import android.view.inputmethod.InputMethodManager;
import java.lang.reflect.Method;
import winterx.extension.TweakContext;

/**
 * Sends real key presses and the Android keyboard's text into Spring's text fields.
 *
 * Spring has one typing path for every built-in app and .sapp: its keyboard calls x1.i1.H1(text) to type ("\n" is
 * Return) and x1.i1.x1(false) to delete. Where the iOS keyboard sits comes from x1.i1.Z1(time), which also decides
 * whether a touch lands on the keyboard or the app, and I1.v.b draws it. Hiding it means reporting it as off screen
 * and not drawing it.
 */
final class RealKeyboard {
    static final String TYPE = "Lx1/i1;->H1(Ljava/lang/String;)V";
    static final String TOP = "Lx1/i1;->Z1(J)F";
    static final String DRAW = "LI1/v;->b(Landroid/graphics/Canvas;LE1/o6;Ljava/util/Map;FJF)V";
    static final String PRESS = "Lx1/i1;->K1(FF)V", RELEASE = "Lx1/i1;->L1(FF)V";
    static final String KEYS = "Lcom/guille/spring/LauncherActivity;->dispatchKeyEvent(Landroid/view/KeyEvent;)Z";
    static final float SCREEN = 480f;                        // Spring's screen height in points; the keyboard top when hidden

    private final TweakContext context;
    volatile boolean hideIos = true, androidKeyboard;
    private x1.i1 spring;
    private Activity activity;
    private InputView input;
    private boolean shown;
    private int composing;                                   // characters of the Android keyboard's word in progress
    private Method loop;

    RealKeyboard(TweakContext context) { this.context = context; }

    void start() {
        context.hook(TOP, call -> {
            spring = (x1.i1)call.self;
            boolean visible = spring.Y != null && spring.Y.a;
            if (visible != shown) { shown = visible; onKeyboard(visible); }
            // With the Android keyboard on screen, keep Spring's room for it; otherwise give apps the whole screen.
            if (!context.active() || !hideIos || androidKeyboard) return call.proceed();
            return SCREEN + spring.e();
        });
        context.hook(DRAW, call -> context.active() && hideIos ? null : call.proceed());
        context.hook(PRESS, call -> hiddenKeys() ? null : call.proceed());
        context.hook(RELEASE, call -> hiddenKeys() ? null : call.proceed());
        context.hook(KEYS, call -> {
            activity = (Activity)call.self;
            if (spring == null) spring = controller(activity);
            View focused = activity.getCurrentFocus();                 // no green focus frame around Spring once keys are used
            if (focused != null && focused != input) focused.setDefaultFocusHighlightEnabled(false);
            return context.active() && typing() && key((KeyEvent)call.args[0]) ? Boolean.TRUE : call.proceed();
        });
    }

    void stop() { hideAndroidKeyboard(); }

    /** Spring's controller, before anything has asked where the keyboard is. */
    private static x1.i1 controller(Activity activity) {
        try {
            java.lang.reflect.Field field = activity.getClass().getDeclaredField("controller"); field.setAccessible(true);
            return (x1.i1)field.get(activity);
        } catch (ReflectiveOperationException | RuntimeException unavailable) { return null; }
    }

    /** Touches where the hidden keyboard would be must not press its invisible keys. */
    private boolean hiddenKeys() { return context.active() && hideIos && androidKeyboard; }

    private boolean typing() { return spring != null && spring.Y != null && spring.Y.a; }

    /** A real key press while a text field is being edited. True when it was used. */
    private boolean key(KeyEvent event) {
        int code = event.getKeyCode();
        if (event.getAction() == KeyEvent.ACTION_MULTIPLE && event.getCharacters() != null) { type(event.getCharacters()); return true; }
        if (event.getAction() != KeyEvent.ACTION_DOWN) return isTypingKey(event);
        if ((event.isCtrlPressed() || event.isMetaPressed()) && code == KeyEvent.KEYCODE_V) { paste(); return true; }
        if (event.isCtrlPressed() || event.isMetaPressed()) return false;
        if (code == KeyEvent.KEYCODE_DEL) { delete(1); return true; }
        if (code == KeyEvent.KEYCODE_ENTER || code == KeyEvent.KEYCODE_NUMPAD_ENTER) { type("\n"); return true; }
        int unicode = event.getUnicodeChar(event.getMetaState());
        if (unicode == 0 || (unicode & android.view.KeyCharacterMap.COMBINING_ACCENT) != 0) return false;
        type(new String(Character.toChars(unicode)));
        return true;
    }

    /** Key-ups of keys we typed are ours too, so Spring never sees half a key press. */
    private static boolean isTypingKey(KeyEvent event) {
        int code = event.getKeyCode();
        return code == KeyEvent.KEYCODE_DEL || code == KeyEvent.KEYCODE_ENTER || code == KeyEvent.KEYCODE_NUMPAD_ENTER
            || (!event.isCtrlPressed() && !event.isMetaPressed() && event.getUnicodeChar(event.getMetaState()) != 0);
    }

    void type(String text) {
        if (spring == null || text.isEmpty()) return;
        spring.H1(text);
        redraw();
    }

    void delete(int count) {
        if (spring == null) return;
        for (int i = 0; i < count; i++) spring.x1(false);
        redraw();
    }

    private void paste() {
        ClipboardManager clipboard = activity == null ? null : (ClipboardManager)activity.getSystemService(Context.CLIPBOARD_SERVICE);
        ClipData clip = clipboard == null ? null : clipboard.getPrimaryClip();
        CharSequence text = clip == null || clip.getItemCount() == 0 ? null : clip.getItemAt(0).coerceToText(activity);
        if (text != null) type(text.toString().replace("\r\n", "\n"));
    }

    /** Spring only redraws while something animates; make sure the new text shows. */
    private void redraw() {
        if (activity == null) return;
        try {
            if (loop == null) { loop = activity.getClass().getDeclaredMethod("startAnimationLoop"); loop.setAccessible(true); }
            loop.invoke(activity);
        } catch (ReflectiveOperationException ignored) {}
    }

    // ----- the Android on-screen keyboard -----

    private void onKeyboard(boolean visible) {
        composing = 0;
        if (!context.active() || !androidKeyboard || activity == null) { if (!visible) hideAndroidKeyboard(); return; }
        activity.runOnUiThread(() -> { if (visible) showAndroidKeyboard(); else hideAndroidKeyboard(); });
    }

    private void showAndroidKeyboard() {
        if (input == null) {
            input = new InputView(activity);
            activity.addContentView(input, new ViewGroup.LayoutParams(1, 1));
        }
        input.requestFocus();
        InputMethodManager manager = (InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE);
        if (manager != null) { manager.restartInput(input); manager.showSoftInput(input, 0); }
    }

    void hideAndroidKeyboard() {
        InputView view = input;
        if (view == null) return;
        view.post(() -> {
            InputMethodManager manager = (InputMethodManager)view.getContext().getSystemService(Context.INPUT_METHOD_SERVICE);
            if (manager != null) manager.hideSoftInputFromWindow(view.getWindowToken(), 0);
            view.clearFocus();
        });
    }

    /** A 1×1 view that the Android keyboard types into; everything it sends goes to Spring's text field. */
    private final class InputView extends View {
        InputView(Context context) { super(context); setFocusable(true); setFocusableInTouchMode(true); }

        @Override public boolean onCheckIsTextEditor() { return true; }

        @Override public InputConnection onCreateInputConnection(EditorInfo info) {
            info.inputType = InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES | InputType.TYPE_TEXT_FLAG_MULTI_LINE;
            info.imeOptions = EditorInfo.IME_FLAG_NO_EXTRACT_UI | EditorInfo.IME_FLAG_NO_FULLSCREEN;
            return new BaseInputConnection(this, false) {
                // A word being typed with suggestions is shown as it changes, then committed: retype it each time.
                @Override public boolean setComposingText(CharSequence text, int cursor) {
                    delete(composing); type(text.toString()); composing = text.length(); return true;
                }
                @Override public boolean commitText(CharSequence text, int cursor) {
                    delete(composing); composing = 0; type(text.toString()); return true;
                }
                @Override public boolean finishComposingText() { composing = 0; return true; }
                @Override public boolean deleteSurroundingText(int before, int after) {
                    composing -= Math.min(before, composing);
                    delete(before); return true;
                }
                @Override public boolean performEditorAction(int action) { composing = 0; type("\n"); return true; }
            };
        }
    }
}
