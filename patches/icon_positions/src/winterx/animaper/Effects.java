package winterx.animaper;

/** Stateless icon offsets, in pixels, while a home-screen page is moving. */
public final class Effects {
    private Effects() {}
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
            default: return new int[]{0, 0};
        }
        return new int[]{(int)Math.round(x), (int)Math.round(y)};
    }
}
