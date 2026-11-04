import java.io.File;
import java.lang.reflect.Method;
import java.util.List;
public class RubyHooksCheck {
  static boolean hasRubyRow(Object root) throws Exception {
    List<?> sections = (List<?>) root.getClass().getField("c").get(root);
    for (Object section : sections) {
      for (Object row : (List<?>) section.getClass().getField("c").get(section)) {
        if ("ruby-test".equals(row.getClass().getField("a").get(row))) return true;
      }
    }
    return false;
  }
  public static void main(String[] args) throws Exception {
    boolean expected = Boolean.parseBoolean(args[0]);
    boolean safe = Boolean.parseBoolean(args[1]);
    Class<?> hooks = Class.forName("ruby.RubyHooks");
    if (((Boolean) hooks.getMethod("safeMode").invoke(null)) != safe) throw new AssertionError("safe mode gate failed");
    Method enabled = hooks.getMethod("settingsEnabled");
    if (((Boolean)enabled.invoke(null)) != expected) throw new AssertionError("marker gate failed");
    Method page = hooks.getMethod("settingsPage", String.class);
    if (page.invoke(null, "wifi") != null) throw new AssertionError("Stock page intercepted");
    Object testPage = page.invoke(null, "ruby-test-page");
    if ((testPage != null) != expected) throw new AssertionError("Page gate failed");
    if (expected) {
      if (!"Ruby Test".equals(testPage.getClass().getField("b").get(testPage))) throw new AssertionError("Page title");
      List<?> sections = (List<?>) testPage.getClass().getField("c").get(testPage);
      List<?> rows = (List<?>) sections.get(0).getClass().getField("c").get(sections.get(0));
      if (rows.size() != 2 || !"ruby-action-alert".equals(rows.get(0).getClass().getField("a").get(rows.get(0))) ||
          !"ruby-action-close".equals(rows.get(1).getClass().getField("a").get(rows.get(1)))) throw new AssertionError("Page actions");
      java.lang.reflect.Field f = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
      f.setAccessible(true);
      sun.misc.Unsafe unsafe = (sun.misc.Unsafe) f.get(null);
      for (String name : new String[]{"E1.B0", "E1.b4"}) {
        Class<?> controller = Class.forName(name);
        Object instance = unsafe.allocateInstance(controller);
        Object result = controller.getMethod("a", String.class).invoke(instance, "ruby-test-page");
        if (result == null || !"Ruby Test".equals(result.getClass().getField("b").get(result)))
          throw new AssertionError(name + " did not resolve the page");
      }
      System.out.println("Ruby Test page and both Settings controllers passed");
    }
    Class<?> settings = Class.forName("E1.Z3");
    Object ios4 = settings.getField("c").get(null);
    if (hasRubyRow(ios4) != expected) throw new AssertionError("iOS 4 root row gate failed");
    List<?> ios6Screens = (List<?>) settings.getField("s").get(null);
    Object ios6 = null;
    for (Object screen : ios6Screens) {
      if ("root".equals(screen.getClass().getField("a").get(screen))) { ios6 = screen; break; }
    }
    if (ios6 == null) throw new AssertionError("iOS 6 root Settings screen not found");
    if (hasRubyRow(ios6) != expected) throw new AssertionError("iOS 6 root row gate failed");
    hooks.getMethod("boot", android.app.Activity.class).invoke(null, new android.app.Activity());
    if (!new File(System.getProperty("ruby.test.dir"), "ruby/boot-ok-v1").isFile()) throw new AssertionError("boot marker missing");
    System.out.println("safe mode=" + safe + "; settings=" + expected + "; iOS 4 and iOS 6 roots match; boot marker present");
  }
}
