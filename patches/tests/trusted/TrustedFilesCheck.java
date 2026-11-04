import java.nio.file.*;
import java.io.File;
import winterx.runtime.TrustedFiles;
public class TrustedFilesCheck {
  static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
  public static void main(String[] args) throws Exception {
    Path root=Paths.get(args[0]).resolve("spring-files");
    Path own=root.resolve("sapps-data/com.winterx.iexplored/files"); Files.createDirectories(own);
    Path script=root.resolve("sapps/com.winterx.iexplored/3/main.js"); Files.createDirectories(script.getParent());
    Files.copy(Paths.get(args[1]),script);
    check(TrustedFiles.resolve(own.toFile(),"winterx/").equals(root.toFile().getCanonicalFile()),"trusted root denied");
    check(TrustedFiles.resolve(own.toFile(),"winterx/notes/test.txt").equals(root.resolve("notes/test.txt").toFile().getCanonicalFile()),"trusted file denied");
    check(TrustedFiles.protectedRoot(own.toFile(),root.toFile().getCanonicalFile()),"root not protected");
    check(TrustedFiles.resolve(own.toFile(),"winterx/../outside")==null,"traversal allowed");
    Path rubyOwn=root.resolve("sapps-data/com.ruby.manager/files"); Files.createDirectories(rubyOwn);
    Path rubyScript=root.resolve("sapps/com.ruby.manager/14/main.js"); Files.createDirectories(rubyScript.getParent());
    Files.copy(Paths.get(args[2]),rubyScript);
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/").equals(root.toFile().getCanonicalFile()),"Ruby root denied");
    Path ruby15=root.resolve("sapps/com.ruby.manager/15/main.js");Files.createDirectories(ruby15.getParent());Files.copy(Paths.get(args[4]),ruby15);
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/").equals(root.toFile().getCanonicalFile()),"Ruby 1.5 root denied");
    Path ruby16=root.resolve("sapps/com.ruby.manager/16/main.js");Files.createDirectories(ruby16.getParent());Files.copy(Paths.get(args[5]),ruby16);
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/").equals(root.toFile().getCanonicalFile()),"Ruby 1.6 root denied");
    Path ruby17=root.resolve("sapps/com.ruby.manager/17/main.js");Files.createDirectories(ruby17.getParent());Files.copy(Paths.get(args[6]),ruby17);
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/")!=null,"Ruby 1.7 root denied");
    Files.writeString(ruby17,"tampered");
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/")==null,"tampered Ruby 1.7 gained access");
    Path ruby18=root.resolve("sapps/com.ruby.manager/18/main.js");Files.createDirectories(ruby18.getParent());Files.copy(Paths.get(args[7]),ruby18);
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/")!=null,"Ruby 1.8 root denied");
    Files.writeString(ruby18,"tampered");
    check(TrustedFiles.resolve(rubyOwn.toFile(),"winterx/")==null,"tampered Ruby 1.8 gained access");
    Path winterx=root.resolve("sapps-data/com.ruby.jailbreak/files"); Files.createDirectories(winterx);
    Path receipt=root.resolve("ruby/boot-ok-v1");Files.createDirectories(receipt.getParent());Files.createFile(receipt);
    check(TrustedFiles.resolve(winterx.toFile(),"winterx/status").equals(receipt.toFile().getCanonicalFile()),"WinterX status not exposed");
    check(TrustedFiles.resolve(winterx.toFile(),"winterx/")==null,"WinterX got broad access");
    Path other=root.resolve("sapps-data/com.other.app/files"); Files.createDirectories(other);
    check(TrustedFiles.resolve(other.toFile(),"winterx/")==null,"ordinary app gained access");
    Path escape=root.resolve("escape"); Files.createSymbolicLink(escape, Paths.get(args[0]));
    check(TrustedFiles.resolve(own.toFile(),"winterx/escape/outside")==null,"symlink escaped root");
    Path newerSupported=root.resolve("sapps/com.winterx.iexplored/4"); Files.createDirectories(newerSupported);
    Files.copy(Paths.get(args[3]), newerSupported.resolve("main.js"));
    check(TrustedFiles.resolve(own.toFile(),"winterx/")!=null,"verified newer IExplored denied");
    Files.delete(newerSupported.resolve("main.js"));Files.delete(newerSupported);
    Path newer=root.resolve("sapps/com.winterx.iexplored/5"); Files.createDirectories(newer);
    check(TrustedFiles.resolve(own.toFile(),"winterx/")==null,"unverified newer app gained access");
    Files.delete(newer);
    Files.writeString(script,"tampered");
    check(TrustedFiles.resolve(own.toFile(),"winterx/")==null,"tampered app gained access");
    System.out.println("Trusted file access and untrusted sandbox separation passed");
  }
}
