# Portable bridge work: Windows, Linux and Android

**Status: transports, bounded inventory/repository processing and host recovery journals implemented; Android engine installation and tweak reconciliation are not finished or live-verified.** The existing jailbreak bridge is still Mac.APK-only. Do not interpret a passing private-folder access probe or inventory request as a working Android jailbreak.

The target is a Windows/Linux/macOS host bridge for Spring 0.8.1 on Android devices or emulators with verified access to Spring's private files—not a check that merely says the device is rooted. Supported access mechanisms in the transport code are:

- ADB shell with actual access, including an emulator where the user has already enabled root ADB.
- ADB `run-as com.guille.spring`, only when that particular build permits it. Stock non-debuggable apps usually do not.
- ADB `su -c`, only on a device with working user-approved root access.
- An already accessible/mounted private files directory, without ADB. This is not an automatic mount or a bypass of Android permissions.
- An already configured Android SSH server, with key authentication and an already trusted/pinned host key. This is a host transport, not an installed WinterX SSH service/tweak.

The transport uses Python's standard library and invokes `adb`/`adb.exe` or OpenSSH without a host shell. It explicitly selects one target, preserves binary bytes, and quotes the remote command string including `sh -c` scripts/traps. Captured stdout/stderr and command duration are bounded on the host, as well as file reads/listings on the target. It rejects traversal/symlinks/Windows reserved filenames and restricts Android roots to Spring's `files` directory under `/data/data/` or `/data/user/<user>/`. Each remote file operation rechecks UID, folder ownership and the canonical root. Root-created entries retain Spring's UID/GID and use `restorecon` where available; enforcing SELinux without a working context-restoration path fails closed. No command disables SELinux or grants world-writable access.

## Access check (development only)

Install Python 3.10+ and Android platform-tools on the host. Authorize USB debugging or pair/connect ADB yourself. The tool does not turn on root, connect to a network endpoint, install an APK, stop or start Spring.

Linux/macOS, read-only permission check:

```sh
python3 tools/android_access.py --serial emulator-5554 --access shell
```

Windows, with platform-tools on PATH:

```powershell
py -3 tools/android_access.py --serial emulator-5554 --access shell
```

For an explicitly root-approved device, choose `--access su`. For an eligible debuggable build, choose `--access run-as`. Override `--files-root` only to the exact Spring private `files` directory, never a broad Android data/storage root. Override `--adb` to the full path of `adb.exe` if needed.

A shared/mounted directory can be checked with:

```sh
python3 tools/android_access.py --directory /path/to/spring/files
```

By default no files are written. Adding **`--write-probe`** explicitly creates one uniquely named probe under `ruby/`, reads its random bytes back and removes that probe. It may create `ruby/` if missing. It never writes page files, icon positions, code, preferences or engine-selection state. Back up first and use this only on a controlled test target. A permissions-only check is weaker than a completed write/read round trip.

## Inventory/repository processor (development only)

With Ruby already present in a controlled target and a complete data backup:

```sh
python3 tools/portable_bridge.py --serial emulator-5554 --access shell --state /path/to/host-recovery/emulator-5554
```

On Windows, use `py -3` and a dedicated host recovery path. `--directory` or `--ssh-host` can replace `--serial`. This processes pending Ruby requests once and exits. Do not put host recovery state inside Spring's private folder. Artwork/thumbnails require Pillow; neither a package scan nor repository management requires the Spring SDK. Adding/refreshing a repository can make HTTPS downloads requested by that Ruby action.

- Supported actions: `scan_packages`, `add_repository`, `remove_repository`, `refresh_repositories`.
- Mirroring is limited to Ruby's manifests, `.springys` imports, registry-owned files and artwork—not the whole private folder. Snapshots are capped at 256 files/24 MiB; transfer batches and host journals have separate bounds. Results are written only after successful conflict-checked transfer.
- `tools/private_transaction.py` retains a target-bound host journal before writes and restores known bytes after interruption. If a remote file differs from both expected/replacement bytes, recovery stays pending and refuses to clobber the external edit. Preserve this host state for recovery. This is a recoverable **sequence of file changes**, not an atomic filesystem-wide transaction or a hardened multi-host protocol.
- User imports, saved page JSON, sparse/legacy positions, capacity preferences and tweak state/data are not overwritten. Only hash-named repository imports and narrow bridge-owned outputs are writable.
- **Tweak install/remove requests are refused.** A pending package-registry operation also fails closed rather than being silently reconciled by a scan. APK installs, jailbreak, Safe Mode/respring, app installs/removals and file-explorer actions are not available through this processor.

Directory-transport scans/repository requests and interrupted/conflicting transfers pass isolated tests. ADB/SSH command generation is mocked, with an additional POSIX host-shell check of generated ADB script quoting. These are not real Android, SSH-server, Windows or Linux-host validation.

## Existing SSH server (development transport)

Use `--ssh-host user@android-test` (or a configured SSH alias), optionally `--ssh-port 2222`, in either access/bridge command. OpenSSH must already be installed. `BatchMode=yes` prevents password prompts; `StrictHostKeyChecking=yes` refuses untrusted/changed host keys. Tunnels and connection multiplexing are disabled. Set up and verify the server/key yourself. These tools do not install/start a daemon, generate credentials, accept a new host key or expose a public filesystem service. **No SSH server or connection was started during development.**

## What remains

- Complete runtime reconciliation and recovery after verifying the actually running Android engine before enabling compiled hooks or executable-tweak installation; a new APK on disk is insufficient.
- Implement safe Android deployment/signing and backup/rollback. Access to private data does not provide Spring's signing key. Do not uninstall stock Spring or erase its data to get around an update-signature mismatch.
- Test against real Windows/Linux hosts and an Android device/emulator, including app UID permissions, SELinux, architecture/native QuickJS support, updates and recovery. Current ADB command-generation tests use a fake transport; Windows API tests are simulated on macOS.
- Validate the separate [optional on-device SSH engine and native Settings controls](ssh.md) on Android. Its source and unselected batch2 are implemented, but configuration/service spies have not established a working listener, connection, SFTP or exec on Android. The existing SSH-client adapter is not that service. No public HTTP root/filesystem service is implemented or exposed.

`tools/file_lock.py` replaces the registry's unconditional `fcntl` import with Windows byte-range locking or POSIX flock. Tests cover genuine two-process contention on the current host and simulated Windows lock/unlock calls. Locks coordinate this host's bridge processes; they do not lock Spring or another host. Mac.APK's bridge remains separate.
