package winterx.keyboard;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Collections;
import winterx.extension.NativeTweak;
import winterx.extension.TweakContext;

public final class KeyboardEntry implements NativeTweak {
    private TweakContext context;
    private RealKeyboard keyboard;

    @Override public void start(TweakContext context) {
        this.context = context;
        keyboard = new RealKeyboard(context);
        keyboard.hideIos = !"off".equals(read("hide-ios.txt"));
        keyboard.androidKeyboard = "on".equals(read("android-keyboard.txt"));
        keyboard.start();
    }

    @Override public void stop() { if (keyboard != null) keyboard.stop(); }

    @Override public Object call(String point, Object[] a) {
        if (!context.active()) return null;
        switch (point) {
            case "settings.page": return "main".equals(a[0]) ? page() : null;   // only our own page, never Spring's
            case "settings.tap":
                if ("hide".equals(a[1])) { keyboard.hideIos = !keyboard.hideIos; write("hide-ios.txt", keyboard.hideIos ? "on" : "off"); }
                else if ("android".equals(a[1])) {
                    keyboard.androidKeyboard = !keyboard.androidKeyboard; write("android-keyboard.txt", keyboard.androidKeyboard ? "on" : "off");
                    if (!keyboard.androidKeyboard) keyboard.hideAndroidKeyboard();
                }
                return null;
            default: return null;
        }
    }

    private T6 page() {
        String row = "winterx-tw-r/" + context.id() + "/main/";
        V6 hide = Z3.g(Z3.a, row + "hide", (keyboard.hideIos ? "✓ " : "") + "Hide the iOS keyboard", null, null, null, 0x18);
        V6 android = Z3.g(Z3.a, row + "android", (keyboard.androidKeyboard ? "✓ " : "") + "Use the Android keyboard", null, null, null, 0x18);
        W6 section = new W6("KEYBOARD", null,
            "Typing on a real keyboard always works while a text field is being edited, including ⌘V / Ctrl+V to paste. "
            + "On Mac.APK, hide the iOS keyboard and type with your Mac's. On a phone, turn on Use the Android keyboard to get your own keyboard instead.",
            null, Arrays.asList(hide, android));
        return new T6("winterx-tw-p/" + context.id(), "Android Keyboard", Collections.singletonList(section));
    }

    private String read(String name) {
        try { File file = context.data(name); return file.isFile() ? new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8).trim() : null; }
        catch (Exception unavailable) { return null; }
    }
    private void write(String name, String value) {
        try { File file = context.data(name); file.getParentFile().mkdirs(); Files.write(file.toPath(), value.getBytes(StandardCharsets.UTF_8)); }
        catch (Exception ignored) {}
    }
}
