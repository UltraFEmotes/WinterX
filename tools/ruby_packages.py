"""Local .springys package operations for the Ruby bridge on Mac.APK."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import os
import re
import tempfile

import springys
import springys_registry

ID = re.compile(r'^[a-z0-9]+(?:[.-][a-z0-9]+)+$')


def _same_stage(source, expected):
    """Staged registry tree still matches its recorded sha256 before it runs."""
    try:
        digest = (source / 'sha256').read_text(encoding='utf-8').strip()
        code = (source / 'code/main.js').read_bytes()
        return digest == expected and springys_registry._same_tree(source, expected)
    except (OSError, ValueError):
        return False


def _sync_tree(source, target):
    """Replace only runtime-owned files; retain the user's tweak state/data."""
    target = Path(target)
    target = target.parent.resolve() / target.name
    if target.is_symlink() or target.resolve() != target.absolute():
        raise ValueError('Tweak storage must not contain symlinks')
    changes = []
    for relative in ('code/main.js', 'manifest.json', 'sha256', 'manifest.sha256'):
        path = source / relative
        destination = target / relative
        if destination.is_symlink() or destination.resolve() != destination.absolute():
            raise ValueError('Tweak storage must not contain symlinks')
        payload = path.read_bytes()
        if destination.is_file() and destination.read_bytes() == payload:
            continue
        changes.append((destination, payload))
    # Reconciliation also visits unchanged packages. Leave their enabled marker
    # intact or a live context may mistake an unrelated install for removal.
    if changes:
        (target / 'enabled').unlink(missing_ok=True)
        for destination, payload in changes:
            _atomic(destination, payload)
    if not (target / 'enabled').is_file():
        _atomic(target / 'enabled', b'enabled\n')
        try:
            (target / 'enabled').chmod(0o644)
        except OSError:
            pass


def _atomic(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.ruby-art-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(contents)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def icon_thumbnail(root, payload, directory='package-art'):
    """Make a 32-point icon for Spring's 44-point table rows."""
    from PIL import Image
    with Image.open(BytesIO(payload)) as original:
        image = original.convert('RGBA')
        image.thumbnail((64, 64), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((64 - image.width) // 2, (64 - image.height) // 2))
        out = BytesIO()
        canvas.save(out, format='PNG')
    name = 'icon-64-' + hashlib.sha256(payload).hexdigest() + '.png'
    relative = directory + '/' + name
    _atomic(Path(root) / relative, out.getvalue())
    return relative


class Packages:
    def __init__(self, app_files, marker, apply, extra_hooks=None, tweak_root=None, supported_tweaks=False, supported_capabilities=()):
        self.files = Path(app_files)
        self.imports = self.files / 'imports'
        self.marker = Path(marker)
        self.apply = apply
        # Engine-visible location (Spring's own files dir) for tweak code.
        self.tweaks_root = Path(tweak_root or (self.files / 'winterx-tweaks'))
        self.hooks = {'test.settings': (self.marker, lambda enabled: self.apply(enabled))}
        if extra_hooks:
            self.hooks.update(extra_hooks)
        self.registry = springys_registry.Registry(self.files / 'package-registry', self._reconcile,
                                                     supported_hooks=tuple(self.hooks), supported_tweaks=supported_tweaks,
                                                     supported_capabilities=supported_capabilities)

    def _reconcile(self, hooks, tweaks=None):
        # Change only hooks and tweaks owned by this transaction. Other manually
        # installed tweaks must survive installs, updates, removals, and journal
        # recovery.
        managed = set(hooks)
        desired_tweaks = tweaks or {}
        managed_tweaks = set(desired_tweaks)
        if self.registry.journal.exists():
            record = json.loads(self.registry.journal.read_text(encoding='utf-8'))
            for state in ('before', 'after'):
                managed.update(item['hook'] for item in record[state].values() if item.get('hook'))
                managed_tweaks.update(key for key, item in record[state].items()
                                      if item.get('type') == 'tweak')
        for tweak_id in sorted(managed_tweaks):
            if not ID.fullmatch(tweak_id):
                continue
            target = self.tweaks_root.resolve() / tweak_id
            if target.is_symlink():
                raise ValueError('Tweak storage must not contain symlinks')
            if tweak_id not in desired_tweaks:
                # Disabling is sufficient; preserve state/data and old code for
                # recovery. No recursively deleted user files on uninstall.
                (target / 'enabled').unlink(missing_ok=True)
                continue
            entry = desired_tweaks[tweak_id]
            stage = entry.get('tweak_stage', '')
            if not re.fullmatch(r'tweaks/[0-9a-f]{64}', stage):
                raise RuntimeError('Invalid tweak revision path')
            source = self.registry.root / stage
            if not _same_stage(source, entry['code_sha256']):
                raise RuntimeError('Installed tweak code failed integrity check for ' + tweak_id)
            _sync_tree(source, target)
        for hook in sorted(managed):
            if hook not in self.hooks:
                raise ValueError('Unsupported hook: ' + hook)
            marker, apply = self.hooks[hook]
            enabled = hook in hooks
            if marker.is_file() == enabled:
                continue
            result = apply(enabled)
            if not result.get('ok'):
                raise RuntimeError(result.get('message', 'Tweak could not be applied'))

    def _package(self, name):
        if not isinstance(name, str) or Path(name).name != name or not name.lower().endswith('.springys'):
            raise ValueError('Invalid package filename')
        directory = self.imports.resolve(strict=True)
        path = (directory / name)
        if path.is_symlink() or not path.is_file() or path.resolve().parent != directory:
            raise ValueError('Package must be a regular file in Ruby imports')
        return path

    def scan(self):
        self.registry.recover()
        installed = self.registry.list()
        available = []
        self.imports.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.imports.glob('*.springys')):
            try:
                path = self._package(path.name)
                metadata, images = springys.inspect(path)
                metadata['filename'] = path.name
                metadata['installedVersion'] = installed.get(metadata['id'], {}).get('version')
                metadata['installedSha256'] = installed.get(metadata['id'], {}).get('sha256')
                art = {}
                for name, payload in images.items():
                    target = 'package-art/' + hashlib.sha256(payload).hexdigest() + Path(name).suffix.lower()
                    _atomic(self.files / target, payload)
                    art[name] = target
                icon = metadata['icon']
                metadata['icon'] = icon_thumbnail(self.files, images[icon]) if icon else None
                metadata['previews'] = [art[name] for name in metadata['previews']]
                available.append(metadata)
            except (OSError, ValueError):
                continue
        installed_display = []
        for entry in installed.values():
            display = dict(entry)
            icon = display.get('icon')
            if icon:
                try:
                    root = self.registry.root.resolve(strict=True)
                    path = (root / icon).resolve(strict=True)
                    if not path.is_relative_to(root) or not path.is_file():
                        raise ValueError('Invalid installed icon')
                    display['icon'] = icon_thumbnail(root, path.read_bytes(), 'art')
                except (OSError, ValueError):
                    display['icon'] = None
            installed_display.append(display)
        return {'available': available, 'installed': installed_display}

    def install(self, filename):
        path = self._package(filename)
        self.registry.recover()
        previous = self.registry.list()
        expected = None
        if re.fullmatch(r'repo-[0-9a-f]{64}\.springys', filename):
            expected = filename[5:-9]
        metadata, _ = springys.inspect(path, expected)
        hook = metadata.get('hook')
        if hook and hook in self.hooks and self.hooks[hook][0].is_file() and not any(
                 entry.get('hook') == hook for entry in previous.values()):
            raise ValueError('Remove the existing %s tweak in Ruby before importing this package.' % ('Settings' if hook == 'test.settings' else hook))
        return self.registry.install(path, expected_sha256=expected)

    def uninstall(self, package_id):
        if not isinstance(package_id, str) or not ID.fullmatch(package_id):
            raise ValueError('Invalid package ID')
        return self.registry.uninstall(package_id)
