package winterx.ssh;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.PublicKey;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.apache.sshd.common.config.keys.AuthorizedKeyEntry;
import org.apache.sshd.common.config.keys.KeyUtils;
import org.apache.sshd.common.config.keys.PublicKeyEntryResolver;
import org.apache.sshd.common.file.virtualfs.VirtualFileSystemFactory;
import org.apache.sshd.common.io.nio2.Nio2ServiceFactoryFactory;
import org.apache.sshd.core.CoreModuleProperties;
import org.apache.sshd.server.SshServer;
import org.apache.sshd.server.auth.pubkey.UserAuthPublicKeyFactory;
import org.apache.sshd.server.command.Command;
import org.apache.sshd.server.forward.RejectAllForwardingFilter;
import org.apache.sshd.server.keyprovider.SimpleGeneratorHostKeyProvider;
import org.apache.sshd.server.shell.ProcessShellFactory;
import org.apache.sshd.sftp.server.SftpSubsystemFactory;

/** Actual optional SSH/SFTP engine. Disabled by default; no bind in configure(). Runs as Spring's UID, never su/root. */
public final class SshServerEngine {
    public static final String ABI = "winterx-sshd-auth-v1";
    public static final String INFO_ABI = "winterx-ssh-info-v1";
    public static final String APP_ABI = "winterx-ssh-app-v1";
    public static final String SHELL_ABI = "winterx-ssh-prompt-v1";
    private final SshServer server;
    public final String fingerprint;
    private SshServerEngine(SshServer server, String fingerprint) { this.server = server; this.fingerprint = fingerprint; }
    private static Path safe(Path path) throws IOException {
        Path absolute = path.toAbsolutePath().normalize();
        for (Path part = absolute; part != null; part = part.getParent()) if (Files.isSymbolicLink(part)) throw new IOException("SSH storage links refused");
        return absolute;
    }
    public static List<PublicKey> authorized(Path path) throws Exception {
        safe(path);
        if (!Files.isRegularFile(path) || Files.size(path) > 16384) throw new IOException("Supply a private authorized_keys file (max 16 KiB)");
        List<PublicKey> result = new ArrayList<>();
        for (String line : new String(Files.readAllBytes(path), StandardCharsets.UTF_8).split("\\r?\\n")) {
            line = line.trim(); if (line.isEmpty() || line.startsWith("#")) continue;
            // Options such as command=, from= and certificates are intentionally unsupported, not silently ignored.
            if (!line.startsWith("ssh-ed25519 ") && !line.startsWith("ssh-rsa ") && !line.startsWith("ecdsa-sha2-nistp256 "))
                throw new IOException("Use plain RSA, Ed25519 or P-256 public keys without options");
            AuthorizedKeyEntry entry = AuthorizedKeyEntry.parseAuthorizedKeyEntry(line);
            PublicKey key = entry.resolvePublicKey(null, PublicKeyEntryResolver.FAILING);
            if (KeyUtils.getKeySize(key) < ("RSA".equals(key.getAlgorithm()) ? 3072 : 256)) throw new IOException("SSH key too small");
            result.add(key); if (result.size() > 8) throw new IOException("At most eight authorized keys");
        }
        if (result.isEmpty()) throw new IOException("No authorized public keys");
        return Collections.unmodifiableList(result);
    }
    public static SshServerEngine configure(Path files, Path keys, Path hostKey, int port, boolean confirmed) throws Exception {
        if (!confirmed) throw new IOException("SSH requires an explicit Start action each session");
        files = safe(files); keys = safe(keys); hostKey = safe(hostKey);
        if (!Files.isDirectory(files) || !hostKey.startsWith(files) || !keys.startsWith(files) || port < 1024 || port > 65535)
            throw new IOException("Invalid private SSH paths or unprivileged port");
        final List<PublicKey> allowed = authorized(keys);
        SimpleGeneratorHostKeyProvider provider = new SimpleGeneratorHostKeyProvider(hostKey);
        provider.setAlgorithm("RSA"); provider.setKeySize(3072); provider.setOverwriteAllowed(false);
        KeyPair pair = provider.loadKeys(null).iterator().next();
        if (!Files.isRegularFile(hostKey)) throw new IOException("Host key was not persisted");
        try { Files.setPosixFilePermissions(hostKey, java.nio.file.attribute.PosixFilePermissions.fromString("rw-------")); }
        catch (UnsupportedOperationException failure) { throw new IOException("Private host-key permissions unavailable", failure); }
        SshServer ssh = SshServer.setUpDefaultServer(); ssh.setHost("127.0.0.1"); ssh.setPort(port);
        ssh.setIoServiceFactoryFactory(new Nio2ServiceFactoryFactory());
        ssh.setKeyPairProvider(provider);
        ssh.setUserAuthFactories(Collections.singletonList(UserAuthPublicKeyFactory.INSTANCE));
        ssh.setPasswordAuthenticator((username, password, session) -> false);
        ssh.setKeyboardInteractiveAuthenticator(null);
        ssh.setPublickeyAuthenticator((username, key, session) -> "winterx".equals(username) && allowed.stream().anyMatch(value -> KeyUtils.compareKeys(value, key)));
        ssh.setForwardingFilter(RejectAllForwardingFilter.INSTANCE);
        ssh.setShellFactory(channel -> new BuiltinShell());
        ssh.setCommandFactory((channel, command) -> {
            if (command == null || command.length() > 8192) throw new IOException("SSH command too long");
            Command info = FetchCommand.create(command);
            if (info != null) return info; // Works on Mac.APK too, without /system/bin/sh.
            Command action = AppCommand.create(command);
            if (action != null) return action; // Malformed reserved commands never fall through to a shell.
            if (!Files.isExecutable(java.nio.file.Paths.get("/system/bin/sh"))) throw new IOException("Android shell unavailable");
            return new ProcessShellFactory("/system/bin/sh", "/system/bin/sh", "-c", command).createShell(channel);
        });
        ssh.setFileSystemFactory(new VirtualFileSystemFactory(files));
        ssh.setSubsystemFactories(Collections.singletonList(new SftpSubsystemFactory.Builder().build()));
        CoreModuleProperties.AUTH_TIMEOUT.set(ssh, Duration.ofSeconds(20));
        CoreModuleProperties.IDLE_TIMEOUT.set(ssh, Duration.ofMinutes(3));
        CoreModuleProperties.MAX_AUTH_REQUESTS.set(ssh, 5);
        CoreModuleProperties.MAX_CONCURRENT_SESSIONS.set(ssh, 2);
        CoreModuleProperties.MAX_CONCURRENT_CHANNELS.set(ssh, 4);
        CoreModuleProperties.NIO_WORKERS.set(ssh, 2);
        CoreModuleProperties.STOP_WAIT_TIME.set(ssh, Duration.ofSeconds(5));
        return new SshServerEngine(ssh, KeyUtils.getFingerPrint(pair.getPublic()));
    }
    public void start() throws Exception { try { server.start(); } catch (Exception failure) { server.close(true); throw failure; } }
    public void stop() throws Exception { server.stop(true); }
    public boolean running() { return server.isStarted(); }
    // Exposes configuration to no-listener regression checks, not the tweak JavaScript API.
    SshServer configuration() { return server; }
}
