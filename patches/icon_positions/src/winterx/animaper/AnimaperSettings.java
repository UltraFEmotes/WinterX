package winterx.animaper;

import android.app.ActivityThread;
import android.app.Application;
import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Native Spring Settings page for the Animaper tweak. */
public final class AnimaperSettings {
    public static final String PAGE = "winterx-animaper-page";
    public static final String ROW = "winterx-animaper";
    public static final String PREFIX = "winterx-animaper-mode-";
    private static final String[] MODES = {"wave", "cascade", "bounce", "orbit", "ripple", "columns", "fan", "zigzag"};
    private AnimaperSettings() {}
    private static File folder() {
        Application app = ActivityThread.currentApplication();
        return app == null ? null : new File(app.getFilesDir(), "ruby");
    }
    public static boolean enabled() {
        try { File dir = folder(); return dir != null && !new File(dir,"safe-mode.enabled").isFile() && new File(dir,"animaper.enabled").isFile(); }
        catch (RuntimeException ignored) { return false; }
    }
    private static V6 row(String id, String title) { return Z3.g(Z3.a,id,title,null,null,null,0x18); }
    private static String current() {
        try {
            File dir=folder(); File file=dir == null ? null : new File(dir,"animaper.mode");
            if (file == null || !file.isFile() || file.length() > 64) return "wave";
            byte[] bytes=new byte[64];
            try (FileInputStream in=new FileInputStream(file)) {
                int n=in.read(bytes); return n < 1 ? "wave" : new String(bytes,0,n,StandardCharsets.UTF_8).trim();
            }
        } catch (Exception ignored) { return "wave"; }
    }
    /** Add a separate section dynamically, so live installation needs no reboot. */
    public static T6 decorate(T6 page) {
        if (page == null || !"root".equals(page.a) || !enabled()) return page;
        try {
            for (Object sectionObject : page.c) {
                W6 section=(W6)sectionObject;
                for (Object rowObject : section.c) if (ROW.equals(((V6)rowObject).a)) return page;
            }
            List<W6> sections=new ArrayList<>();
            for (Object section : page.c) sections.add((W6)section);
            sections.add(new W6(null,null,null,null,Collections.singletonList(row(ROW,"Animaper"))));
            return new T6(page.a,page.b,sections);
        } catch (RuntimeException ignored) { return page; }
    }
    public static T6 page(String id) {
        if (!PAGE.equals(id) || !enabled()) return null;
        String selected=current();
        List<V6> rows=new ArrayList<>();
        for (String mode : MODES) {
            String title=Character.toUpperCase(mode.charAt(0))+mode.substring(1);
            rows.add(row(PREFIX+mode, title+(mode.equals(selected) ? "  ✓" : "")));
        }
        return new T6(PAGE,"Animaper",Collections.singletonList(new W6("PAGE ANIMATION",null,null,null,rows)));
    }
    public static void select(String id) {
        if (!enabled() || id == null || !id.startsWith(PREFIX)) return;
        String mode=id.substring(PREFIX.length());
        boolean found=false; for (String value : MODES) if (value.equals(mode)) found=true;
        if (!found) return;
        File dir=folder(), temp=null;
        try {
            temp=File.createTempFile(".animaper-", ".tmp", dir);
            try (FileOutputStream out=new FileOutputStream(temp)) {
                out.write((mode+"\n").getBytes(StandardCharsets.UTF_8)); out.getFD().sync();
            }
            if (!temp.renameTo(new File(dir,"animaper.mode"))) throw new java.io.IOException("Could not save animation");
        } catch (Exception ignored) { }
        finally { if (temp != null && temp.exists()) temp.delete(); }
    }
}
