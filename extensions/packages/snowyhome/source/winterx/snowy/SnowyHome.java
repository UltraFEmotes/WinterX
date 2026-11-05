package winterx.snowy;

import android.app.ActivityThread;
import android.app.Application;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Rect;
import android.graphics.RectF;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.AbstractMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import org.json.JSONObject;

/** Opt-in per-icon copies. Never replaces shared artwork, geometry, app labels or saved pages. */
public final class SnowyHome {
    public static final String ABI = "snowyhome-render-v1";
    private static final int CACHE_BYTES = 16 * 1024 * 1024;
    private static final LinkedHashMap<String, Cached> cache = new LinkedHashMap<>(16, .75f, true);
    private static int cacheBytes;
    private static long lastRead;
    private static File observedFolder;
    private static String selected = "stock", badge = "stock";
    private static double corners = -1;
    private static boolean hideLabels;
    private static IconPack pack;
    private static final class Cached {
        final Bitmap source, image;
        Cached(Bitmap source, Bitmap image) { this.source = source; this.image = image; }
    }
    private SnowyHome() {}
    static File folder() {
        Application app = ActivityThread.currentApplication();
        if (app == null) return null;
        try {
            // Resolve the platform-owned files alias once, retaining link refusal
            // below that boundary for preferences, inboxes and immutable packs.
            File root = new File(app.getFilesDir().getCanonicalFile(), "ruby"), dir = new File(root, "snowyhome");
            return Files.isSymbolicLink(root.toPath()) || Files.isSymbolicLink(dir.toPath()) ? null : dir;
        } catch (Exception failure) { return null; }
    }
    public static boolean enabled() {
        return winterx.extension.NativeRuntime.enabled("com.winterx.snowyhome");
    }
    static synchronized void refresh(boolean force) {
        File dir = folder(); long now = android.os.SystemClock.elapsedRealtime();
        if (!force && java.util.Objects.equals(dir, observedFolder) && lastRead != 0 && now >= lastRead && now - lastRead < 500) return;
        JSONObject value = new JSONObject();
        try { if (dir != null) value = new JSONObject(new String(IconPack.read(new File(dir, "preferences.json"), 4096), StandardCharsets.UTF_8)); }
        catch (Exception ignored) {}
        String nextPack = value.optString("pack", "stock"), nextBadge = value.optString("badge", "stock");
        if (!nextPack.equals("stock") && !nextPack.matches("[0-9a-f]{64}")) nextPack = "stock";
        if (!nextBadge.equals("stock") && !nextBadge.matches("#[0-9A-Fa-f]{6}")) nextBadge = "stock";
        double nextCorners = value.optDouble("corners", -1);
        if (Double.isNaN(nextCorners) || Double.isInfinite(nextCorners) || (nextCorners != -1 && (nextCorners < 0 || nextCorners > .5))) nextCorners = -1;
        if (!java.util.Objects.equals(dir, observedFolder) || !nextPack.equals(selected) || !nextBadge.equals(badge) || nextCorners != corners) {
            // Do not recycle images held by Spring's render caches; let GC reclaim unused copies.
            cache.clear(); cacheBytes = 0; pack = null;
        }
        selected = nextPack; badge = nextBadge; corners = nextCorners; hideLabels = value.optBoolean("hideLabels", false);
        observedFolder = dir; lastRead = now;
        if (!selected.equals("stock") && pack == null && dir != null) pack = IconPack.load(new File(dir, "packs"), selected);
    }
    public static synchronized boolean hiddenLabels() { if (!enabled()) return false; refresh(false); return hideLabels; }
    /** With labels hidden, centre each Home icon in its cell by moving it down half of the label gap. Dock icons stay put. */
    public static Integer beginIcon(android.graphics.Canvas canvas, E1.i6 profile, int y) {
        if (canvas == null || profile == null || profile.k == null || !hiddenLabels()) return null;
        if (profile.l != null && y >= profile.c - profile.l.c - profile.e - 1) return null;
        float shift = profile.k.f / 2f;
        if (shift <= 0 || shift > profile.e) return null;
        int saved = canvas.save(); canvas.translate(0f, shift);
        return saved;
    }
    private static Bitmap cached(String key, Bitmap source) {
        Cached saved = cache.get(key); return saved != null && saved.source == source && !saved.image.isRecycled() ? saved.image : null;
    }
    private static Bitmap remember(String key, Bitmap source, Bitmap image) {
        int size = image.getByteCount(); if (size > CACHE_BYTES) return image;
        Cached old = cache.remove(key); if (old != null) cacheBytes -= old.image.getByteCount();
        while (!cache.isEmpty() && (cacheBytes + size > CACHE_BYTES || cache.size() >= 128)) {
            String oldest = cache.keySet().iterator().next(); cacheBytes -= cache.remove(oldest).image.getByteCount();
        }
        cache.put(key, new Cached(source, image)); cacheBytes += size; return image;
    }
    public static synchronized Bitmap icon(E1.a app, Bitmap original) {
        if (!enabled() || app == null || !IconPack.app(app.a) || original == null || original.isRecycled()) return original;
        refresh(false);
        if (pack == null && corners < 0) return original;
        int width = original.getWidth(), height = original.getHeight();
        if (width < 1 || height < 1 || width > 1024 || height > 1024) return original;
        String key = "icon/" + app.a; Bitmap saved = cached(key, original); if (saved != null) return saved;
        Bitmap replacement = null;
        try {
            byte[] bytes = pack == null ? null : pack.icon(app.a);
            if (bytes != null) {
                BitmapFactory.Options bounds = new BitmapFactory.Options(); bounds.inJustDecodeBounds = true;
                BitmapFactory.decodeByteArray(bytes, 0, bytes.length, bounds);
                if (bounds.outWidth == bounds.outHeight && bounds.outWidth >= 16 && bounds.outWidth <= 1024) {
                    BitmapFactory.Options options = new BitmapFactory.Options(); options.inPreferredConfig = Bitmap.Config.ARGB_8888;
                    replacement = BitmapFactory.decodeByteArray(bytes, 0, bytes.length, options);
                }
            }
            if (replacement == null && corners < 0) return original;
            Bitmap result = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(result); int checkpoint = canvas.save();
            try {
                if (corners >= 0) {
                    Path clip = new Path(); float radius = (float)corners * Math.min(width, height);
                    clip.addRoundRect(new RectF(0, 0, width, height), radius, radius, Path.Direction.CW); canvas.clipPath(clip);
                }
                Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
                canvas.drawBitmap(replacement == null ? original : replacement, null, new Rect(0, 0, width, height), paint);
            } finally { canvas.restoreToCount(checkpoint); }
            return remember(key, original, result);
        } catch (RuntimeException failure) { return original; }
        finally { if (replacement != null) replacement.recycle(); }
    }
    private static Bitmap tint(Bitmap source, String hex) {
        if (source == null || source.isRecycled() || source.getWidth() > 512 || source.getHeight() > 512) return source;
        String key = "badge/" + hex + "/" + System.identityHashCode(source); Bitmap saved = cached(key, source); if (saved != null) return saved;
        Bitmap result = source.copy(Bitmap.Config.ARGB_8888, true); if (result == null) return source;
        int[] pixels = new int[result.getWidth() * result.getHeight()]; source.getPixels(pixels, 0, result.getWidth(), 0, 0, result.getWidth(), result.getHeight());
        int rgb = Integer.parseInt(hex.substring(1), 16);
        for (int i = 0; i < pixels.length; i++) {
            int p = pixels[i], r = p >> 16 & 255, g = p >> 8 & 255, b = p & 255;
            // Keep white exclamation glyphs/highlights, text and transparent margins unchanged.
            if ((p >>> 24) == 0 || r <= g + 12 || r <= b + 12) continue;
            int low = Math.min(g, b), amount = r - low;
            int nr = Math.min(255, low + (rgb >> 16 & 255) * amount / 255);
            int ng = Math.min(255, low + (rgb >> 8 & 255) * amount / 255);
            int nb = Math.min(255, low + (rgb & 255) * amount / 255);
            pixels[i] = (p & 0xff000000) | nr << 16 | ng << 8 | nb;
        }
        result.setPixels(pixels, 0, result.getWidth(), 0, 0, result.getWidth(), result.getHeight());
        return remember(key, source, result);
    }
    public static synchronized Map artwork(final Map original) {
        if (!enabled() || original == null) return original;
        refresh(false); if (badge.equals("stock")) return original;
        return new AbstractMap<Object, Object>() {
            public Object get(Object key) {
                Object value = original.get(key);
                if (("ios4/chrome/badge_bg.png".equals(key) || "ios4/chrome/badge_exclamation.png".equals(key)) && value instanceof Bitmap) {
                    synchronized (SnowyHome.class) {
                        // A renderer may retain this read-only view across a Safe Mode/marker change.
                        if (!enabled()) return value;
                        refresh(false); if (badge.equals("stock")) return value;
                        try { return tint((Bitmap)value, badge); } catch (RuntimeException failure) { return value; }
                    }
                }
                return value;
            }
            public boolean containsKey(Object key) { return original.containsKey(key); }
            public Set<Entry<Object, Object>> entrySet() {
                return new java.util.AbstractSet<Entry<Object, Object>>() {
                    public int size() { return original.size(); }
                    public java.util.Iterator<Entry<Object, Object>> iterator() {
                        final java.util.Iterator<?> keys = original.keySet().iterator();
                        return new java.util.Iterator<Entry<Object, Object>>() {
                            public boolean hasNext() { return keys.hasNext(); }
                            public Entry<Object, Object> next() { Object key = keys.next(); return new SimpleImmutableEntry<>(key, get(key)); }
                            public void remove() { throw new UnsupportedOperationException("Read-only artwork view"); }
                        };
                    }
                };
            }
        };
    }
    static synchronized JSONObject preferences() {
        refresh(true); JSONObject value = new JSONObject();
        try { value.put("pack", selected); value.put("badge", badge); value.put("corners", corners); value.put("hideLabels", hideLabels); }
        catch (Exception impossible) { throw new IllegalStateException(impossible); }
        return value;
    }
    static synchronized boolean select(String key, Object value) {
        if (!enabled()) return false;
        File dir = folder(), temp = null; if (dir == null) return false;
        try {
            JSONObject preferences = preferences(); preferences.put(key, value);
            if (!dir.isDirectory() && !dir.mkdirs()) return false;
            File target = new File(dir, "preferences.json"); if (Files.isSymbolicLink(target.toPath())) return false;
            temp = File.createTempFile(".snowy-", ".tmp", dir);
            try (FileOutputStream out = new FileOutputStream(temp)) { out.write(preferences.toString().getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
            try { Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE); }
            catch (java.nio.file.AtomicMoveNotSupportedException failure) { Files.move(temp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING); }
            refresh(true); return true;
        } catch (Exception failure) { android.util.Log.e("WinterXSnowy", "Preference unchanged", failure); return false; }
        finally { if (temp != null) temp.delete(); }
    }
}
