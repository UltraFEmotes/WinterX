import java.io.File;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;
public class PatchedDisabledCheck {
    static Unsafe unsafe() throws Exception { Field f=Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o,String name,Object v) throws Exception { Field f=o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o,v); }
    static void check(boolean value,String message) { if (!value) throw new AssertionError(message); }
    public static void main(String[] args) throws Exception {
        System.setProperty("ruby.test.dir", args[0]);
        E1.i6 profile=(E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile,"b",320); set(profile,"c",568); set(profile,"d",20); set(profile,"e",60);
        set(profile,"k",new E1.k0(4,4,0,0,10,10,0,0,Arrays.asList(0,70,140,210)));
        x1.i1 host=(x1.i1)unsafe().allocateInstance(x1.i1.class);
        set(host,"e",profile); set(host,"b",E1.r7.T); set(host,"L6",0f);
        E1.a app=(E1.a)unsafe().allocateInstance(E1.a.class); set(app,"a","one");
        set(host,"L1",List.of(new E1.c(app,0,0))); set(host,"S1",new ArrayList<>()); set(host,"M1",new ArrayList<>());
        check(host.o1(10,30)!=null && host.o1(180,240)==null,"disabled hit testing differs from grid");
        E1.i2 model=new E1.i2(new ArrayList<>(),new ArrayList<>(List.of(new ArrayList<>(List.of("one","two")))),new LinkedHashMap<>());
        x1.P0 cb=x1.P0.class.getDeclaredConstructor(x1.i1.class,int.class).newInstance(host,0);
        E1.O1 edit=new E1.O1(model,16,4,cb);
        edit.o(0,0,40,100,1000); check(edit.m!=null,"stock drag did not start");
        edit.x(1001); check(edit.e.toString().equals("[[one, two]]"),"disabled drag changed layout unexpectedly");
        check(!new File(args[0],"ruby/icon-positions-v1.json").exists(),"disabled tweak wrote position data");
        System.out.println("Disabled tweak leaves stock touch and drag behavior intact");
    }
}
