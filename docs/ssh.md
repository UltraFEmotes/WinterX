# SSH — optional, unlisted development tweak

An optional on-device SSH/SFTP engine is implemented in source and the local test. It is **not installed or live-verified on Android**. The host-side SSH transport is separate. The newest engine adds an interactive **`winterx>` prompt**, a **blue-snowflake Neofetch** report and guarded Spring-app commands, all running in-process.

## Explicit native controls

On a compatible running engine with the unlisted `com.winterx.ssh` / `tweak.ssh` package, **Spring Settings → WINTERX TWEAKS → SSH** offers **Start SSH for This Session** and **Stop SSH**. Install, boot and Safe Mode exit never start it automatically.

The older reviewed batch2 rejected Mac.APK's legitimate platform-files alias despite an enabled marker. UI-fix2 corrected that trusted root while retaining rejection of child links. The newly prepared renderer/Barrel/actions engine retains the correction. Neither preparation nor boot starts SSH. See [development status](development-status.md) for the selected pin; a historical receipt is not a running-engine guarantee.

- Binds **127.0.0.1:2222** only; username **winterx**; public-key authentication only. No passwords, root, automatic LAN exposure or forwarding. The newest interactive prompt handles WinterX built-ins with client-terminal line editing; it creates no native OS shell/PTY process.
- Plain RSA (3072+ bits), Ed25519 or P-256 public keys in `files/ruby/ssh/authorized_keys`, maximum eight keys / 16 KiB. Options/certificates are refused. Actual Android crypto support still needs verification.
- On explicit Start, persists a private RSA host identity at `files/ruby/ssh/host-key.ser`; native Settings displays its fingerprint. Host keys are not overwritten to resolve an authentication problem.
- SFTP is rooted at Spring's private files. Exec uses `/system/bin/sh -c` as **Spring's UID**, not `su`. Authorized keys can change Spring's accessible data; this is powerful app-level access, **not a sandbox for untrusted users**.
- Stop cancels in-flight Start and closes owned resources. Safe Mode, removal or changed authorized keys stop/refuse activation; another explicit Start is required.

Remote access would require an external tunnel configured deliberately by the user. No tunnel/network/root setup is performed by these tools. Private-folder access does not provide Spring's Android signing key; never uninstall/reinstall Spring to bypass signing.

## First connection on the local Mac.APK test

Reuse an existing dedicated key when one is already configured. For a new setup only, create a key in Terminal, choosing a passphrase and refusing to overwrite an existing key:

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

## Interactive WinterX terminal

On the **SSH-terminal/snowflake engine**, connect without supplying a command:

```sh
ssh -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1
```

At **`winterx>`**, type commands directly:

```text
neofetch
winterx-info --no-color
winterx-app list
winterx-app --help
help
exit
```

`winterx-app open`, `close` and confirmed `install` use the same guarded implementation as one-shot SSH commands. Backspace edits the line; Ctrl-U clears it; Ctrl-C cancels pending work; Ctrl-D, `exit` or `logout` disconnects. A native action already committed cannot be rolled back. Input is limited to 512 ASCII characters; commands are not automatically queued behind a running action. Shell metacharacters/unknown commands do not invoke a system shell.

The prompt ABI is `winterx-ssh-prompt-v1`. The new explicit preparation flag is **`--ssh-terminal`**, selecting `builds/WinterXSpring-0.8.1-ssh-terminal-snowflake-dev.apk` (SHA `adbc9df090bed714afb4121df8b9927cd3478ae810e783fe1964d75115f1f664`). Fully quit Spring before any authorized engine change and launch the selected test yourself afterward. All earlier engine pins remain accepted. Older engines offer one-shot commands only; reconnecting to an old running engine cannot add the prompt.

General Android one-shot exec still requires `/system/bin/sh`, which is unavailable on this Mac host. The interactive prompt supports the WinterX built-ins above; SFTP remains a separate subsystem.

## WinterX Neofetch-style report

After explicitly upgrading to an info-capable engine, configuring your public key and starting SSH:

```sh
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 neofetch
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 'winterx-info --no-color'
```

Both names work as built-in one-shot requests and in the new interactive prompt. `--help` shows usage; unsupported arguments return exit status 2. The newest report has a **blue ASCII snowflake**, WinterX heading and an 80-column layout. `--no-color` retains the snowflake while removing ANSI styling. Older saved engine/library pins still contain their historical red WX logo.

The report shows the development info ABI, runtime, Spring's actual package version, **reported** device manufacturer/model, Android release/API and display metrics, plus host OS/architecture, runtime CPU count, Java heap, device uptime and the local SSH endpoint. Mac.APK's reported Android/device values are kept separate from the host OS; Spring's iOS-style interface is not advertised as a real iPhone or iOS installation. Missing metadata is shown as unavailable, not invented. Runtime CPU/heap figures are not physical phone specifications.

Collection reads fixed platform metadata and runtime counters only. It does not read private files, keys, contacts, messages, serials, Android IDs, MAC addresses or hostnames, and opens no sockets or processes. Values and row counts are bounded; terminal control/bidirectional characters are filtered. Authentication, loopback binding, forwarding restrictions and Start/Stop guards are retained. This is a built-in report, not an installation of upstream Neofetch.

Historical pins remain accepted: Neofetch-only `a1de2419994ccfa009e181af2d1ad7471332613de0af1e30c5d6464ca67e0987` (`--neofetch`), and renderer/actions `db1b7d4fd692cc426cab7b9ce9044af8088de6c35b95260fe187981c889c918e` (`--render-actions`). The selected **SSH-terminal/snowflake** follow-up uses `--ssh-terminal` and the pin above. Its fresh 21:00 backup preserved all 485 current entries; preparation never launches Spring or starts SSH. Launch stays under user control through `Start WinterX Local Test.command`.

## Guarded Spring-app commands

The renderer/Barrel/actions development engine adds **`winterx-app`** alongside Neofetch. It runs in-process on Mac.APK as well as in the Android source implementation; it does not require `/system/bin/sh`.

After explicit Settings Start and fingerprint verification:

```sh
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 'winterx-app --help'
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 'winterx-app list'
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 'winterx-app open sapp:me.example.app'
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 'winterx-app close sapp:me.example.app'
```

Use an exact installed `.sapp` ID from `list`. **Open** requires an unlocked, idle Home screen and uses Spring's native launch location/API. **Close** calls native runtime cleanup, not merely Home. A foreground app first completes its native close transition; cancellation, a session change or an unfinished transition prevents the later runtime-destruction step. These commands do not kill/restart Spring, uninstall apps or control arbitrary Android packages.

**Install** accepts one explicitly named new JavaScript `.sapp`, not an APK, URL or arbitrary path. Enable Spring's existing Developer Mode yourself. Through SFTP, create `ruby/ssh/inbox` if needed and upload `Example.sapp` there; this dedicated inbox is not Spring's automatically scanned external `sapps-inbox`. Finish the upload before invoking:

```sh
HASH=$(shasum -a 256 Example.sapp | awk '{print $1}')
ssh -T -p 2222 -i "$HOME/.ssh/winterx_local" -o IdentitiesOnly=yes winterx@127.0.0.1 \
  "winterx-app install Example.sapp --sha256 $HASH --confirm"
```

The command preserves the uploaded source, validates a private bounded snapshot and its explicit SHA-256, then uses the native **single-archive** installer on its existing worker. It does not scan/import other inbox files or open the installed app. Existing IDs, code/build directories and app-data directories are refused, including built-in WinterX apps: this initial command is for **new installs**, because Spring's native update path can replace old builds. Native installation/permission/version checks remain in place. A successful result means the native installer returned successfully; the app-availability refresh may still be queued.

Limits: 512 command characters, exact argument count, bounded IDs/simple filenames, 40 MiB archive, 1,024 entries, 16 MiB per entry, 80 MiB expanded total, 64 KiB manifest and 1,024×1,024 maximum icon PNG. Unsafe/duplicate paths, links, incomplete files, size/CRC/hash mismatches and incompatible metadata are refused. Install names use the native `app.json` ID, not the archive filename.

Each queued/commit step rechecks cancellation, the explicitly started SSH session, authorized-key revision, application root and native session. Stop, Safe Mode, removal or changed keys revoke queued actions immediately. Output is bounded/control-filtered; requests have finite queues/deadlines and no automatic retry. Cancellation cannot roll back an action already committed to Spring's native APIs. On timeout, inspect native state before retrying.

These commands require both `winterx-ssh-app-v1` in the optional library and `winterx-spring-app-actions-v1` plus native accessors in the engine. The older UI-fix2 and Neofetch-only engines do not gain app actions from copying a library into private data. Native Settings exposes help availability only on compatible builds. SSH actions are not exported as executable-tweak JavaScript globals.

## Build without installation

The optional library uses checksum-pinned Apache MINA SSHD **2.20.1** core/common/SFTP and SLF4J **2.0.17**, retaining dependency license notices. The builder downloads dependencies only from Maven Central and refuses unexpected hashes.

```sh
python3 patches/ssh/build.py builds/WinterX-SSH-dev.jar --deps path/to/dependency-cache \
  --javac /opt/homebrew/opt/openjdk/bin/javac
WINTERX_BUILD_ANIMAPER=1 WINTERX_BUILD_TRUSTED_FILES=1 WINTERX_BUILD_INBOX=1 \
  WINTERX_BUILD_SNOWYHOME=1 WINTERX_BUILD_MESSAGEPLUS=1 WINTERX_BUILD_SSH_ACTIONS=1 \
  WINTERX_SSH_LIBRARY="$PWD/builds/WinterX-SSH-dev.jar" \
  python3 patches/icon_positions/build.py Spring-0.8.1.apk builds/WinterXSpring-ssh-dev.apk
python3 tools/springys_tool.py build builtin-repo/sources/ssh builds/SSH-dev.springys
```

All outputs must be new. These commands build only; they do not configure the selected test, install Android updates, create user keys or launch Spring. The bridge gate requires ABI `winterx-sshd-auth-v1`, the real server dependency and native Settings helpers in a checksum-verified **running** engine. New info-capable libraries also declare `winterx-ssh-info-v1`; the older UI-fix2 engine does not contain the new report.

## Verification boundaries

`patches/ssh/check.py` takes the **new info-capable library or converted engine**. It checks actual configuration, host identity persistence and authentication without starting the server; keys live only in disposable fixtures. It also drives the real command factory and built-in command lifecycle using in-memory streams, fixed Android metadata objects and no SSH connection or shell. Info checks cover branding, aliases/help/plain output, honest metadata labels, missing values, bounded/control-safe output, privacy, exits, cancellation and output/provider failures. They are not live device-report verification.

`patches/tests/check_ssh_service.py converted-engine.jar --packaged` checks both iOS 4/6 root rows, direct/aliased platform roots, child-link refusal, serialized Start/Stop before state changes, pre-worker/busy cancellation, resource ownership, failed Start and Safe Mode/removal/key-change stopping using an **engine spy with no sockets or shell**. The reviewed build passes the locking/direct-root tests but fails the newer alias regression; UI-fix2 passes both roots. The original unsynchronized batch also fails the stronger lock test as a negative control.

NIO/JCE/host-key permission compatibility on Android, authenticated connection, SFTP, live built-in/action output, general exec, automatic status refresh and signing-compatible deployment remain unverified. SSH is enabled in the user-authorized local test, not automatically started or installed on Android. A source build alone does not select an engine or start a listener. SSH stays outside working catalogues.

App-command checks add in-memory parsing/dispatch, bounded queues, confirmation/checksum gates, at-most-once exits, cancellation and timeout behaviour. `check_ssh_actions.py --packaged` exercises the actual packaged adapter with **non-acting native spies** in disposable roots; it never installs, opens or closes a live app. `check_ssh_native_archive.py` exercises the real native file importer against a new disposable ID/directory with an icon-adapter spy; it does not create a launcher or execute JavaScript. Native patch-matrix checks verify the exact accessor/installer anchors and atomic rejection. These are distinct from an authenticated live action trial.

The interactive runner uses memory streams and keyboard/signal fixtures to check both client-PTY and plain streams, blue/plain snowflake output, app dispatch, CRLF/editing, bounded input, command/control rejection, Ctrl-C and disconnect cleanup. No live SSH connection or app action is performed. Client-terminal rendering still requires a user trial.
