import java.io.File;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import winterx.animaper.AnimaperSettings;
public class AnimaperSettingsCheck {
  static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
  static boolean contains(E1.T6 page,String id) {
    for(Object section:page.c) for(Object row:((E1.W6)section).c) if(id.equals(((E1.V6)row).a))return true;
    return false;
  }
  static String selected(E1.T6 page) {
    String selected=null;
    for(Object row:((E1.W6)page.c.get(0)).c) {
      E1.V6 value=(E1.V6)row;
      if(value.b.contains("✓")) { check(selected==null,"multiple selected modes"); selected=value.a; }
    }
    return selected;
  }
  public static void main(String[] args) throws Exception {
    E1.t.j=args.length>0 && Boolean.parseBoolean(args[0]);
    File dir=new File(System.getProperty("ruby.test.dir"),"ruby");dir.mkdirs();
    Map<File,byte[]> protectedFiles=new LinkedHashMap<>();
    for(String name:new String[]{"../ios4_pages.json","../ios6_pages.json","icon-positions-v1.json","freeme-slots-v1.json","dockin.capacity"}) {
      File file=new File(dir,name); Files.writeString(file.toPath(),"protected "+name); protectedFiles.put(file,Files.readAllBytes(file.toPath()));
    }
    File mode=new File(dir,"animaper.mode");
    Files.writeString(mode.toPath(),"orbit\n"); byte[] original=Files.readAllBytes(mode.toPath());
    E1.T6 ios4=E1.Z3.c, ios6=null;
    for(Object value:E1.Z3.s) { E1.T6 page=(E1.T6)value; if("root".equals(page.a)) ios6=page; }
    check(ios6!=null,"iOS 6 root missing");
    check(!contains(AnimaperSettings.decorate(ios4),AnimaperSettings.ROW),"uninstalled tweak visible");
    new File(dir,"animaper.enabled").createNewFile();
    check(contains(AnimaperSettings.decorate(ios4),AnimaperSettings.ROW),"iOS 4 row missing");
    check(contains(AnimaperSettings.decorate(ios6),AnimaperSettings.ROW),"iOS 6 row missing");
    E1.T6 page=(E1.T6)Class.forName("ruby.RubyHooks").getMethod("settingsPage",String.class).invoke(null,AnimaperSettings.PAGE);
    check(page!=null && ((E1.W6)page.c.get(0)).c.size()==9,"animation page does not have nine options");
    String[] modes={"wave","cascade","bounce","orbit","ripple","columns","fan","zigzag","barrel"};
    for(int index=0;index<modes.length;index++) check(((E1.V6)((E1.W6)page.c.get(0)).c.get(index)).a.equals(AnimaperSettings.PREFIX+modes[index]),"existing effect order changed");
    check(Arrays.equals(original,Files.readAllBytes(mode.toPath())) && selected(page).equals(AnimaperSettings.PREFIX+"orbit"),"upgrade selected Barrel or changed saved mode");
    AnimaperSettings.select(AnimaperSettings.PREFIX+"barrel");
    check(Files.readString(mode.toPath()).trim().equals("barrel"),"explicit Barrel selection not saved");
    check(winterx.animaper.Animaper.barrelEnabled(),"native selection did not invalidate runtime preference");
    page=AnimaperSettings.page(AnimaperSettings.PAGE);
    check(selected(page).equals(AnimaperSettings.PREFIX+"barrel"),"selected mode is not marked");
    AnimaperSettings.select(AnimaperSettings.PREFIX+"orbit");
    check(!winterx.animaper.Animaper.barrelEnabled(),"switching back did not invalidate Barrel");
    AnimaperSettings.select(AnimaperSettings.PREFIX+"invalid");
    check(Files.readString(new File(dir,"animaper.mode").toPath()).trim().equals("orbit"),"invalid choice changed mode");
    new File(dir,"safe-mode.enabled").createNewFile();
    check(!contains(AnimaperSettings.decorate(ios6),AnimaperSettings.ROW) && AnimaperSettings.page(AnimaperSettings.PAGE)==null,"Safe Mode did not hide tweak settings");
    AnimaperSettings.select(AnimaperSettings.PREFIX+"barrel");
    check(Files.readString(mode.toPath()).trim().equals("orbit"),"Safe Mode changed selection");
    Files.delete(new File(dir,"safe-mode.enabled").toPath());
    File target=new File(dir,"mode-target"); Files.writeString(target.toPath(),"orbit\n"); Files.delete(mode.toPath()); Files.createSymbolicLink(mode.toPath(),target.toPath().toAbsolutePath());
    AnimaperSettings.select(AnimaperSettings.PREFIX+"barrel");
    check(Files.isSymbolicLink(mode.toPath()) && Files.readString(target.toPath()).equals("orbit\n"),"mode symlink was followed or replaced");
    for(Map.Entry<File,byte[]> value:protectedFiles.entrySet()) check(Arrays.equals(value.getValue(),Files.readAllBytes(value.getKey().toPath())),"saved layout changed");
    System.out.println("Native Animaper Settings: both roots, nine effects, preserved selection/layouts, explicit Barrel, Safe Mode and link rejection passed");
  }
}
