import java.io.File;
import java.nio.file.Files;
import java.util.List;
import winterx.animaper.AnimaperSettings;
public class AnimaperSettingsCheck {
  static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
  static boolean contains(E1.T6 page,String id) {
    for(Object section:page.c) for(Object row:((E1.W6)section).c) if(id.equals(((E1.V6)row).a))return true;
    return false;
  }
  public static void main(String[] args) throws Exception {
    File dir=new File(System.getProperty("ruby.test.dir"),"ruby");dir.mkdirs();
    E1.T6 ios4=E1.Z3.c, ios6=null;
    for(Object value:E1.Z3.s) { E1.T6 page=(E1.T6)value; if("root".equals(page.a)) ios6=page; }
    check(ios6!=null,"iOS 6 root missing");
    check(!contains(AnimaperSettings.decorate(ios4),AnimaperSettings.ROW),"uninstalled tweak visible");
    new File(dir,"animaper.enabled").createNewFile();
    check(contains(AnimaperSettings.decorate(ios4),AnimaperSettings.ROW),"iOS 4 row missing");
    check(contains(AnimaperSettings.decorate(ios6),AnimaperSettings.ROW),"iOS 6 row missing");
    E1.T6 page=(E1.T6)Class.forName("ruby.RubyHooks").getMethod("settingsPage",String.class).invoke(null,AnimaperSettings.PAGE);
    check(page!=null && ((E1.W6)page.c.get(0)).c.size()==8,"animation page does not have eight options");
    AnimaperSettings.select(AnimaperSettings.PREFIX+"orbit");
    check(Files.readString(new File(dir,"animaper.mode").toPath()).trim().equals("orbit"),"mode not saved");
    page=AnimaperSettings.page(AnimaperSettings.PAGE);
    boolean selected=false;
    for(Object row:((E1.W6)page.c.get(0)).c) if(((E1.V6)row).b.startsWith("Orbit") && ((E1.V6)row).b.contains("✓")) selected=true;
    check(selected,"selected mode is not marked");
    AnimaperSettings.select(AnimaperSettings.PREFIX+"invalid");
    check(Files.readString(new File(dir,"animaper.mode").toPath()).trim().equals("orbit"),"invalid choice changed mode");
    new File(dir,"safe-mode.enabled").createNewFile();
    check(!contains(AnimaperSettings.decorate(ios6),AnimaperSettings.ROW) && AnimaperSettings.page(AnimaperSettings.PAGE)==null,"Safe Mode did not hide tweak settings");
    System.out.println("Native Animaper Settings: both roots, eight effects, selection and Safe Mode passed");
  }
}
