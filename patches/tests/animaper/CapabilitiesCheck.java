import java.io.File;
import java.nio.file.Files;
import java.util.Arrays;
import org.json.JSONObject;
import winterx.animaper.Animaper;
import winterx.animaper.AnimaperSettings;
import winterx.runtime.Capabilities;
import winterx.ssh.SshActions;

/** Runtime capability receipts reflect real native hooks, never preference/install side effects. */
public final class CapabilitiesCheck {
    static void check(boolean ok, String why) { if (!ok) throw new AssertionError(why); }
    public static void main(String[] args) throws Exception {
        boolean barrel = Boolean.parseBoolean(args[0]), actions = Boolean.parseBoolean(args[1]);
        File root = new File(System.getProperty("ruby.test.dir")), ruby = new File(root, "ruby"); ruby.mkdirs();
        File mode = new File(ruby, "animaper.mode"), enabled = new File(ruby, "animaper.enabled");
        Files.writeString(mode.toPath(), "orbit\n"); Files.writeString(enabled.toPath(), "1"); byte[] original = Files.readAllBytes(mode.toPath());
        check(Animaper.barrelSupported() == barrel, "Barrel helper was mistaken for native drawing hooks");
        check(SshActions.available() == actions, "SSH helper/library was mistaken for native action hooks");
        E1.T6 page = AnimaperSettings.page(AnimaperSettings.PAGE);
        check(((E1.W6)page.c.get(0)).c.size() == (barrel ? 9 : 8), "unsupported native effect is selectable");
        Capabilities.publish(root);
        File receipt = new File(ruby, "capabilities-v1.json"); JSONObject json = new JSONObject(Files.readString(receipt.toPath()));
        check(json.getString("abi").equals(Capabilities.ABI) && json.getBoolean("animaperBarrel") == barrel && json.getBoolean("sshAppActions") == actions, "wrong runtime capability receipt");
        check(Arrays.equals(original, Files.readAllBytes(mode.toPath())) && !new File(ruby, "ssh").exists(), "capability discovery changed modes or configured SSH");
        File destination = new File(ruby, "protected-receipt"); Files.writeString(destination.toPath(), "protected"); Files.delete(receipt.toPath());
        Files.createSymbolicLink(receipt.toPath(), destination.toPath().toAbsolutePath()); Capabilities.publish(root);
        check(Files.isSymbolicLink(receipt.toPath()) && Files.readString(destination.toPath()).equals("protected"), "linked capability receipt followed or replaced");
        System.out.println("Native capability availability/settings/receipt and preference/child-link preservation passed: Barrel=" + barrel + ", actions=" + actions);
    }
}
