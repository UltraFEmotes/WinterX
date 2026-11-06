package winterx.legacyboot;

import android.app.Activity;
import android.graphics.Rect;
import android.view.View;
import android.view.ViewGroup;

/**
 * Where Spring draws its phone screen inside the content area. With Spring's frame on, that's the glass inside the
 * frame; frameless, it's the whole window. Spring's main view (x1.N1) keeps it as a Viewport: offset, size and scale.
 */
final class SpringScreen {
    private SpringScreen() {}

    /** The screen in content-area coordinates, or null when Spring's main view isn't there yet. */
    static Rect rect(Activity activity) {
        ViewGroup content = (ViewGroup)activity.findViewById(android.R.id.content);
        View main = content == null ? null : find(content);
        if (main == null || main.getWidth() == 0) return null;
        I1.i1 viewport = ((x1.N1)main).c();
        if (viewport == null || viewport.d <= 0 || viewport.e <= 0) return null;
        int[] at = new int[2], origin = new int[2];
        main.getLocationInWindow(at);
        content.getLocationInWindow(origin);
        int left = at[0] - origin[0] + viewport.b, top = at[1] - origin[1] + viewport.c;
        return new Rect(left, top, left + viewport.d, top + viewport.e);
    }

    static View main(Activity activity) {
        ViewGroup content = (ViewGroup)activity.findViewById(android.R.id.content);
        return content == null ? null : find(content);
    }

    private static View find(View view) {
        if (view instanceof x1.N1) return view;
        if (!(view instanceof ViewGroup)) return null;
        ViewGroup group = (ViewGroup)view;
        for (int i = 0; i < group.getChildCount(); i++) {
            View found = find(group.getChildAt(i));
            if (found != null) return found;
        }
        return null;
    }
}
