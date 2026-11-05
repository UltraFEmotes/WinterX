package H1;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipFile;
import org.json.JSONObject;
/** Metadata-only boundary fixture. Native parser/installer bytecode is checked separately. */
public final class Q {
    public static boolean mismatch;
    public static m0 h(File archive) throws Exception {
        try (ZipFile zip = new ZipFile(archive)) {
            String json = new String(zip.getInputStream(zip.getEntry("app.json")).readAllBytes(), StandardCharsets.UTF_8);
            return new m0(mismatch ? "me.example.wrong" : new JSONObject(json).getString("id"));
        }
    }
}
