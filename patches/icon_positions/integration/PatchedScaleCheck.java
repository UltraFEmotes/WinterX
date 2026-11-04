import java.io.File;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.IconRuntime;

public class PatchedScaleCheck {
    static Unsafe unsafe() throws Exception { Field f=Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o,String name,Object v) throws Exception { Field f=o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o,v); }
    static void check(boolean value,String why) { if(!value) throw new AssertionError(why); }
    public static void main(String[] args) throws Exception {
        System.setProperty("ruby.test.dir",args[0]);
        E1.t.j = args.length > 1 && Boolean.parseBoolean(args[1]);
        File folder=new File(args[0],"ruby"); folder.mkdirs(); new File(folder,"free-icons.enabled").createNewFile();
        E1.i6 profile=(E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile,"b",640); set(profile,"c",960); set(profile,"d",40); set(profile,"e",114);
        set(profile,"k",new E1.k0(4,4,34,27,38,62,0,0,Arrays.asList(34,186,338,490)));
        x1.i1 host=(x1.i1)unsafe().allocateInstance(x1.i1.class);
        set(host,"e",profile); set(host,"b",E1.r7.T); set(host,"L6",0f);
        x1.P0 cb=x1.P0.class.getDeclaredConstructor(x1.i1.class,int.class).newInstance(host,0);
        E1.i2 model=new E1.i2(new ArrayList<>(),new ArrayList<>(List.of(new ArrayList<>(List.of("one","two")))),new LinkedHashMap<>());
        E1.O1 edit=new E1.O1(model,16,4,cb);
        edit.o(0,0,46.5f,70,1000); check(edit.m!=null,"drag did not start");
        float half=E1.t.j ? 30f : 29.5f;
        edit.m.f=90+edit.m.c+half; edit.m.g=250+edit.m.d+37; edit.w=0; edit.D="two";
        edit.u(0,1000,1,false); edit.D="two"; edit.x(1001);
        int height=960-Math.round((E1.t.j ? 96f : 89f)*2);
        int[] saved=IconRuntime.position(0,"one",640,height,114,114);
        check(saved!=null && saved[0]==180 && saved[1]==500,"incorrect drop: "+Arrays.toString(saved));
        check(edit.D==null && edit.e.toString().equals("[[one, two]]"),"icons merged or reordered");
        E1.a app=(E1.a)unsafe().allocateInstance(E1.a.class); set(app,"a","one");
        E1.c icon=new E1.c(app,0,0);
        set(host,"L1",List.of(icon)); set(host,"S1",new ArrayList<>()); set(host,"M1",new ArrayList<>());
        E1.A0 hit=host.o1(190,510); check(hit!=null,"custom 2x position was not tappable");
        check(host.o1(35,70)==null,"old grid position remained tappable");
        M1.b animation=host.n4(hit);
        check(((Number)animation.h).intValue()==180 && ((Number)animation.w).intValue()==500,"wrong animation coordinates");
        E1.q6 state=(E1.q6)unsafe().allocateInstance(E1.q6.class);
        set(state,"a",profile); set(state,"b",List.of(icon)); set(state,"n0",new ArrayList<>()); set(state,"o0",0f);
        I1.b0 draw=(I1.b0)I1.h0.i0(state).get(0);
        check(draw.b==180 && draw.c==500,"wrong rendered coordinates");
        E1.O1 second=new E1.O1(model,16,4,cb);
        second.o(0,0,90+half,287,2000);
        check(second.m!=null && Math.abs(second.m.c)<.1 && Math.abs(second.m.d)<.1,"moved icon pickup used wrong scale");
        System.out.println("Patched 2x drag, no-merge, draw, tap and repeat pickup passed");
    }
}
