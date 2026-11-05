package winterx.ssh;
/** Session-revision spy. Real ownership/key/root checks run in check_ssh_service.py. */
public final class SshService {
    public static volatile String revision = "fixture-session-a";
    public static String actionRevision() { return revision; }
}
