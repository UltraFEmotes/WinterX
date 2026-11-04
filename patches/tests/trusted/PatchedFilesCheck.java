import java.nio.file.*;
import java.io.File;
public class PatchedFilesCheck {
  static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
  public static void main(String[] args) throws Exception {
    Path root=Paths.get(args[0]).resolve("files");
    Path app=root.resolve("sapps-data/com.winterx.iexplored");Files.createDirectories(app.resolve("files"));
    Path script=root.resolve("sapps/com.winterx.iexplored/3/main.js");Files.createDirectories(script.getParent());Files.copy(Paths.get(args[1]),script);
    J1.I trusted=new J1.I(app.toFile());
    check(trusted.f("winterx/").equals(root.toFile().getCanonicalFile()),"patched host did not resolve trusted root");
    boolean rejected=false;try{trusted.b("winterx/");}catch(Exception e){rejected=true;}
    check(rejected,"root directory was mutable");
    rejected=false;try{trusted.f("winterx/../escape");}catch(Exception e){rejected=true;}
    check(rejected,"traversal accepted");
    trusted.d("winterx/test.txt", "hello".getBytes("UTF-8"), false);
    check(Files.readString(root.resolve("test.txt")).equals("hello"),"trusted file write failed");
    check(new String(trusted.e("winterx/test.txt"),"UTF-8").equals("hello"),"trusted file read failed");
    Path winterx=root.resolve("sapps-data/com.ruby.jailbreak");Files.createDirectories(winterx.resolve("files"));
    Path receipt=root.resolve("ruby/boot-ok-v1");Files.createDirectories(receipt.getParent());Files.createFile(receipt);
    J1.I jailbreak=new J1.I(winterx.toFile());
    check(jailbreak.f("winterx/status").equals(receipt.toFile().getCanonicalFile()),"WinterX native status was not exposed");
    check(!jailbreak.f("winterx/").equals(root.toFile().getCanonicalFile()),"WinterX got broad file access");
    Path other=root.resolve("sapps-data/com.example.other");Files.createDirectories(other.resolve("files"));
    J1.I ordinary=new J1.I(other.toFile());
    check(!ordinary.f("winterx/").equals(root.toFile().getCanonicalFile()),"ordinary app escaped sandbox");
    System.out.println("Real patched Spring files API: trusted read/write, root protection, traversal and ordinary sandbox passed");
  }
}
