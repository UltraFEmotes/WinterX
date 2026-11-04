import java.io.File;
import java.lang.reflect.Field;
import java.util.*;
import sun.misc.Unsafe;
import winterx.layout.IconRuntime;

/** Tests patched Spring 0.8.1 classes loaded from the converted multi-dex APK. */
public class PatchedControllerCheck {
    static Unsafe unsafe() throws Exception { Field f=Unsafe.class.getDeclaredField("theUnsafe"); f.setAccessible(true); return (Unsafe)f.get(null); }
    static void set(Object o,String name,Object v) throws Exception { Field f=o.getClass().getDeclaredField(name); f.setAccessible(true); f.set(o,v); }
    static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
    static void drop(E1.O1 edit,int index,float x,float y,long now) {
        edit.o(0,index,40,100,now);
        check(edit.m!=null,"native drag did not start");
        edit.m.f=x+edit.m.c+(E1.t.j ? 30f : 29.5f); edit.m.g=y+edit.m.d+37; edit.w=0;
        edit.x(now+1);
    }
    public static void main(String[] args) throws Exception {
        File root=new File(args[0]); System.setProperty("ruby.test.dir",root.toString());
        File folder=new File(root,"ruby"); folder.mkdirs(); new File(folder,"free-icons.enabled").createNewFile();
        E1.i6 profile=(E1.i6)unsafe().allocateInstance(E1.i6.class);
        set(profile,"b",320); set(profile,"c",568); set(profile,"d",20); set(profile,"e",60);
        set(profile,"k",new E1.k0(4,4,0,0,10,10,0,0,Arrays.asList(0,70,140,210)));
        x1.i1 host=(x1.i1)unsafe().allocateInstance(x1.i1.class);
        set(host,"e",profile); set(host,"b",E1.r7.T); set(host,"L6",0f);
        x1.P0 callback=x1.P0.class.getDeclaredConstructor(x1.i1.class,int.class).newInstance(host,0);
        E1.i2 model=new E1.i2(new ArrayList<>(),new ArrayList<>(List.of(new ArrayList<>(List.of("one","two")))),new LinkedHashMap<>());
        E1.O1 edit=new E1.O1(model,16,4,callback);
        drop(edit,0,180,240,1000);
        check(edit.e.toString().equals("[[one, two]]"),"original layout changed");
        int[] saved=IconRuntime.position(0,"one",320,479,60,60);
        check(saved!=null && saved[0]==180 && saved[1]==240,"drop not saved");
        E1.a app=(E1.a)unsafe().allocateInstance(E1.a.class); set(app,"a","one");
        E1.c icon=new E1.c(app,0,0);
        set(host,"L1",List.of(icon)); set(host,"S1",new ArrayList<>()); set(host,"M1",new ArrayList<>());
        E1.A0 hit=host.o1(190,250);
        check(hit!=null && hit.b==0 && hit.c==0,"touch did not hit moved icon");
        check(host.o1(10,30)==null,"old position remained tappable");
        M1.b animation=host.n4(hit);
        check(((Number)animation.h).intValue()==180 && ((Number)animation.w).intValue()==240,"launch animation position incorrect");
        E1.O1 repeat=new E1.O1(model,16,4,callback);
        repeat.o(0,0,209.5f,277,1200); // Finger begins on the previously moved icon.
        check(repeat.m!=null && Math.abs(repeat.m.c)<1f && Math.abs(repeat.m.d)<1f,"edit drag started at the old grid position: " + (repeat.m == null ? "missing" : repeat.m.c + ", " + repeat.m.d));
        repeat.m.f=229.5f; repeat.m.g=347; repeat.u(0, 1200, 1, false); repeat.D="two"; repeat.x(1201);
        int[] movedAgain=IconRuntime.position(0,"one",320,479,60,60);
        check(movedAgain[0]==200 && movedAgain[1]==310,"free drag with a stale folder target failed");
        check(repeat.D==null && repeat.e.toString().equals("[[one, two]]"),"free drag merged or reordered icons");
        check(IconRuntime.record(0,"one",180,240,320,479,60,60),"could not reset test position");
        E1.q6 state=(E1.q6)unsafe().allocateInstance(E1.q6.class);
        set(state,"a",profile); set(state,"b",List.of(icon)); set(state,"n0",new ArrayList<>()); set(state,"o0",0f);
        ArrayList<?> rendered=I1.h0.i0(state);
        check(rendered.size()==1,"renderer did not return the icon");
        I1.b0 draw=(I1.b0)rendered.get(0);
        check(draw.b==180 && draw.c==240,"draw position differs from touch position");
        E1.a otherApp=(E1.a)unsafe().allocateInstance(E1.a.class); set(otherApp,"a","three");
        E1.c otherIcon=new E1.c(otherApp,0,0);
        check(IconRuntime.record(1,"three",150,300,320,479,60,60),"second-page record failed");
        set(host,"S1",List.of(List.of(otherIcon))); set(host,"L6",320f);
        E1.A0 secondHit=host.o1(160,310);
        check(secondHit!=null && secondHit.c==1,"second-page touch missed");
        M1.b secondAnimation=host.n4(secondHit);
        check(((Number)secondAnimation.h).intValue()==150 && ((Number)secondAnimation.w).intValue()==300,"second-page launch position incorrect");
        set(state,"n0",List.of(List.of(otherIcon))); set(state,"o0",320f);
        ArrayList<?> secondRendered=I1.h0.i0(state);
        check(secondRendered.size()==1,"second-page renderer missing icon");
        I1.b0 secondDraw=(I1.b0)secondRendered.get(0);
        check(secondDraw.b==150 && secondDraw.c==300,"second-page render differs from touch");
        E1.O1 next=new E1.O1(model,16,4,callback);
        drop(next,0,70,20,2000);
        saved=IconRuntime.position(0,"one",320,479,60,60);
        check(saved[0]==180 && saved[1]==240,"overlap changed saved position");
        check(next.e.toString().equals("[[one, two]]"),"overlap changed original order");
        E1.O1 folderDrop=new E1.O1(model,16,4,callback);
        folderDrop.o(0,0,210,277,3000);
        folderDrop.D="two";
        folderDrop.m.f=100; folderDrop.m.g=57; folderDrop.w=0;
        folderDrop.x(3001);
        check(folderDrop.D==null,"folder target was not cleared");
        check(folderDrop.e.toString().equals("[[one, two]]"),"overlapping drag changed Spring's layout");
        saved=IconRuntime.position(0,"one",320,479,60,60);
        check(saved[0]==180 && saved[1]==240,"overlapping drag changed the saved position");
        new File(folder,"safe-mode.enabled").createNewFile();
        set(host,"L6",0f);
        check(IconRuntime.position(0,"one",320,479,60,60)==null,"Safe Mode did not disable position");
        check(host.o1(190,250)==null,"Safe Mode left custom hit active");
        check(host.o1(10,30)!=null,"Safe Mode did not restore the grid");
        System.out.println("Patched Spring renderer, touch, drop, collision and Safe Mode passed");
    }
}
