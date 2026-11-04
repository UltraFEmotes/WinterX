package android.app;
import java.io.File;
public class Activity { public File inbox, files; public boolean destroyed; public boolean recreated; public File getFilesDir(){return files;} public void recreate(){recreated=true;destroyed=true;} public boolean isFinishing(){return destroyed;} public boolean isDestroyed(){return destroyed;} public File getExternalFilesDir(String name){return inbox;} }
