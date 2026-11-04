package x1;
import Z1.l;
public final class J {
    public final android.os.Handler e = new android.os.Handler();
    public int shown, cancel;
    public String title, message;
    public String[] buttons;
    public l clicked;
    public H n(String title, String message, String[] buttons, int cancel, l clicked) {
        shown++; this.title = title; this.message = message; this.buttons = buttons;
        this.cancel = cancel; this.clicked = clicked; return null;
    }
}
