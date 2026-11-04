package winterx.coloredbar;

import android.graphics.Bitmap;
import E1.T6;
import E1.V6;
import E1.W6;
import java.io.File;
import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import sun.misc.Unsafe;
import winterx.appearance.RubyAppearance;

public final class ColoredBarCheck {
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); }
    static void set(Object object, String name, Object value) throws Exception {
        Field field = object.getClass().getDeclaredField(name); field.setAccessible(true); field.set(object, value);
    }
    static V6 find(T6 page, String id) {
        if (page == null) return null;
        for (Object section : page.c) for (Object row : ((W6) section).c) if (id.equals(((V6) row).a)) return (V6) row;
        return null;
    }
    public static void main(String[] args) throws Exception {
        File ruby = new File(System.getProperty("ruby.test.dir"), "ruby"); ruby.mkdirs();
        check(ColoredBar.page(ColoredBar.PAGE) == null, "uninstalled page visible");
        new File(ruby, ColoredBar.ENABLED).createNewFile();
        check(ColoredBar.page(ColoredBar.PAGE) != null, "Settings page missing");
        String chosen = "139BD7";
        for (int i = 0; i < 6; i++) {
            String digitPage = ColoredBar.PAGE + "/digit/" + i;
            check(digitPage.equals(find(ColoredBar.page(ColoredBar.PAGE), digitPage).e), "digit navigation target incorrect");
            check(ColoredBar.page(digitPage) != null, "hex picker page missing");
            check(ColoredBar.action("winterx-cb-digit/" + i + "/" + chosen.charAt(i)), "hex digit save failed");
        }
        check(chosen.equals(ColoredBar.color()), "arbitrary RGB colour not stored");
        check(!ColoredBar.action("winterx-cb-digit/8/F"), "invalid digit index accepted");
        check(!ColoredBar.action("winterx-cb-color-nope"), "invalid RGB accepted");
        Field unsafeField = Unsafe.class.getDeclaredField("theUnsafe"); unsafeField.setAccessible(true);
        Unsafe unsafe = (Unsafe) unsafeField.get(null);
        E1.q6 state = (E1.q6) unsafe.allocateInstance(E1.q6.class);
        E1.a settings = (E1.a) unsafe.allocateInstance(E1.a.class);
        set(settings, "a", "settings"); set(settings, "b", "Settings");
        E1.a custom = (E1.a) unsafe.allocateInstance(E1.a.class);
        set(custom, "a", "sapp:me.example.app"); set(custom, "b", "My App");
        E1.a phone = (E1.a) unsafe.allocateInstance(E1.a.class);
        set(phone, "a", "phone"); set(phone, "b", "Phone");
        E1.a contacts = (E1.a) unsafe.allocateInstance(E1.a.class);
        set(contacts, "a", "contacts"); set(contacts, "b", "Contacts");
        E1.a appstore = (E1.a) unsafe.allocateInstance(E1.a.class);
        set(appstore, "a", "appstore"); set(appstore, "b", "App Store");
        set(state, "b", Arrays.asList(new E1.c(settings, 0, 0)));
        set(state, "c", Arrays.asList(phone));
        set(state, "n0", Arrays.asList(Arrays.asList(new E1.c(custom, 0, 0), contacts, appstore)));
        ColoredBar.observe(state);
        check(find(ColoredBar.page(ColoredBar.APPS_PAGE), "winterx-cb-exclude/sapp:me.example.app") != null, "secondary-page app not listed");
        check("Phone".equals(find(ColoredBar.page(ColoredBar.APPS_PAGE), "winterx-cb-exclude/phone").b), "dock Phone not listed by name");
        check(find(ColoredBar.page(ColoredBar.APPS_PAGE), "winterx-cb-exclude/contacts") != null, "folder app not listed");
        check(state.c.get(0) == phone && state.b.size() == 1, "app discovery changed icon placement");
        Bitmap original = Bitmap.createBitmap(2, 1, Bitmap.Config.ARGB_8888);
        original.setPixels(new int[]{0x80D7D7D7, 0}, 0, 2, 0, 0, 2, 1);
        Map<String, Object> stock = new HashMap<>();
        String asset = "ios4/uikit/UINavigationBarDefaultBackground.png";
        stock.put(asset, original); stock.put("UINavigationBarDefaultBack.png", original);
        stock.put("ios6/uikit/UINavigationBarShadow.png", original); stock.put("wallpaper.png", original);
        String bottom = "ios4/uikit/UIButtonBarBlackOpaqueBackgroundTall.png";
        stock.put(bottom, original); stock.put("UIButtonBarSelectedIndicator.png", original);
        stock.put("ios4/uikit/UITabBarBlueGradient.png", original);
        String storeBar = "ios6/apps/appstore/NavBar.png";
        stock.put(storeBar, original); stock.put("ios6/apps/appstore/NavBarShadow.png", original);
        stock.put("ios6/apps/other/NavBar.png", original); stock.put("ios6/apps/appstore/UISearch.png", original);
        Map colored = ColoredBar.assets(stock, "settings");
        Bitmap output = (Bitmap) colored.get(asset);
        check(output != original, "navigation asset not tinted");
        check(stock.get(asset) == original, "stock bitmap map modified");
        int[] pixels = new int[2]; output.getPixels(pixels, 0, 2, 0, 0, 2, 1);
        check(pixels[0] == 0x80139BD7 && pixels[1] == 0, "colour/alpha incorrect");
        check(colored.get(asset) == output, "bitmap tint cache missed");
        check(colored.get("wallpaper.png") == original, "non-navigation artwork tinted");
        check(colored.get("ios6/uikit/UINavigationBarShadow.png") == original, "shadow tinted");
        check(colored.get(bottom) == original, "ColoredBar recoloured another app's bottom bar");
        check(new HashMap(colored).get(asset) == output, "map iteration disagrees with get");
        check(ColoredBar.settingsAsset(asset, original) == output, "Settings lazy artwork not tinted");
        check(ColoredBar.settingsAsset(asset, null) == null, "Settings missing artwork fabricated");
        check(ColoredBar.settingsAsset(42, original) == original, "Settings non-string key tinted");
        check(ColoredBar.assets(stock, "appstore").get(storeBar) == output, "custom App Store navigation bar not tinted");
        check(colored.get("ios6/apps/appstore/NavBarShadow.png") == original, "App Store shadow tinted");
        check(colored.get("ios6/apps/other/NavBar.png") == original, "unrecognized app artwork tinted");
        check(colored.get("ios6/apps/appstore/UISearch.png") == original, "App Store search glyph tinted");
        check(ColoredBar.action("winterx-cb-exclude/settings"), "exclude save failed");
        check(ColoredBar.assets(stock, "settings") == stock, "excluded app was tinted");
        check(ColoredBar.settingsAsset(asset, original) == original, "excluded Settings lazy artwork tinted");
        check(ColoredBar.action("winterx-cb-exclude/appstore"), "App Store exclusion save failed");
        check(ColoredBar.assets(stock, "appstore") == stock, "excluded App Store was tinted");
        check(ColoredBar.action("winterx-cb-exclude/phone"), "dock Phone exclusion save failed");
        check(ColoredBar.assets(stock, "phone") == stock, "excluded dock Phone was tinted");
        check(ColoredBar.action("winterx-cb-exclude/phone"), "dock Phone exclusion toggle failed");
        check(ColoredBar.assets(stock, "phone").get(asset) == output, "unexcluded dock Phone lost tint");
        check(ColoredBar.assets(stock, "sapp:me.example.app").get(asset) == output, "non-excluded app lost tint");
        check(!ColoredBar.action("winterx-cb-exclude/unknown.app"), "undeclared app accepted");
        check(ColoredBar.assets(stock, "sapp:com.ruby.manager") == stock, "ColoredBar affected Ruby");
        check(ColoredBar.assets(stock, "com.ruby.manager") == stock, "unprefixed Ruby affected");
        check(!ColoredBar.action("winterx-cb-exclude/sapp:com.ruby.manager"), "Ruby exclusion could be toggled");
        Map rubyBars = RubyAppearance.assets(stock, "sapp:com.ruby.manager");
        Bitmap rubyOutput = (Bitmap) rubyBars.get(asset);
        rubyOutput.getPixels(pixels, 0, 2, 0, 0, 2, 1);
        check(pixels[0] == 0x80C9253D && pixels[1] == 0, "Ruby red/alpha incorrect");
        check(rubyBars.get(bottom) == rubyOutput, "Ruby bottom bar not red");
        check(rubyBars.get("UIButtonBarSelectedIndicator.png") == rubyOutput, "Ruby selected tab not red");
        check(rubyBars.get("ios4/uikit/UITabBarBlueGradient.png") == original, "shared tab glyph cache affected");
        check(ColoredBar.assets(rubyBars, "sapp:com.ruby.manager") == rubyBars, "Ruby base skin overwritten");
        check(RubyAppearance.assets(stock, "settings") == stock, "Ruby styling leaked to Settings");
        check(new HashMap(rubyBars).get(bottom) == rubyOutput, "Ruby map iteration lost red bar");
        new File(ruby, "safe-mode.enabled").createNewFile();
        check(ColoredBar.page(ColoredBar.PAGE) == null, "page active in Safe Mode");
        check(ColoredBar.assets(stock, "sapp:me.example.app") == stock, "Safe Mode did not restore stock artwork");
        check(ColoredBar.settingsAsset(asset, original) == original, "Settings remained tinted in Safe Mode");
        check(!ColoredBar.action("winterx-cb-color-ABCDEF"), "Safe Mode preference write");
        check(chosen.equals(ColoredBar.color()), "Safe Mode changed saved colour");
        check(RubyAppearance.assets(stock, "sapp:com.ruby.manager").get(bottom) == rubyOutput, "Safe Mode removed Ruby branding");
        new File(ruby, ColoredBar.ENABLED).delete();
        check(RubyAppearance.assets(stock, "com.ruby.manager").get(asset) == rubyOutput, "Ruby required an installed tweak");
        check(stock.get(bottom) == original, "Ruby modified shared stock bottom bar");
        System.out.println("ColoredBar: native preferences, immutable per-app artwork and Safe Mode; Ruby: independent red navigation/bottom bars and permanent exclusion passed");
    }
}
