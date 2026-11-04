package android.content.res;
public class AssetManager {
    public java.io.InputStream open(String path) { return new java.io.ByteArrayInputStream(("original:" + path).getBytes(java.nio.charset.StandardCharsets.UTF_8)); }
}
