package winterx.animaper;

/** Stateless icon offsets, in pixels, while a home-screen page is moving. */
public final class Effects {
    private Effects() {}
    /** Local tangent/depth projection of a rotating vertical cylinder. */
    public static final class Barrel {
        public final float shiftX, scaleX, scaleY;
        private Barrel(float shiftX, float scaleX, float scaleY) {
            this.shiftX = shiftX; this.scaleX = scaleX; this.scaleY = scaleY;
        }
    }
    private static final Barrel IDENTITY = new Barrel(0f, 1f, 1f);
    public static Barrel barrel(float progress, float center, int width) {
        if (width <= 0 || !Float.isFinite(progress) || !Float.isFinite(center) ||
            center < 0 || center > width || Math.abs(progress) >= 1f || progress == 0f) return IDENTITY;
        double amount = Math.sin(Math.PI * Math.abs(progress));
        double radius = width * .65, distance = width * 2.8;
        double angle = Math.asin((center - width * .5) / radius) + progress * Math.PI * .75;
        double depth = radius * (Math.cos(angle) - 1), perspective = distance / (distance - depth);
        double projected = width * .5 + radius * Math.sin(angle) * perspective;
        return new Barrel((float)((projected - center - progress * width) * amount),
            (float)(1 + amount * (Math.max(.14, Math.cos(angle)) * perspective - 1)),
            (float)(1 + amount * (perspective - 1)));
    }
    public static int[] offset(String mode, float progress, int row, int column, int width, int icon) {
        if (mode == null || width <= 0 || icon <= 0 || !Float.isFinite(progress)) return new int[]{0, 0};
        float p = Math.max(-1f, Math.min(1f, progress));
        double wave = Math.sin(Math.PI * Math.abs(p));
        if (wave < .00001) return new int[]{0, 0};
        double sign = p < 0 ? -1 : 1, x = 0, y = 0;
        switch (mode) {
            case "wave": y = Math.sin(column * .9 + p * Math.PI) * icon * .65 * wave; break;
            case "cascade": y = (row - 2) * icon * .22 * wave; break;
            case "bounce": y = -Math.abs(Math.sin((row + 1) * 1.2 + p * Math.PI)) * icon * .7 * wave; break;
            case "orbit": x = Math.cos(row * .9 + column * .5) * icon * .35 * wave * sign;
                          y = Math.sin(row * .9 + column * .5) * icon * .55 * wave; break;
            case "ripple": y = Math.cos(Math.hypot(column - 1.5, row - 2) * 1.4 - p * Math.PI) * icon * .6 * wave; break;
            case "columns": y = ((column % 2 == 0) ? -1 : 1) * icon * .6 * wave; break;
            case "fan": x = (column - 1.5) * icon * .2 * wave;
                        y = (row - 2) * icon * .25 * wave; break;
            case "zigzag": x = ((row % 2 == 0) ? -1 : 1) * icon * .4 * wave * sign; break;
            // Positional component for standalone math clients. The native adapter
            // uses actual sparse-grid centers and applies foreshortening on Canvas.
            case "barrel": x = barrel(p, (column + .5f) * width / 4f, width).shiftX; break;
            default: return new int[]{0, 0};
        }
        return new int[]{(int)Math.round(x), (int)Math.round(y)};
    }
}
