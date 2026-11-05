package winterx.appearance;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Base64;
import android.widget.ImageView;

/** WinterX boot artwork for the Spring boot overlay, used where the APK's own resources are not replaced (rooted mode). */
public final class BootArt {
    private static final int CYCLE1 = 0x7f050000, CYCLE2 = 0x7f050001;
    private static Bitmap logo;
    private static boolean failed;
    private BootArt() {}

    private static synchronized Bitmap logo() {
        if (logo == null && !failed) {
            try {
                byte[] data = Base64.decode(BootArtData.WEBP, Base64.DEFAULT);
                logo = BitmapFactory.decodeByteArray(data, 0, data.length);
            } catch (RuntimeException e) { logo = null; }
            failed = logo == null;
        }
        return logo;
    }

    /** Replaces only the two boot overlay drawables; any other id or failure keeps Spring's own resource. */
    public static void apply(ImageView view, int id) {
        Bitmap art = id == CYCLE1 || id == CYCLE2 ? logo() : null;
        if (art != null) view.setImageBitmap(art);
        else view.setImageResource(id);
    }
}
