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


def _atomic(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.ruby-art-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(contents)
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
    def __init__(self, app_files, marker, apply, extra_hooks=None):
        self.files = Path(app_files)
        self.imports = self.files / 'imports'
        self.marker = Path(marker)
        self.apply = apply
        self.hooks = {'test.settings': (self.marker, lambda enabled: self.apply(enabled))}
        if extra_hooks:
            self.hooks.update(extra_hooks)
        self.registry = springys_registry.Registry(self.files / 'package-registry', self._reconcile,
                                                    supported_hooks=tuple(self.hooks))

    def _reconcile(self, hooks):
        # Change only hooks owned by this transaction. Other manually installed
        # tweaks must survive installs, updates, removals, and journal recovery.
        managed = set(hooks)
        if self.registry.journal.exists():
            record = json.loads(self.registry.journal.read_text(encoding='utf-8'))
            for state in ('before', 'after'):
                managed.update(item['hook'] for item in record[state].values())
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
        hook = metadata['hook']
        if hook in self.hooks and self.hooks[hook][0].is_file() and not any(
                entry['hook'] == hook for entry in previous.values()):
            raise ValueError('Remove the existing %s tweak in Ruby before importing this package.' % ('Settings' if hook == 'test.settings' else hook))
        return self.registry.install(path, expected_sha256=expected)

    def uninstall(self, package_id):
        if not isinstance(package_id, str) or not ID.fullmatch(package_id):
            raise ValueError('Invalid package ID')
        return self.registry.uninstall(package_id)
