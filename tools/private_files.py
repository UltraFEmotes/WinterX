"""Bounded private-folder transports. No APK installation, process control or automatic service setup."""
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import tempfile
import uuid

from bounded_process import run as bounded_run

MAX_FILE = 24 * 1024 * 1024
SAFE_PART = re.compile(r'^[A-Za-z0-9_.-]+$')
SERIAL = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}$')
PACKAGE = 'com.guille.spring'
APP_ROOT = re.compile(r'^/data/(?:data|user/[0-9]+)/com\.guille\.spring/files$')
MISSING = 44
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


class AccessError(RuntimeError):
    pass


class ConflictError(AccessError):
    pass


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError('Invalid private-folder path')
    parts = value.split('/')
    if len(parts) > 20 or any(p in ('', '.', '..') or not SAFE_PART.fullmatch(p) or p.endswith('.') or
                              p.split('.')[0].upper() in RESERVED for p in parts):
        raise ValueError('Private-folder paths must be relative, without links or traversal')
    return '/'.join(parts)


def _payload(value):
    if not isinstance(value, bytes) or len(value) > MAX_FILE:
        raise ValueError('Private-folder writes require bytes, at most 24 MiB')


class DirectoryFiles:
    """An already accessible shared/mounted Spring files folder, on any host OS."""
    def __init__(self, root):
        root = Path(root)
        if root.is_symlink() or not root.is_dir():
            raise AccessError('Select an existing private files directory, not a symlink')
        self.root = root.resolve(strict=True)

    def _path(self, relative):
        path = self.root
        for part in relative_path(relative).split('/'):
            path = path / part
            if path.is_symlink():
                raise AccessError('Private-folder symlinks are refused')
        if path.resolve().is_relative_to(self.root):
            return path
        raise AccessError('Path escapes the private folder')

    def read(self, relative, limit=MAX_FILE):
        if not isinstance(limit, int) or not 0 <= limit <= MAX_FILE:
            raise ValueError('Invalid read limit')
        path = self._path(relative)
        if not path.exists():
            return None
        if not path.is_file():
            raise AccessError('Expected a regular private file')
        with path.open('rb') as source:
            value = source.read(limit + 1)
        if len(value) > limit:
            raise AccessError('Private file exceeds the read limit')
        return value

    def write(self, relative, value, *, expected):
        _payload(value)
        path = self._path(relative)
        if self.read(relative) != expected:
            raise ConflictError('Private file changed; refusing to overwrite it')
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.winterx-write-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as out:
                out.write(value)
                out.flush()
                os.fsync(out.fileno())
            # Preserve an existing mount's mode instead of changing access rights.
            if path.exists():
                os.chmod(name, path.stat().st_mode & 0o777)
            if self.read(relative) != expected:
                raise ConflictError('Private file changed while writing')
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def remove(self, relative, *, expected):
        path = self._path(relative)
        if self.read(relative) != expected:
            raise ConflictError('Private file changed; refusing to remove it')
        if path.exists():
            path.unlink()

    def list_files(self, relative, limit=2000):
        if not isinstance(limit, int) or not 1 <= limit <= 10000:
            raise ValueError('Invalid directory file limit')
        path = self._path(relative)
        if not path.exists():
            return []
        if not path.is_dir():
            raise AccessError('Expected a private directory')
        result = []
        for base, dirs, files in os.walk(path, followlinks=False):
            for name in dirs + files:
                item = Path(base) / name
                if item.is_symlink():
                    raise AccessError('Private-folder symlinks are refused')
                relative_path(item.relative_to(self.root).as_posix())
            for name in files:
                result.append((Path(base) / name).relative_to(self.root).as_posix())
                if len(result) > limit:
                    raise AccessError('Private directory exceeds the file limit')
        return sorted(result)


class AdbFiles:
    """ADB exec-out avoids Windows shell quoting and binary/newline conversion."""
    def __init__(self, serial, root='/data/user/0/com.guille.spring/files', access='shell', adb='adb', runner=bounded_run):
        if not isinstance(serial, str) or not SERIAL.fullmatch(serial):
            raise ValueError('Choose one explicit, valid ADB serial')
        if access not in ('shell', 'run-as', 'su'):
            raise ValueError('ADB access must be shell, run-as or su')
        if not isinstance(root, str) or not root.startswith('/'):
            raise ValueError('Android private folder must be absolute')
        relative_path(root[1:])
        if not APP_ROOT.fullmatch(root):
            raise ValueError('Select Spring\'s private files directory, not a broad device root')
        self.serial, self.root, self.access = serial, root, access
        self.adb, self.runner = str(adb), runner
        self.identity = None

    def _run(self, script, payload=None, missing=False):
        command = [self.adb, '-s', self.serial, 'exec-out']
        command.append(shlex.join(self._remote(script)))
        return self._capture(command, payload, missing, 'ADB')

    def _remote(self, script):
        if self.access == 'su':
            remote = ['su', '-c', script]
        elif self.access == 'run-as':
            remote = ['run-as', PACKAGE, 'sh', '-c', script]
        else:
            remote = ['sh', '-c', script]
        # ADB executes a remote command string, not a preserved argv vector. Quote the
        # entire sh -c argument, including newlines, traps and inner single quotes.
        return remote

    def _capture(self, command, payload, missing, transport):
        try:
            result = self.runner(command, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=20, check=False, shell=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AccessError(transport + ' could not reach the selected device: ' + str(exc)) from exc
        if missing and result.returncode == MISSING:
            return None
        if result.returncode:
            if result.returncode == 45:
                raise ConflictError('Android private file changed; operation refused')
            detail = result.stderr.decode('utf-8', errors='replace').strip()[:200]
            raise AccessError(transport + ' private-folder access failed' + (': ' + detail if detail else ''))
        return result.stdout

    def verify(self):
        """Read-only identity/path/permission check; does not grant or enable root."""
        self.identity = None
        q = shlex.quote(self.root)
        raw = self._run('set -eu\ntest -d ' + q + '\ncd ' + q + '\npwd -P\nid -u\nstat -c \'%u:%g\' .\n'
                        'if test -r . && test -w . && test -x .; then echo rw; else echo denied; fi\n')
        lines = raw.decode('utf-8', errors='strict').splitlines()
        if len(lines) != 4 or not lines[0].startswith('/') or not re.fullmatch(r'[0-9]+', lines[1]) or not re.fullmatch(r'[0-9]+:[0-9]+', lines[2]):
            raise AccessError('Unexpected Android private-folder identity response')
        relative_path(lines[0][1:])
        if not APP_ROOT.fullmatch(lines[0]):
            raise AccessError('Resolved path is not a private files directory')
        uid = int(lines[1]); owner, group = map(int, lines[2].split(':'))
        if lines[3] != 'rw' or uid not in (0, owner) or owner == 0:
            raise AccessError('Need writable access as Spring\'s app UID or root; permissions/SELinux still apply')
        self.root = lines[0]
        self.identity = {'uid': uid, 'owner': owner, 'group': group, 'access': self.access, 'filesRoot': self.root}
        return dict(self.identity)

    def _guard(self, relative, directory=False, create=False):
        if self.identity is None:
            raise AccessError('Verify private-folder access before reading or writing')
        parts = relative_path(relative).split('/')
        path = self.root
        script = 'set -eu\ntest -d ' + shlex.quote(path) + '\ntest ! -L ' + shlex.quote(path) + '\n'
        script += ('test "$(id -u)" = ' + str(self.identity['uid']) + '\n'
                   'test "$(stat -c \'%u:%g\' ' + shlex.quote(path) + ')" = '
                   + str(self.identity['owner']) + ':' + str(self.identity['group']) + '\n'
                   'test "$(cd ' + shlex.quote(path) + ' && pwd -P)" = ' + shlex.quote(path) + '\n')
        for index, part in enumerate(parts):
            path += '/' + part
            q = shlex.quote(path)
            is_dir = index < len(parts) - 1 or directory
            script += 'test ! -L ' + q + '\n'
            if is_dir:
                if create:
                    script += 'if test ! -e ' + q + '; then mkdir ' + q + '\nchmod 700 ' + q + '\n'
                    script += self._owner(q) + 'fi\n'
                script += 'if test -e ' + q + '; then test -d ' + q + '; fi\n'
            else:
                script += 'if test -e ' + q + '; then test -f ' + q + '; fi\n'
        return script, shlex.quote(path)

    def _owner(self, quoted):
        if self.identity['uid'] != 0:
            return ''
        owner = str(self.identity['owner']) + ':' + str(self.identity['group'])
        # A root-created file can otherwise be unreadable to Spring under SELinux.
        return ('chown ' + owner + ' ' + quoted + '\n'
                'if command -v restorecon >/dev/null 2>&1; then restorecon -F ' + quoted + '\n'
                'elif test "$(getenforce 2>/dev/null || true)" = Enforcing; then exit 46; fi\n')

    def read(self, relative, limit=MAX_FILE):
        if not isinstance(limit, int) or not 0 <= limit <= MAX_FILE:
            raise ValueError('Invalid read limit')
        script, q = self._guard(relative)
        raw = self._run(script + 'if test ! -e ' + q + '; then exit 44; fi\nhead -c ' + str(limit + 1) + ' ' + q + '\n', missing=True)
        if raw is not None and len(raw) > limit:
            raise AccessError('Android private file exceeds the read limit')
        return raw

    @staticmethod
    def _compare(q, expected):
        if expected is None:
            return 'if test -e ' + q + '; then exit 45; fi\n'
        _payload(expected)
        digest = hashlib.sha256(expected).hexdigest()
        return ('test -f ' + q + ' || exit 45\nactual=$(sha256sum ' + q + ')\n'
                'test "${actual%% *}" = ' + digest + ' || exit 45\n')

    def write(self, relative, value, *, expected):
        _payload(value)
        script, q = self._guard(relative, create=True)
        parent = str(PurePosixPath(self.root) / PurePosixPath(relative).parent)
        temp = shlex.quote(parent + '/.winterx-write-' + uuid.uuid4().hex)
        script += 'test ! -e ' + temp + '\ntest ! -L ' + temp + '\n'
        script += '(umask 077; set -C; : > ' + temp + ')\n'
        script += 'trap ' + shlex.quote('rm -f ' + temp) + ' EXIT\n'
        script += 'cat > ' + temp + '\n'
        # A disconnected stdin can look like a clean EOF to the remote cat. Verify
        # the complete replacement before touching the existing destination.
        script += ('received=$(sha256sum ' + temp + ')\n'
                   'test "${received%% *}" = ' + hashlib.sha256(value).hexdigest() + ' || exit 47\n')
        script += self._owner(temp)
        script += self._compare(q, expected) + 'mv ' + temp + ' ' + q + '\n'
        self._run(script, value)

    def remove(self, relative, *, expected):
        script, q = self._guard(relative)
        script += self._compare(q, expected)
        script += 'if test -e ' + q + '; then rm ' + q + '; fi\n'
        self._run(script)

    def list_files(self, relative, limit=2000):
        if not isinstance(limit, int) or not 1 <= limit <= 10000:
            raise ValueError('Invalid directory file limit')
        script, q = self._guard(relative, directory=True)
        # Refuse links, rather than silently omitting a link substituted for data.
        script += 'if test ! -e ' + q + '; then exit 44; fi\n'
        script += 'links=$(find ' + q + ' -type l -print -quit)\ntest -z "$links"\n'
        # Bound output on device as well as host; every safe relative path <= 1024.
        script += 'find ' + q + ' -type f -print0 | head -c ' + str((limit + 1) * 1026) + '\n'
        raw = self._run(script, missing=True)
        if raw is None:
            return []
        if raw and not raw.endswith(b'\0'):
            raise AccessError('Android directory listing exceeded the limit')
        result = []
        for entry in raw.split(b'\0')[:-1]:
            absolute = entry.decode('utf-8', errors='strict')
            if not absolute.startswith(self.root + '/'):
                raise AccessError('Android listing escapes the private folder')
            item = relative_path(absolute[len(self.root) + 1:])
            if not item.startswith(relative.rstrip('/') + '/'):
                raise AccessError('Android listing escapes the selected directory')
            result.append(item)
        if len(result) > limit:
            raise AccessError('Android directory exceeds the file limit')
        return sorted(result)


class SshFiles(AdbFiles):
    """An already configured Android SSH server. Never installs/enables a daemon or accepts new host keys."""
    def __init__(self, host, root='/data/user/0/com.guille.spring/files', access='shell', port=22,
                 ssh='ssh', runner=bounded_run):
        if not isinstance(host, str) or not re.fullmatch(r'(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,79}@)?[A-Za-z0-9][A-Za-z0-9_.-]{0,199}', host):
            raise ValueError('Select an explicit SSH host or configured alias, without shell options')
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError('Invalid SSH port')
        super().__init__('ssh-target', root, access, runner=runner)
        self.host, self.port, self.ssh = host, port, str(ssh)

    def _run(self, script, payload=None, missing=False):
        command = [self.ssh, '-T', '-p', str(self.port), '-o', 'BatchMode=yes',
                   '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
                   '-o', 'ClearAllForwardings=yes', '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
                   '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no', '-o', 'PermitLocalCommand=no',
                   self.host, shlex.join(self._remote(script))]
        return self._capture(command, payload, missing, 'SSH')


def write_probe(store):
    """Explicit reversible round-trip probe. Never touches layouts or tweak state."""
    relative = 'ruby/.winterx-access-' + uuid.uuid4().hex
    value = os.urandom(32)
    store.write(relative, value, expected=None)
    try:
        if store.read(relative, 32) != value:
            raise AccessError('Private-folder write/read verification failed')
    finally:
        store.remove(relative, expected=value)
