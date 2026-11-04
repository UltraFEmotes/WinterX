package android.os;
public class Handler {
    public boolean post(Runnable task) { task.run(); return true; }
}
