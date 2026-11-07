package winterx.packages;

import winterx.extension.NativeTweak;
import winterx.ssh.SshService;
import winterx.ssh.SshSettings;

/** Installing this code never starts the listener. Native Settings owns explicit Start/Stop. */
public final class SshEntry implements NativeTweak {
    @Override public void start(winterx.extension.TweakContext context) { winterx.ssh.KeyImport.install(context); }
    public Object call(String point, Object[] arguments) {
        switch (point) {
            case "settings.page": return SshSettings.page((String)arguments[0]);
            case "settings.action": SshSettings.action((String)arguments[0]); return null;
            default: return null;
        }
    }
    @Override public void stop() { SshService.request(false); }
}
