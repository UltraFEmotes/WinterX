package J1;
import java.io.File;
/** Native code/data destinations, all under the disposable fixture root. */
public final class P {
    public final File a, b;
    public P(File files) { a = new File(files, "sapps"); b = new File(files, "sapps-data"); }
}
