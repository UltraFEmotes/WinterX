import android.content.res.AssetManager;
import java.io.File;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
public class TintCheck {
    static String open(AssetManager assets, String path) throws Exception {
        return new String(ruby.RubyHooks.openAsset(assets, path).readAllBytes(), StandardCharsets.UTF_8);
    }
    public static void main(String[] args) throws Exception {
        File base = new File(System.getProperty("ruby.test.dir"));
        File folder = new File(base, "ruby"); folder.mkdirs();
        String path = "ios6/uikit/UINavigationBarDefaultBackground.png";
        File themed = new File(folder, "theme/" + path); themed.getParentFile().mkdirs();
        Files.writeString(themed.toPath(), "red");
        AssetManager assets = new AssetManager();
        if (!open(assets, path).equals("original:" + path)) throw new AssertionError("Theme enabled without marker");
        new File(folder, "ui-colors.enabled").createNewFile();
        if (!open(assets, path).equals("red")) throw new AssertionError("Themed bar missing");
        String other = "ios6/wallpapers/home.png";
        if (!open(assets, other).equals("original:" + other)) throw new AssertionError("Wallpaper was altered");
        String missing = "ios6/uikit/UINavigationBarMissing.png";
        if (!open(assets, missing).equals("original:" + missing)) throw new AssertionError("Missing theme did not fall back");
        String escape = "ios6/uikit/UINavigationBar../secret.png";
        if (!open(assets, escape).equals("original:" + escape)) throw new AssertionError("Invalid path accepted");
        new File(folder, "safe-mode.enabled").createNewFile();
        if (!open(assets, path).equals("original:" + path)) throw new AssertionError("Theme active in Safe Mode");
        System.out.println("Navigation bar assets, fallback and Safe Mode passed");
    }
}
