package winterx.ssh;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.util.Collections;
import org.apache.sshd.common.config.keys.PublicKeyEntry;
import org.apache.sshd.server.forward.RejectAllForwardingFilter;

/** Configuration/authentication only. Does not start a listener or shell. */
public final class SshEngineCheck {
    static void check(boolean ok, String why) { if (!ok) throw new AssertionError(why); }
    public static void main(String[] args) throws Exception {
        Path files = java.nio.file.Paths.get(args[0]).toRealPath(), keys = files.resolve("authorized_keys"), host = files.resolve("host-key.ser");
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA"); generator.initialize(3072);
        KeyPair allowed = generator.generateKeyPair(), wrong = generator.generateKeyPair();
        Files.write(keys, Collections.singletonList(PublicKeyEntry.toString(allowed.getPublic())));
        try { SshServerEngine.configure(files, keys, host, 2222, false); throw new AssertionError("unconfirmed server configured"); }
        catch (java.io.IOException expected) {}
        check(!Files.exists(host), "unconfirmed request generated host key");
        SshServerEngine engine = SshServerEngine.configure(files, keys, host, 2222, true);
        org.apache.sshd.server.SshServer server = engine.configuration();
        check(!engine.running() && server.getBoundAddresses().isEmpty(), "configuration opened a listener");
        check(server.getHost().equals("127.0.0.1") && server.getPort() == 2222, "unsafe bind default");
        check(server.getUserAuthFactories().size() == 1 && server.getUserAuthFactories().get(0).getName().equals("publickey"), "password auth enabled");
        check(server.getPublickeyAuthenticator().authenticate("winterx", allowed.getPublic(), null), "authorized key rejected");
        check(!server.getPublickeyAuthenticator().authenticate("root", allowed.getPublic(), null), "root login accepted");
        check(!server.getPublickeyAuthenticator().authenticate("winterx", wrong.getPublic(), null), "wrong key accepted");
        check(server.getForwardingFilter() == RejectAllForwardingFilter.INSTANCE, "forwarding enabled");
        check(SshServerEngine.SHELL_ABI.equals("winterx-ssh-prompt-v1") && server.getShellFactory().createShell(null) instanceof BuiltinShell,
            "interactive shell is not the in-process WinterX prompt");
        check(SshServerEngine.INFO_ABI.equals("winterx-ssh-info-v1"), "built-in info capability missing");
        check(FetchCheck.run(server.getCommandFactory().createCommand(null, "neofetch --no-color"), 0).contains("WinterX"),
            "real command factory did not route the built-in before Android shell fallback");
        check(FetchCheck.run(server.getCommandFactory().createCommand(null, "winterx-info --help"), 0).contains("Usage:"), "factory alias/help missing");
        FetchCheck.run(server.getCommandFactory().createCommand(null, "neofetch --unknown"), 2);
        check(SshServerEngine.APP_ABI.equals("winterx-ssh-app-v1"), "guarded app-command capability missing");
        check(FetchCheck.run(server.getCommandFactory().createCommand(null, "winterx-app --help"), 0).contains("Spring-app"), "real command factory did not route app help before shell fallback");
        FetchCheck.run(server.getCommandFactory().createCommand(null, "winterx-app; unwanted-shell"), 2);
        check(!engine.running() && server.getBoundAddresses().isEmpty(), "built-in report started a listener");
        byte[] saved = Files.readAllBytes(host);
        SshServerEngine second = SshServerEngine.configure(files, keys, host, 2222, true);
        check(second.fingerprint.equals(engine.fingerprint) && java.util.Arrays.equals(saved, Files.readAllBytes(host)), "host key rotated");
        Files.write(keys, Collections.singletonList("command=evil " + PublicKeyEntry.toString(allowed.getPublic())));
        try { SshServerEngine.authorized(keys); throw new AssertionError("key options ignored"); } catch (java.io.IOException expected) {}
        server.close(true); second.configuration().close(true);
        System.out.println("SSH no-listener check: explicit start gate, pinned host identity, key-only auth, wrong-key/root rejection, loopback/no-forwarding, interactive built-in factory and one-shot dispatch passed");
    }
}
