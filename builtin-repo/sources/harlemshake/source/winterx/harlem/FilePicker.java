package winterx.harlem;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import winterx.extension.TweakContext;

/**
 * Opens the system file picker (a real macOS dialog on Mac.APK) from inside Spring. Spring hands every picker
 * result to LauncherActivity.onActivityResult; this tweak claims only its own request code and passes the rest on.
 */
final class FilePicker {
    static final String RESULT = "Lcom/guille/spring/LauncherActivity;->onActivityResult(IILandroid/content/Intent;)V";
    static final int REQUEST = 0x4853;                       // "HS"; Spring's own codes are small numbers
    interface Picked { void picked(Uri file); }
    private static volatile Picked pending;

    static void install(TweakContext context) {
        context.hook(RESULT, call -> {
            if (((Number)call.args[0]).intValue() != REQUEST) return call.proceed();
            Picked picked = pending; pending = null;
            Intent data = (Intent)call.args[2];
            if (picked != null && ((Number)call.args[1]).intValue() == Activity.RESULT_OK && data != null && data.getData() != null)
                picked.picked(data.getData());
            return null;                                     // ours alone; Spring never sees this request
        });
    }

    /** Ask for one file of {@code type} (such as "audio/*"); false when Spring's activity isn't known yet. */
    static boolean open(String type, Picked picked) {
        Activity activity = (Activity)SpringFrames.activity();
        if (activity == null) return false;
        pending = picked;
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType(type);
        new Handler(Looper.getMainLooper()).post(() -> {
            try { activity.startActivityForResult(intent, REQUEST); }
            catch (RuntimeException noPicker) { pending = null; }
        });
        return true;
    }
}
