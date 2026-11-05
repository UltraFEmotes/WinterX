import java.io.File;
import java.lang.reflect.Field;
import java.util.Arrays;
import sun.misc.Unsafe;
public class AnimaperCheck {
  static void set(Object target,String name,Object value) throws Exception { Field f=target.getClass().getDeclaredField(name);f.setAccessible(true);f.set(target,value); }
  static void eq(M1.b a,M1.b b,String message) { if (!a.h.equals(b.h) || !a.w.equals(b.w)) throw new AssertionError(message); }
  public static void main(String[] args) throws Exception {
    E1.t.j=args.length>0 && Boolean.parseBoolean(args[0]);
    Field f=Unsafe.class.getDeclaredField("theUnsafe");f.setAccessible(true);Unsafe u=(Unsafe)f.get(null);
    E1.i6 profile=(E1.i6)u.allocateInstance(E1.i6.class);
    set(profile,"b",640);set(profile,"c",960);set(profile,"d",40);set(profile,"e",114);
    set(profile,"k",new E1.k0(4,4,34,27,38,62,0,0,Arrays.asList(34,186,338,490)));
    E1.a app=(E1.a)u.allocateInstance(E1.a.class);set(app,"a","test.app");
    E1.c entry=new E1.c(app,1,2);
    E1.q6 state=(E1.q6)u.allocateInstance(E1.q6.class);
    set(state,"a",profile); set(state,"b",Arrays.asList(entry)); set(state,"n0",new java.util.ArrayList<>()); set(state,"o0",160f);
    I1.b0 plain=(I1.b0)I1.h0.i0(state).get(0);
    M1.b original=winterx.layout.SpringHooks.location(profile,entry,0);
    eq(winterx.animaper.Animaper.location(profile,entry,0,320),original,"disabled animation moved icon");
    File dir=new File(System.getProperty("ruby.test.dir"),"ruby");dir.mkdirs();new File(dir,"animaper.enabled").createNewFile();
    eq(winterx.animaper.Animaper.location(profile,entry,0,0),original,"settled icon moved");
    M1.b animated=winterx.animaper.Animaper.location(profile,entry,0,320);
    I1.b0 rendered=(I1.b0)I1.h0.i0(state).get(0);
    if (rendered.b==plain.b && rendered.c==plain.c) throw new AssertionError("Spring renderer did not animate icon");
    if (animated.h.equals(original.h) && animated.w.equals(original.w)) throw new AssertionError("swiping icon did not animate");
    new File(dir,"safe-mode.enabled").createNewFile();
    eq(winterx.animaper.Animaper.location(profile,entry,0,320),original,"Safe Mode did not disable animation");
    I1.b0 safe=(I1.b0)I1.h0.i0(state).get(0);
    if (safe.b!=plain.b || safe.c!=plain.c) throw new AssertionError("Spring renderer animated in Safe Mode");
    System.out.println("Animaper adapter: disabled, swipe, settled and Safe Mode passed");
  }
}
