package winterx.tweaks;

import java.io.File;
import java.nio.file.Files;
import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;

/** Real Spring models, with only Application/ActivityThread stubbed. Does not run JNI. */
public final class TweakSettingsCheck {
    static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static V6 find(T6 page, String id) {
        if (page == null) return null;
        for (Object section : page.c) for (Object row : ((W6) section).c) {
            V6 entry = (V6) row;
            if (id.equals(entry.a)) return entry;
        }
        return null;
    }
    public static void main(String[] args) throws Exception {
        String id = "me.example.codetweak";
        File dir = new File(System.getProperty("ruby.test.dir"), "winterx-tweaks/" + id);
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby");
        ruby.mkdirs();
        T6 ios4 = Z3.c, ios6 = null;
        for (Object value : Z3.s) if ("root".equals(((T6) value).a)) ios6 = (T6) value;
        check(ios6 != null, "iOS 6 root missing");
        String main = "winterx-tw-p/" + id;
        check(find(TweakSettings.decorate(ios4), main) != null, "iOS 4 tweak row missing");
        check(find(TweakSettings.decorate(ios6), main) != null, "iOS 6 tweak row missing");
        T6 decorated = TweakSettings.decorate(ios6);
        check(TweakSettings.decorate(decorated).c.size() == decorated.c.size(), "duplicate decoration");
        check(find(TweakSettings.page(main), "winterx-tw-r/" + id + "/main/hello") != null, "custom button missing");
        check(TweakSettings.page(main + "/main") != null, "main page alias failed");
        check(TweakSettings.page(main + "/more") != null, "secondary page missing");
        String toggle = "winterx-tw-r/" + id + "/main/enabled";
        TweakSettings.action(toggle);
        check(TweakHost.setting(id, "main/enabled", "off"), "toggle did not persist");
        check(find(TweakSettings.page(main), toggle).b.startsWith("✓"), "toggle not reflected in model");
        String state = TweakHost.readText(new File(dir, "state.json"));
        TweakSettings.action("winterx-tw-r/" + id + "/main/undeclared");
        check(state.equals(TweakHost.readText(new File(dir, "state.json"))), "undeclared row changed state");
        check(TweakSettings.page(main + "/../../bad") == null, "invalid page accepted");
        new File(ruby, "safe-mode.enabled").createNewFile();
        check(TweakSettings.page(main) == null, "Safe Mode exposed tweak page");
        check(find(TweakSettings.decorate(ios6), main) == null, "Safe Mode exposed root row");
        TweakSettings.action(toggle);
        check(state.equals(TweakHost.readText(new File(dir, "state.json"))), "Safe Mode changed state");
        new File(ruby, "safe-mode.enabled").delete();
        Files.write(new File(dir, "manifest.json").toPath(), "{}".getBytes("UTF-8"));
        check(TweakSettings.page(main) == null, "corrupt manifest accepted");
        new File(ruby, "coloredbar.enabled").createNewFile();
        check(find(TweakSettings.decorate(ios6), "winterx-cb-picker") != null, "ColoredBar-only installation missing root row");
        System.out.println("Tweak Settings: iOS 4/6 models, nested pages, persisted toggle, integrity and Safe Mode passed");
    }
}
