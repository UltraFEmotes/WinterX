package J1;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
/** Non-acting installer/runtime spies. They never install an app, execute JS or touch app data. */
public final class y {
    public ExecutorService i;
    public P g;
    public Object k = new HashMap<String, Object>();
    public final HashMap<String, Object> l = new HashMap<>(), m = new HashMap<>();
    public final HashSet<String> r = new HashSet<>();
    public final Map<String, Object> rendered = new HashMap<>();
    public final List<String> destroyed = new ArrayList<>(), accepted = new ArrayList<>();
    public Thread installThread;
    public Map<String, Object> d() { return rendered; }
    public void i(String id) { destroyed.add(id); l.remove(id); m.remove(id); r.remove(id); }
    public String winterxInstallArchive(File archive) throws Exception {
        if (android.os.Looper.myLooper() == android.os.Looper.getMainLooper() || !archive.isFile() || !archive.getParentFile().getName().equals("prepared"))
            throw new AssertionError("unsafe fixture installer dispatch");
        installThread = Thread.currentThread(); String id = H1.Q.h(archive).a; accepted.add(id); return id;
    }
}
