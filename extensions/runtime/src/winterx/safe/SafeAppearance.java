package winterx.safe;

import android.app.ActivityThread;
import android.app.Application;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import java.io.File;

/** Appearance overrides for Safe Mode. The user's wallpaper is never changed. */
public final class SafeAppearance {
    private SafeAppearance() {}
    private static boolean enabled() {
        try {
            Application app = ActivityThread.currentApplication();
            return app != null && new File(app.getFilesDir(), "ruby/safe-mode.enabled").isFile();
        } catch (RuntimeException e) { return false; }
    }
    public static boolean wallpaper(Canvas canvas, E1.i6 profile) {
        if (!enabled()) return false;
        try {
            float width = profile.b, height = profile.c;
            if (width <= 0 || height <= 0) return false;
            canvas.drawColor(Color.rgb(12, 32, 60));
            Paint paint = new Paint(3);
            paint.setColor(Color.rgb(222, 240, 255));
            paint.setStrokeCap(Paint.Cap.ROUND);
            float cx = width / 2, cy = height * .43f, radius = width * .19f;
            paint.setStrokeWidth(width * .018f);
            for (int n = 0; n < 6; n++) {
                double angle = Math.PI * n / 3 - Math.PI / 2;
                float ux = (float)Math.cos(angle), uy = (float)Math.sin(angle);
                canvas.drawLine(cx, cy, cx + ux * radius, cy + uy * radius, paint);
                float bx = cx + ux * radius * .65f, by = cy + uy * radius * .65f;
                for (int sign : new int[]{-1, 1}) {
                    double branch = angle + sign * Math.PI / 3;
                    canvas.drawLine(bx, by, bx + (float)Math.cos(branch) * radius * .32f,
                                    by + (float)Math.sin(branch) * radius * .32f, paint);
                }
            }
            paint.setTypeface(Typeface.DEFAULT_BOLD);
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTextSize(width * .075f);
            canvas.drawText("WinterX", cx, cy + radius + width * .13f, paint);
            paint.setTextSize(width * .045f);
            canvas.drawText("SAFE MODE", cx, height * .86f, paint);
            return true;
        } catch (RuntimeException e) { return false; }
    }
    public static void status(Canvas canvas) {
        if (!enabled()) return;
        try {
            int width = canvas.getWidth();
            if (width <= 0) return;
            Paint paint = new Paint(3);
            paint.setColor(Color.rgb(45, 145, 255));
            paint.setTypeface(Typeface.DEFAULT_BOLD);
            paint.setTextSize(width * .026f);
            paint.setTextAlign(Paint.Align.CENTER);
            canvas.drawText("SAFE MODE", width * .72f, 28f, paint);
        } catch (RuntimeException ignored) { }
    }
}
