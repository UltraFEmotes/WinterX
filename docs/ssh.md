# SSH — optional, unlisted development tweak

An optional on-device SSH/SFTP engine is implemented in source and the local test. It is **not installed or live-verified on Android**. The host-side SSH transport is a separate feature. The new built-in `neofetch` / `winterx-info` report runs in-process, without installing Neofetch or requiring an Android shell; it needs the separate info-capable engine described below.

## Explicit native controls

On a compatible running engine with the unlisted `com.winterx.ssh` / `tweak.ssh` package, **Spring Settings → WINTERX TWEAKS → SSH** offers **Start SSH for This Session** and **Stop SSH**. Install, boot and Safe Mode exit never start it automatically.

The older reviewed batch2 rejected Mac.APK's legitimate platform-files alias despite an enabled marker. The UI-fix2 correction is now selected and user-launched; it resolves that trusted root while retaining rejection of links in markers, `ruby/`, SSH directories and authorized keys. Neither preparation nor boot starts SSH. Building a newer engine does not change that running selection.

- Binds **127.0.0.1:2222** only; username **winterx**; public-key authentication only. No passwords, root, automatic LAN exposure, forwarding or interactive PTY.
- Plain RSA (3072+ bits), Ed25519 or P-256 public keys in `files/ruby/ssh/authorized_keys`, maximum eight keys / 16 KiB. Options/certificates are refused. Actual Android crypto support still needs verification.
- On explicit Start, persists a private RSA host identity at `files/ruby/ssh/host-key.ser`; native Settings displays its fingerprint. Host keys are not overwritten to resolve an authentication problem.
- SFTP is rooted at Spring's private files. Exec uses `/system/bin/sh -c` as **Spring's UID**, not `su`. Authorized keys can change Spring's accessible data; this is powerful app-level access, **not a sandbox for untrusted users**.
- Stop cancels in-flight Start and closes owned resources. Safe Mode, removal or changed authorized keys stop/refuse activation; another explicit Start is required.

Remote access would require an external tunnel configured deliberately by the user. No tunnel/network/root setup is performed by these tools. Private-folder access does not provide Spring's Android signing key; never uninstall/reinstall Spring to bypass signing.

## First connection on the local Mac.APK test

Create a dedicated client key in Terminal, choosing a passphrase and refusing to overwrite an existing key:

```sh
mkdir -p "$HOME/.ssh"
ssh-keygen -t rsa -b 3072 -f "$HOME/.ssh/winterx_local" -C "WinterX local"
```

Then add **only the public `.pub` file**, once, without replacing other authorized keys:

```sh
SSH_DIR="$HOME/Library/Application Support/MacApk/com.guille.spring/data/data/com.guille.spring_0.8.1/files/ruby/ssh"
mkdir -p "$SSH_DIR"
cat "$HOME/.ssh/winterx_local.pub" >> "$SSH_DIR/authorized_keys"
chmod 700 "$SSH_DIR"
chmod 600 "$SSH_DIR/authorized_keys"
```

In Spring, tap **Settings → WINTERX TWEAKS → SSH → Start SSH for This Session**. Start does not open a terminal or show a popup. Its status footer currently needs a **back/reopen** to show the worker's result. Connect only after it says **Listening on 127.0.0.1:2222**, and compare the first connection's fingerprint with that footer before accepting it:

```sh
sftp -P 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1
```

SFTP's `/` is Spring's private `files/` directory. `pwd`, `ls`, `cd ruby` and `bye` are useful initial commands. A missing identity-file warning means key generation has not completed; connection refused means no listener is accepting that port. If Start reports **Not started**, diagnose that exact error instead of retrying login or replacing the host identity. Changing authorized keys stops the service and requires another explicit Start.

**No interactive SSH terminal is implemented.** General one-shot exec requires `/system/bin/sh`; that path is not executable on the current Mac host. This is a Mac.APK implementation gap, not a missing client command. The built-in info command below deliberately bypasses that shell requirement.

## WinterX Neofetch-style report — new, separate engine

After explicitly upgrading to an info-capable engine, configuring your public key and starting SSH:

```sh
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 neofetch
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 'winterx-info --no-color'
```

Both names are built-in SSH exec requests. `--help` shows usage; unsupported arguments return exit status 2 rather than running a shell. The default report has a red WinterX/WX logo and fits an 80-column terminal. `--no-color` removes ANSI styling for logs and copying.

The report shows the development info ABI, runtime, Spring's actual package version, **reported** device manufacturer/model, Android release/API and display metrics, plus host OS/architecture, runtime CPU count, Java heap, device uptime and the local SSH endpoint. Mac.APK's reported Android/device values are kept separate from the host OS; Spring's iOS-style interface is not advertised as a real iPhone or iOS installation. Missing metadata is shown as unavailable, not invented. Runtime CPU/heap figures are not physical phone specifications.

Collection reads fixed platform metadata and runtime counters only. It does not read private files, keys, contacts, messages, serials, Android IDs, MAC addresses or hostnames, and opens no sockets or processes. Values and row counts are bounded; terminal control/bidirectional characters are filtered. Authentication, loopback binding, no-PTY/no-forwarding policy and Start/Stop guards are unchanged. This is a small WinterX report, not an installation of upstream Neofetch or a general command runner.

The local candidate is `builds/WinterXSpring-0.8.1-tweaks-batch2-neofetch-dev.apk`, SHA-256 `a1de2419994ccfa009e181af2d1ad7471332613de0af1e30c5d6464ca67e0987` (6,983 converted classes). **It is built/tested but not selected or launched.** Only after Spring is fully closed, an authorized upgrade can use `python3 tools/prepare_local_test.py --neofetch`; this makes a fresh backup, preserves existing keys/preferences/layouts and selects the same five pinned hooks without launching Spring or starting SSH. Use `Start WinterX Local Test.command` yourself afterward. The running UI-fix2 engine remains unchanged until that explicit preparation.

## Build without installation

The optional library uses checksum-pinned Apache MINA SSHD **2.20.1** core/common/SFTP and SLF4J **2.0.17**, retaining dependency license notices. The builder downloads dependencies only from Maven Central and refuses unexpected hashes.

```sh
python3 patches/ssh/build.py builds/WinterX-SSH-dev.jar --deps path/to/dependency-cache \
  --javac /opt/homebrew/opt/openjdk/bin/javac
WINTERX_BUILD_ANIMAPER=1 WINTERX_BUILD_TRUSTED_FILES=1 WINTERX_BUILD_INBOX=1 \
  WINTERX_BUILD_SNOWYHOME=1 WINTERX_BUILD_MESSAGEPLUS=1 \
  WINTERX_SSH_LIBRARY="$PWD/builds/WinterX-SSH-dev.jar" \
  python3 patches/icon_positions/build.py Spring-0.8.1.apk builds/WinterXSpring-ssh-dev.apk
python3 tools/springys_tool.py build builtin-repo/sources/ssh builds/SSH-dev.springys
```

All outputs must be new. These commands build only; they do not configure the selected test, install Android updates, create user keys or launch Spring. The bridge gate requires ABI `winterx-sshd-auth-v1`, the real server dependency and native Settings helpers in a checksum-verified **running** engine. New info-capable libraries also declare `winterx-ssh-info-v1`; the older UI-fix2 engine does not contain the new report.

## Verification boundaries

`patches/ssh/check.py` takes the **new info-capable library or converted engine**. It checks actual configuration, host identity persistence and authentication without starting the server; keys live only in disposable fixtures. It also drives the real command factory and built-in command lifecycle using in-memory streams, fixed Android metadata objects and no SSH connection or shell. Info checks cover branding, aliases/help/plain output, honest metadata labels, missing values, bounded/control-safe output, privacy, exits, cancellation and output/provider failures. They are not live device-report verification.

`patches/tests/check_ssh_service.py converted-engine.jar --packaged` checks both iOS 4/6 root rows, direct/aliased platform roots, child-link refusal, serialized Start/Stop before state changes, pre-worker/busy cancellation, resource ownership, failed Start and Safe Mode/removal/key-change stopping using an **engine spy with no sockets or shell**. The reviewed build passes the locking/direct-root tests but fails the newer alias regression; UI-fix2 passes both roots. The original unsynchronized batch also fails the stronger lock test as a negative control.

NIO/JCE/host-key permission compatibility on Android, authenticated connection, SFTP, live built-in output, general exec, automatic status refresh and signing-compatible deployment remain unverified. SSH is enabled in the user-authorized corrected local test, not automatically started or installed on Android. The newer info-capable engine requires an explicit stopped-session upgrade; building it alone does not activate the command. SSH stays outside working catalogues.
