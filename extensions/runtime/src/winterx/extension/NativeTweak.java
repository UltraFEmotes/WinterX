package winterx.extension;

/** Public native-code ABI. Implementations live in .springys packages, never the engine APK. */
public interface NativeTweak {
    default void start(TweakContext context) throws Exception {}
    Object call(String point, Object[] arguments) throws Exception;
    default void stop() throws Exception {}
}
