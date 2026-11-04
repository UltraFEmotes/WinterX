# Portable bridge work: Windows, Linux and Android

**Status: transport and locking foundation implemented; full Android bridge/deployment is not finished or live-verified.** The existing jailbreak bridge is still Mac.APK-only. Do not interpret a passing private-folder access probe as a working Android jailbreak.

The target is a Windows/Linux/macOS host bridge for Spring 0.8.1 on Android devices or emulators with verified access to Spring's private files—not a check that merely says the device is rooted. Supported access mechanisms in the transport code are:

- ADB shell with actual access, including an emulator where the user has already enabled root ADB.
- ADB `run-as com.guille.spring`, only when that particular build permits it. Stock non-debuggable apps usually do not.
- ADB `su -c`, only on a device with working user-approved root access.
- An already accessible/mounted private files directory, without ADB. This is not an automatic mount or a bypass of Android permissions.

The source uses only Python's standard library and invokes `adb`/`adb.exe` without a host shell. It explicitly selects one serial, uses binary `exec-out`, bounds file reads and listings, rejects traversal/symlinks/Windows reserved filenames, and checks app UID ownership. Root-created entries retain Spring's UID/GID and use `restorecon` where available; enforcing SELinux without a working context-restoration path fails closed. No command disables SELinux or grants world-writable access.

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

## What remains

- Connect the transport to the portable Ruby request/package/repository processor with bounded mirroring, conflict checks and interrupted-operation recovery. Do not blindly synchronize the entire private folder.
- Verify the actually running Android engine before enabling compiled hooks or executable-tweak installation; a new APK on disk is insufficient.
- Implement safe Android deployment/signing and backup/rollback. Access to private data does not provide Spring's signing key. Do not uninstall stock Spring or erase its data to get around an update-signature mismatch.
- Test against real Windows/Linux hosts and an Android device/emulator, including app UID permissions, SELinux, architecture/native QuickJS support, updates and recovery. Current ADB command-generation tests use a fake transport; Windows API tests are simulated on macOS.
- Add authenticated LAN/device-side service support separately if needed. No public HTTP root/filesystem service is implemented or exposed.

`tools/file_lock.py` replaces the registry's unconditional `fcntl` import with Windows byte-range locking or POSIX flock. Tests cover genuine two-process contention on the current host and simulated Windows lock/unlock calls. Mac.APK's bridge retains its existing behaviour.
