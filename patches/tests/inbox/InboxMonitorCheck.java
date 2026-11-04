import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
public class InboxMonitorCheck {
  public static void main(String[] args) throws Exception {
    Path dir=Path.of(args[0]); J1.y manager=new J1.y(); manager.a.inbox=dir.toFile(); manager.a.files=dir.toFile();
    winterx.runtime.InboxMonitor.start(manager);
    Files.writeString(dir.resolve("incomplete.pending"),"a"); manager.h.tick(); manager.h.tick();
    if(manager.calls!=0) throw new AssertionError("pending copy processed");
    Path pkg=dir.resolve("example.sapp"); Files.writeString(pkg,"first"); manager.h.tick();
    if(manager.calls!=0) throw new AssertionError("new copy processed before stable");
    Files.writeString(pkg,"longer-copy"); manager.h.tick();
    if(manager.calls!=0) throw new AssertionError("changing copy processed");
    manager.h.tick(); if(manager.calls!=1) throw new AssertionError("stable app not processed");
    manager.h.tick(); if(manager.calls!=1) throw new AssertionError("installer spammed");
    manager.a.destroyed=true;manager.h.tick(); if(manager.h.next!=null) throw new AssertionError("monitor kept destroyed activity alive");
    System.out.println("Inbox monitor waits for stable files and stops on exit");
  }
}
