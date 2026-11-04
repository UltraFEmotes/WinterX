package x1;
import Z1.l;
public class J {
    public static final J INSTANCE = new J();
    public int calls;
    public String title;
    public String body;
    public H n(String title, String body, String[] buttons, int selected, l callback) {
        this.calls++; this.title = title; this.body = body;
        if (buttons.length != 1 || !"OK".equals(buttons[0])) throw new AssertionError("Unexpected button");
        callback.a(Integer.valueOf(0));
        return null;
    }
}
