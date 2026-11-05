package winterx.appearance;

import java.util.Map;

/** Ruby's own red iOS-style bars, independent of any installed tweak or Safe Mode. */
public final class RubyAppearance {
    public static final String RED = "C9253D";

    private RubyAppearance() {}

    public static boolean isRuby(String appId) {
        return "sapp:com.ruby.manager".equals(appId) || "com.ruby.manager".equals(appId);
    }

    public static Map assets(Map original, String appId) {
        return isRuby(appId) ? BarArtwork.view(original, RED, true) : original;
    }
}
