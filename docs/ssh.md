# SSH — optional, unlisted development tweak

An optional on-device SSH/SFTP engine is implemented in source and the separate batch2. It is **not installed or live-verified on Android**, and no listener, connection or command was started during development. The host-side SSH transport is a separate feature.

## Explicit native controls

On a compatible running engine with the unlisted `com.winterx.ssh` / `tweak.ssh` package, **Spring Settings → WINTERX TWEAKS → SSH** offers **Start SSH for This Session** and **Stop SSH**. Install, boot and Safe Mode exit never start it automatically.

The selected reviewed batch2 and enabled marker were verified during a missing-UI report. Its path guard nevertheless rejected Mac.APK's legitimate platform-files alias. The separate UI-fix candidate resolves that trusted root while retaining rejection of links in markers, `ruby/`, SSH directories and authorized keys. Building it does not change the running engine or start SSH.

- Binds **127.0.0.1:2222** only; username **winterx**; public-key authentication only. No passwords, root, automatic LAN exposure, forwarding or interactive PTY.
- Plain RSA (3072+ bits), Ed25519 or P-256 public keys in `files/ruby/ssh/authorized_keys`, maximum eight keys / 16 KiB. Options/certificates are refused. Actual Android crypto support still needs verification.
- On explicit Start, persists a private RSA host identity at `files/ruby/ssh/host-key.ser`; native Settings displays its fingerprint. Host keys are not overwritten to resolve an authentication problem.
- SFTP is rooted at Spring's private files. Exec uses `/system/bin/sh -c` as **Spring's UID**, not `su`. Authorized keys can change Spring's accessible data; this is powerful app-level access, **not a sandbox for untrusted users**.
- Stop cancels in-flight Start and closes owned resources. Safe Mode, removal or changed authorized keys stop/refuse activation; another explicit Start is required.

Remote access would require an external tunnel configured deliberately by the user. No tunnel/network/root setup is performed by these tools. Private-folder access does not provide Spring's Android signing key; never uninstall/reinstall Spring to bypass signing.

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

All outputs must be new. These commands build only; they do not configure the selected test, install Android updates, create user keys or launch Spring. The bridge gate requires ABI `winterx-sshd-auth-v1`, the real server dependency and native Settings helpers in a checksum-verified **running** engine.

## Verification boundaries

`patches/ssh/check.py` checks actual configuration, host identity persistence and authentication without calling Start; its keys live only in disposable fixtures. `patches/tests/check_ssh_service.py converted-engine.jar --packaged` checks both iOS 4/6 root rows, direct/aliased platform roots, child-link refusal, serialized Start/Stop before state changes, pre-worker/busy cancellation, resource ownership, failed Start and Safe Mode/removal/key-change stopping using an **engine spy with no sockets or commands**. The reviewed build passes the locking/direct-root tests but fails the newer alias regression. The original unsynchronized batch also fails the stronger lock test as a negative control.

NIO/JCE/host-key permission compatibility on Android, authenticated connection, SFTP, exec, service refresh and signing-compatible deployment remain unverified. SSH is enabled in the user-authorized reviewed local test, not started or installed on Android. The correction candidate remains unselected; SSH stays outside working catalogues.
