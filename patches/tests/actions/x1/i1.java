package x1;
import E1.i6;
import E1.P6;
import E1.O1;
import E1.H6;
import E1.i2;
import E1.c;
import E1.a;
import E1.A0;
import E1.z0;
import J1.y;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
/** Records intended native calls only. No render, app launch, runtime destruction or persistence. */
public final class i1 {
    public i6 e;
    public P6 k = P6.w;
    public O1 W1;
    public H6 B, closeMotion;
    public i2 V1;
    public y C3;
    public String E;
    public boolean developer = true, rejectClose;
    public final List<c> L1 = new ArrayList<>();
    public final List<a> M1 = new ArrayList<>();
    public final List<List<c>> S1 = new ArrayList<>();
    public final HashMap<String, Object> D3 = new HashMap<>();
    public final HashMap<String, a> apps = new HashMap<>();
    public final List<String> opens = new ArrayList<>(), closes = new ArrayList<>(), transitions = new ArrayList<>();
    public Thread actionThread;
    public boolean K0() { return developer; }
    public a s2(String id) { return apps.get(id); }
    public A0 m4(String id) { return new A0(z0.h, 0, 0); }
    public void R2(A0 position, a app) { actionThread = Thread.currentThread(); opens.add(app.a); }
    public boolean N(String id, boolean ignored) { actionThread = Thread.currentThread(); if (rejectClose) return false; transitions.add(id); B = closeMotion; return true; }
    public void Q3(String id) { actionThread = Thread.currentThread(); closes.add(id); D3.remove(id); }
}
