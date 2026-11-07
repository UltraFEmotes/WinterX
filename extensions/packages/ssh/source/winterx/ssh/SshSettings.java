package winterx.ssh;

import E1.T6;
import E1.V6;
import E1.W6;
import E1.Z3;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Visible native controls only when the optional engine and unlisted SSH hook are present. */
public final class SshSettings {
    private static final String PAGE = "winterx-layout-p/ssh", ACTION = "winterx-layout-a/ssh/";
    private SshSettings() {}
    private static V6 row(String id, String title) { return Z3.g(Z3.a, id, title, null, null, null, 0x18); }
    public static void rows(List<V6> rows) { if (SshService.installed()) rows.add(row(PAGE, "SSH")); }
    public static T6 page(String id) {
        if (!PAGE.equals(id) || !SshService.installed()) return null;
        List<V6> rows = new ArrayList<>();
        rows.add(row(ACTION + "start", "Start SSH for This Session")); rows.add(row(ACTION + "stop", "Stop SSH"));
        rows.add(row(ACTION + "import-keys", "Import authorized_keys…"));
        String footer = (KeyImport.note != null ? KeyImport.note + "\n" : "") + SshService.status()
            + "\nPublic-key authentication only. Import a public key file above (or copy it into ruby/ssh/authorized_keys). "
            + "SFTP and Android shell exec run as Spring's UID, not root; an authorized key can change Spring data. "
            + "Loopback only; remote access needs an explicitly configured external tunnel. No passwords or forwarding. Safe Mode/removal/key changes stop this service.";
        if (SshActions.available()) footer += "\nBuilt-ins: neofetch and winterx-app --help. App actions target .sapp apps only; uploads go in ruby/ssh/inbox and require their SHA-256 plus --confirm.";
        if (SshService.promptAvailable()) footer += "\nInteractive terminal: connect with SSH without a command, then type help at winterx>. Ctrl-C cancels pending work; exit disconnects.";
        else footer += "\nThis engine supports one-shot commands only; no interactive prompt.";
        return new T6(id, "SSH", Collections.singletonList(new W6("EXPERIMENTAL PRIVATE ACCESS", null, footer, null, rows)));
    }
    public static void action(String id) {
        if ((ACTION + "start").equals(id)) SshService.request(true);
        else if ((ACTION + "stop").equals(id)) SshService.request(false);
        else if ((ACTION + "import-keys").equals(id)) KeyImport.open();
    }
}
