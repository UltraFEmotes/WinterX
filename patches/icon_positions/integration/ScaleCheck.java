import java.io.File;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.IconRuntime;
import winterx.layout.SpringHooks;

/** Uses Spring's 640x960 @2x profile while its editor works in 320-wide points. */
public class ScaleCheck {
    static Unsafe unsafe() throws Exception { Field f=Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o,String name,Object v) throws Exception { Field f=o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o,v); }
    static void check(boolean value,String why) { if(!value) throw new AssertionError(why); }
    public static void main(String[] args) throws Exception {
        System.setProperty("ruby.test.dir",args[0]);
        File folder=new File(args[0],"ruby"); folder.mkdirs(); new File(folder,"free-icons.enabled").createNewFile();
        E1.i6 profile=(E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile,"b",640); set(profile,"c",960); set(profile,"d",40); set(profile,"e",114);
        set(profile,"k",new E1.k0(4,4,34,27,38,62,0,0,Arrays.asList(34,186,338,490)));
        x1.i1 host=(x1.i1)unsafe().allocateInstance(x1.i1.class); set(host,"e",profile);
        x1.P0 cb=x1.P0.class.getDeclaredConstructor(x1.i1.class,int.class).newInstance(host,0);
        E1.i2 model=new E1.i2(new ArrayList<>(),new ArrayList<>(List.of(new ArrayList<>(List.of("one","two")))),new LinkedHashMap<>());
        E1.O1 edit=new E1.O1(model,16,4,cb);
        SpringHooks.begin(edit,0,0); edit.o(0,0,46.5f,70,1000);
        check(edit.m!=null,"drag missing");
        float editingHalf=E1.t.j ? 30f : 29.5f;
        edit.m.f=90+edit.m.c+editingHalf; edit.m.g=250+edit.m.d+37; edit.w=0; edit.D="two";
        SpringHooks.beforeDrop(edit); edit.x(1001);
        int height=960-Math.round((E1.t.j ? 96f : 89f)*2);
        int[] stored=IconRuntime.position(0,"one",640,height,114,114);
        check(stored!=null,"drop was not recorded");
        check(stored[0]==180 && stored[1]==500,"wrong physical coordinates: "+Arrays.toString(stored));
        M1.b editPoint=SpringHooks.editLocation(edit,0,0);
        check(editPoint!=null && Math.abs(((Number)editPoint.h).floatValue()-90)<.1 && Math.abs(((Number)editPoint.w).floatValue()-250)<.1,"edit coordinates wrong");
        E1.a app=(E1.a)unsafe().allocateInstance(E1.a.class); set(app,"a","one");
        M1.b draw=SpringHooks.location(profile,new E1.c(app,0,0),0);
        check(((Number)draw.h).intValue()==180 && ((Number)draw.w).intValue()==500,"draw coordinates wrong");
        check(edit.e.toString().equals("[[one, two]]"),"layout changed");
        System.out.println("Real 2x profile drag, render and edit coordinate conversion passed");
    }
}
