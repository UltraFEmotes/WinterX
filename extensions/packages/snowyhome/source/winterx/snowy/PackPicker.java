package winterx.snowy;

import android.app.Activity;
import android.app.ActivityThread;
import android.app.Application;
import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import winterx.extension.TweakContext;

/**
 * Choose an icon-pack ZIP with the system file picker: it's copied into the private inbox and imported straight
 * away, so packs work without anyone reaching into Spring's private folder (a rootless install has no other way in).
 */
public final class PackPicker {
    static final String LOOP = "Lcom/guille/spring/LauncherActivity;->startAnimationLoop()V";
    static final String RESULT = "Lcom/guille/spring/LauncherActivity;->onActivityResult(IILandroid/content/Intent;)V";
    static final int REQUEST = 0x534E;                       // "SN"; Spring's own request codes are small numbers
    private static volatile Activity activity;
    private PackPicker() {}

    public static void install(TweakContext context) {
        context.hook(LOOP, call -> { activity = (Activity)call.self; return call.proceed(); });
        context.hook(RESULT, call -> {
            if (((Number)call.args[0]).intValue() != REQUEST) return call.proceed();
            Intent data = (Intent)call.args[2];
            if (((Number)call.args[1]).intValue() == Activity.RESULT_OK && data != null && data.getData() != null) {
                Uri file = data.getData();
                SnowySettings.importStatus = "Copying the pack…";
                new Thread(() -> SnowySettings.importStatus = copy(file), "WinterX-pack-pick").start();
            }
            return null;                                     // ours alone; Spring never sees this request
        });
    }

    static void open() {
        Activity current = activity;
        if (current == null) { SnowySettings.importStatus = "Go to the Home screen once, then try again"; return; }
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("application/zip");
        new Handler(Looper.getMainLooper()).post(() -> {
            try { current.startActivityForResult(intent, REQUEST); }
            catch (RuntimeException noPicker) { SnowySettings.importStatus = "This device has no file picker"; }
        });
    }

    /** Copy into inbox/ under a safe name, then run the usual validated import. */
    private static String copy(Uri uri) {
        Application app = ActivityThread.currentApplication();
        File dir = SnowyHome.folder();
        if (app == null || dir == null) return "Not imported: SnowyHome isn't ready";
        String name = "pack";
        try (android.database.Cursor row = app.getContentResolver().query(uri, new String[]{android.provider.OpenableColumns.DISPLAY_NAME}, null, null, null)) {
            if (row != null && row.moveToFirst() && row.getString(0) != null) name = row.getString(0);
        } catch (RuntimeException unnamed) {}
        name = name.replaceAll("\\.zip$", "").replaceAll("[^A-Za-z0-9_.-]", "-").replaceAll("^[^A-Za-z0-9]+", "");
        if (name.isEmpty()) name = "pack";
        if (name.length() > 70) name = name.substring(0, 70);
        name += ".zip";
        File inbox = new File(dir, "inbox"), target = new File(inbox, name), temporary = new File(inbox, ".picked.tmp");
        try (InputStream in = app.getContentResolver().openInputStream(uri)) {
            if (in == null) return "Not imported: couldn't open that file";
            inbox.mkdirs();
            if (Files.isSymbolicLink(inbox.toPath())) return "Not imported: the inbox is a link";
            long total = 0;
            try (FileOutputStream out = new FileOutputStream(temporary)) {
                byte[] buffer = new byte[65536];
                for (int n; (n = in.read(buffer)) > 0;) {
                    if ((total += n) > 16L * 1024 * 1024) { out.close(); temporary.delete(); return "Not imported: packs can be up to 16 MB"; }
                    out.write(buffer, 0, n);
                }
                out.getFD().sync();
            }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            String revision = PackImport.install(IconPack.sha(name.getBytes(StandardCharsets.UTF_8)));
            return "Imported " + revision.substring(0, 12) + ". Return to Icon Pack to select it.";
        } catch (Exception failure) {
            temporary.delete();
            return "Not imported: " + failure.getMessage();
        }
    }
}
