package winterx.legacyboot;

import android.app.Activity;
import android.view.View;
import android.view.ViewGroup;

/**
 * Puts a full-screen view over Spring, in the activity's content area: Mac.APK only draws the content area, not other
 * children of the window's decor view. Spring rebuilds the content while it boots, so a view it removes is put back on
 * top until it's dismissed.
 */
final class Overlay {
    private final Activity activity;
    private final View view;
    private ViewGroup parent;
    private boolean shown;
    private android.graphics.Rect bounds;                    // null: the whole content area
    private final ViewGroup.OnHierarchyChangeListener guard = new ViewGroup.OnHierarchyChangeListener() {
        @Override public void onChildViewAdded(View p, View child) { if (shown && child != view) view.post(Overlay.this::top); }
        @Override public void onChildViewRemoved(View p, View child) { if (shown && child == view) view.post(Overlay.this::attach); }
    };

    Overlay(Activity activity, View view) { this.activity = activity; this.view = view; }

    void show() { shown = true; attach(); }

    void dismiss() {
        shown = false;
        if (parent != null) parent.setOnHierarchyChangeListener(null);
        ViewGroup current = (ViewGroup)view.getParent();
        if (current != null) current.removeView(view);
    }

    private void attach() {
        if (!shown) return;
        ViewGroup content = (ViewGroup)activity.findViewById(android.R.id.content);
        if (content == null) return;
        if (content != parent) {
            if (parent != null) parent.setOnHierarchyChangeListener(null);
            parent = content;
            parent.setOnHierarchyChangeListener(guard);
        }
        if (view.getParent() == null) content.addView(view, params());
        top();
    }

    /** Covers just this part of the content area (Spring's screen), or all of it for null. */
    void place(android.graphics.Rect area) {
        if (area == null ? bounds == null : area.equals(bounds)) return;
        bounds = area == null ? null : new android.graphics.Rect(area);
        if (view.getParent() != null) view.setLayoutParams(params());
    }

    private ViewGroup.LayoutParams params() {
        if (bounds == null) return new android.widget.FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        android.widget.FrameLayout.LayoutParams params = new android.widget.FrameLayout.LayoutParams(bounds.width(), bounds.height());
        params.leftMargin = bounds.left; params.topMargin = bounds.top;
        return params;
    }

    /** Anything Spring adds later must stay underneath. */
    private void top() {
        if (shown && view.getParent() == parent && parent.indexOfChild(view) != parent.getChildCount() - 1) view.bringToFront();
    }
}
