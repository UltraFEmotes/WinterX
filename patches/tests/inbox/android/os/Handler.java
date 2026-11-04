package android.os;
public class Handler { public Runnable next; public boolean postDelayed(Runnable r,long delay){next=r;return true;} public void tick(){Runnable r=next;next=null;r.run();} }
