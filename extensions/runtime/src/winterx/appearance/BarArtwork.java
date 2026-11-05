package winterx.appearance;

import android.graphics.Bitmap;
import android.util.Log;
import java.util.AbstractMap;
import java.util.AbstractSet;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/** Immutable, per-render bar artwork. Never mutates Spring's shared maps or bitmaps. */
public final class BarArtwork {
    private static final WeakHashMap<Bitmap, Tint> TINTS = new WeakHashMap<>();

    private BarArtwork() {}

    private static String basename(String name) {
        if (name == null || name.contains("..") || name.contains("\\") || !name.endsWith(".png")) return null;
        if (name.startsWith("ios4/uikit/") || name.startsWith("ios6/uikit/")) name = name.substring(11);
        return name.contains("/") ? null : name;
    }

    public static boolean navigationAsset(String name) {
        if ("ios6/apps/appstore/NavBar.png".equals(name)) return true;
        String base = basename(name);
        return base != null && base.startsWith("UINavigationBar") && !base.contains("Shadow");
    }

    private static boolean rubyAsset(String name) {
        String base = basename(name);
        return navigationAsset(name) || (base != null &&
            (base.equals("UIButtonBarBlackOpaqueBackgroundTall.png") || base.equals("UIButtonBarSelectedIndicator.png")));
    }

    public static Map view(Map original, String hex, boolean ruby) {
        if (original == null) return null;
        if (original instanceof Artwork) original = ((Artwork) original).original;
        return new Artwork(original, hex, ruby);
    }

    /** Also used by Settings' lazy loader, after stock cache lookup. */
    public static Object asset(Object key, Object value, String hex, boolean ruby) {
        return key instanceof String && (ruby ? rubyAsset((String) key) : navigationAsset((String) key)) && value instanceof Bitmap
            ? tinted((Bitmap) value, hex) : value;
    }

    private static final class Tint {
        final String hex;
        final Bitmap bitmap;
        Tint(String hex, Bitmap bitmap) { this.hex = hex; this.bitmap = bitmap; }
    }

    private static synchronized Bitmap tinted(Bitmap source, String hex) {
        Tint cached = TINTS.get(source);
        if (cached != null && cached.hex.equals(hex) && !cached.bitmap.isRecycled()) return cached.bitmap;
        try {
            int width = source.getWidth(), height = source.getHeight();
            if (source.isRecycled() || width <= 0 || height <= 0 || (long) width * height > 1024 * 1024) return source;
            int[] pixels = new int[width * height];
            source.getPixels(pixels, 0, width, 0, 0, width, height);
            int rgb = Integer.parseInt(hex, 16);
            for (int i = 0; i < pixels.length; i++) pixels[i] = tintPixel(pixels[i], rgb);
            Bitmap out = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            out.setPixels(pixels, 0, width, 0, 0, width, height);
            // An in-flight frame may still use an evicted image. Do not recycle it.
            TINTS.put(source, new Tint(hex, out));
            return out;
        } catch (Throwable failure) {
            Log.w("WinterX", "Bar artwork unavailable", failure);
            return source;
        }
    }

    public static int tintPixel(int pixel, int rgb) {
        int alpha = pixel >>> 24;
        if (alpha == 0) return pixel;
        int grey = Math.min(Math.max((pixel >> 16) & 255, Math.max((pixel >> 8) & 255, pixel & 255)), 215);
        float shade = (grey + 40) / 255f;
        int red = Math.round(((rgb >> 16) & 255) * shade);
        int green = Math.round(((rgb >> 8) & 255) * shade);
        int blue = Math.round((rgb & 255) * shade);
        return (alpha << 24) | (red << 16) | (green << 8) | blue;
    }

    private static final class Artwork extends AbstractMap<Object, Object> {
        final Map original;
        final String hex;
        final boolean ruby;
        Artwork(Map original, String hex, boolean ruby) { this.original = original; this.hex = hex; this.ruby = ruby; }
        public Object get(Object key) {
            return asset(key, original.get(key), hex, ruby);
        }
        public boolean containsKey(Object key) { return original.containsKey(key); }
        public int size() { return original.size(); }
        public Set<Map.Entry<Object, Object>> entrySet() {
            return new AbstractSet<Map.Entry<Object, Object>>() {
                public int size() { return original.size(); }
                public Iterator<Map.Entry<Object, Object>> iterator() {
                    final Iterator keys = original.keySet().iterator();
                    return new Iterator<Map.Entry<Object, Object>>() {
                        public boolean hasNext() { return keys.hasNext(); }
                        public Map.Entry<Object, Object> next() {
                            Object key = keys.next();
                            return new SimpleImmutableEntry<>(key, get(key));
                        }
                        public void remove() { throw new UnsupportedOperationException("Read-only artwork"); }
                    };
                }
            };
        }
    }
}
