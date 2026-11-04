"""IExplored's bounded file operations for Spring's private files directory."""
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import time

MAX_TEXT = 512 * 1024
MAX_ITEMS = 2000

class Explorer:
    def __init__(self, root, trash):
        self.root = Path(root).resolve(strict=True)
        self.trash = Path(trash)
        if not self.root.is_dir():
            raise ValueError('Spring files directory is unavailable')

    def path(self, relative, existing=True):
        if not isinstance(relative, str) or '\x00' in relative or len(relative) > 2048 or '\\' in relative:
            raise ValueError('Invalid path')
        parts = PurePosixPath(relative).parts
        if PurePosixPath(relative).is_absolute() or any(part in ('.', '..') for part in relative.split('/')):
            raise ValueError('Path escapes Spring files')
        current = self.root
        for i, part in enumerate(parts):
            current = current / part
            if current.is_symlink():
                raise ValueError('Symbolic links cannot be opened')
            if not current.exists() and (existing or i != len(parts) - 1):
                raise ValueError('Path does not exist')
        if not current.resolve(strict=existing).is_relative_to(self.root):
            raise ValueError('Path escapes Spring files')
        return current

    def list(self, relative=''):
        folder = self.path(relative)
        if not folder.is_dir(): raise ValueError('Not a folder')
        items = []
        for child in folder.iterdir():
            if len(items) >= MAX_ITEMS: raise ValueError('Folder contains too many items')
            if child.is_symlink(): continue
            stat = child.stat()
            items.append({'name': child.name, 'directory': child.is_dir(), 'size': stat.st_size})
        return sorted(items, key=lambda x: (not x['directory'], x['name'].casefold()))

    def read(self, relative):
        file = self.path(relative)
        if not file.is_file() or file.stat().st_size > MAX_TEXT: raise ValueError('File is not a small text file')
        try: return file.read_text(encoding='utf-8')
        except UnicodeError as e: raise ValueError('File is not UTF-8 text') from e

    def write(self, relative, text):
        if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_TEXT: raise ValueError('Text is too large')
        file = self.path(relative, existing=False)
        if file == self.root or (file.exists() and not file.is_file()): raise ValueError('Not a file')
        fd, temporary = tempfile.mkstemp(prefix='.iexplored-', dir=file.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                out.write(text); out.flush(); os.fsync(out.fileno())
            os.replace(temporary, file)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    def mkdir(self, relative):
        path = self.path(relative, existing=False)
        if path == self.root: raise ValueError('Cannot replace the root')
        path.mkdir()

    def move_to_trash(self, relative):
        path = self.path(relative)
        if path == self.root: raise ValueError('Cannot remove the root')
        self.trash.mkdir(parents=True, exist_ok=True)
        if self.trash.is_symlink(): raise ValueError('Invalid trash folder')
        token = str(time.time_ns()) + '-' + os.urandom(4).hex()
        destination = self.trash / token
        # Keep a copy before moving; the index allows a later restore.
        import json
        index = self.trash / (token + '.json')
        index.write_text(json.dumps({'path': relative}), encoding='utf-8')
        try: os.replace(path, destination)
        except Exception:
            index.unlink(missing_ok=True)
            raise
        return token

    def restore(self, token):
        if not isinstance(token, str) or not re.fullmatch(r'\d+-[0-9a-f]{8}', token): raise ValueError('Invalid trash item')
        import json
        index = self.trash / (token + '.json')
        record = json.loads(index.read_text(encoding='utf-8'))
        destination = self.path(record['path'], existing=False)
        if destination.exists(): raise ValueError('A file already exists at the original location')
        item = self.trash / token
        if item.is_symlink() or not item.exists(): raise ValueError('Trash item not found')
        os.replace(item, destination)
        index.unlink()
