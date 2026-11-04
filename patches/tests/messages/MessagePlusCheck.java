import java.io.File;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.util.*;
import sun.misc.Unsafe;
import winterx.messages.MessagePlus;

/** Real packaged native models/pointer entries, with only the alert/Android application as spies. */
public final class MessagePlusCheck {
    static void check(boolean value, String why) { if (!value) throw new AssertionError(why); }
    static Unsafe unsafe() throws Exception { Field f = Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object object, String field, Object value) throws Exception { Field f = object.getClass().getDeclaredField(field); f.setAccessible(true); f.set(object, value); }
    public static void main(String[] args) throws Exception {
        boolean packaged = Boolean.parseBoolean(args[0]);
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby"); ruby.mkdirs();
        File marker = new File(ruby, "messageplus.enabled"), prefs = new File(ruby, "messageplus/photo-quality");
        E1.N0 stock = new E1.N0("Edit", null, E1.M0.h, false, null, 1f, null, false);
        check(MessagePlus.button(stock) == stock && MessagePlus.photoQuality(85) == 85, "uninstalled behaviour changed");
        check(MessagePlus.page("winterx-layout-p/messageplus/main") == null, "uninstalled page visible");
        marker.createNewFile();
        E1.N0 button = MessagePlus.button(stock);
        check(button != stock && "Settings".equals(button.a) && button.e.floatValue() == 68f && "Edit".equals(stock.a), "button/shared model changed incorrectly");
        E1.N0 other = new E1.N0("Back", null, E1.M0.h, false, null, 1f, null, false);
        check(MessagePlus.button(other) == other, "unrelated button changed");
        for (int value : new int[]{65, 85, 95}) {
            check(MessagePlus.action("winterx-layout-a/messageplus/photo/" + value), "quality selection failed");
            check(MessagePlus.photoQuality(85) == value, "quality not live");
        }
        check(!MessagePlus.action("winterx-layout-a/messageplus/photo/100"), "unbounded quality accepted");
        for (String bad : List.of("-1", "100", "95.0", "999999999999999999999", "video")) {
            Files.writeString(prefs.toPath(), bad); check(MessagePlus.photoQuality(85) == 85, "malformed quality escaped bounds");
        }
        MessagePlus.action("winterx-layout-a/messageplus/photo/95");
        E1.T6 page = MessagePlus.page("winterx-layout-p/messageplus/main");
        check(page != null && ((E1.W6)page.c.get(0)).c.size() == 3, "native settings choices missing");
        check(((E1.W6)page.c.get(0)).d.contains("unavailable"), "unsupported transport advertised");
        ArrayList<E1.V6> rows = new ArrayList<>(); MessagePlus.rows(rows); check(rows.size() == 1, "root settings row missing");
        x1.i1 spring = (x1.i1)unsafe().allocateInstance(x1.i1.class);
        E1.i6 profile = (E1.i6)unsafe().allocateInstance(E1.i6.class); set(profile, "b", 640); set(spring, "e", profile);
        for (E1.r7 stage : E1.r7.values()) if (stage.a()) { set(spring, "b", stage); break; }
        set(spring, "k", E1.P6.y); set(spring, "E", "messages");
        set(spring, "a", unsafe().allocateInstance(com.guille.spring.LauncherActivity.class));
        x1.J alert = com.guille.spring.LauncherActivity.alert;
        check(!MessagePlus.press(spring, 200, 84) && !MessagePlus.press(spring, 40, 128) && !MessagePlus.press(spring, Float.NaN, 80), "outside/NaN press captured");
        check(MessagePlus.press(spring, 40, 84), "scaled settings press missed");
        check(MessagePlus.release(spring, 40, 84) && alert.shown == 1 && alert.cancel == 3, "release did not present native settings");
        alert.clicked.a(Integer.valueOf(0)); check(MessagePlus.photoQuality(85) == 65 && alert.buttons[0].startsWith("✓"), "actual alert action/refresh failed");
        int shown = alert.shown;
        MessagePlus.press(spring, 40, 84); check(MessagePlus.move(spring, 240, 84), "owned move fell through");
        MessagePlus.release(spring, 40, 84); check(alert.shown == shown, "drag-out/reentry opened settings");
        MessagePlus.press(spring, 40, 84); MessagePlus.cancel(null); check(!MessagePlus.release(spring, 40, 84), "cancel left stale gesture");
        MessagePlus.press(spring, 40, 84); set(spring, "c2", "thread"); MessagePlus.release(spring, 40, 84); check(alert.shown == shown, "thread switch opened list settings");
        check(!MessagePlus.press(spring, 40, 84), "thread button captured"); set(spring, "c2", null);
        set(spring, "E", "mail"); check(!MessagePlus.press(spring, 40, 84), "unrelated app captured"); set(spring, "E", "messages");
        if (packaged) {
            check(spring.u1(40, 84) && spring.t1(40, 84) && spring.v1(40, 84), "actual packaged pointer entry missing");
            E1.l3 model = G1.l.a.a(0, null); check("Settings".equals(((E1.w2)model.a.get(0)).c.a), "main app model hook missing");
            E1.K2 snapshot = (E1.K2)unsafe().allocateInstance(E1.K2.class); set(snapshot, "m", new HashSet<>());
            check("Settings".equals(I1.y.l(snapshot).c.a), "live header model hook missing");
            check("Message+".equals(E1.b4.a.a("winterx-layout-p/messageplus/main").b), "native page router missing");
        }
        byte[] saved = Files.readAllBytes(prefs.toPath());
        MessagePlus.press(spring, 40, 84); new File(ruby, "safe-mode.enabled").mkdir();
        shown = alert.shown; MessagePlus.release(spring, 40, 84);
        check(alert.shown == shown && MessagePlus.button(stock) == stock && MessagePlus.photoQuality(85) == 85, "Safe Mode did not restore stock");
        check(!MessagePlus.action("winterx-layout-a/messageplus/photo/65") && MessagePlus.page("winterx-layout-p/messageplus/main") == null, "Safe Mode changed preferences/pages");
        new File(ruby, "safe-mode.enabled").delete(); marker.delete();
        check(Arrays.equals(saved, Files.readAllBytes(prefs.toPath())) && MessagePlus.button(stock) == stock, "removal erased preference or missed fallback");
        marker.createNewFile(); Files.delete(prefs.toPath()); File outside = new File(ruby, "outside"); Files.writeString(outside.toPath(), "preserved");
        Files.createSymbolicLink(prefs.toPath(), outside.toPath());
        check(!MessagePlus.action("winterx-layout-a/messageplus/photo/65") && MessagePlus.photoQuality(85) == 85 && Files.readString(outside.toPath()).equals("preserved"), "linked preference followed");
        System.out.println("Message+: native models/settings actions, bounded photo quality, scaled pointer entries, cancellation, unrelated apps/threads, Safe Mode/removal and linked-storage preservation passed (alert spy; not live UI/delivery)");
    }
}
