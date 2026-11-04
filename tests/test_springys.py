import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import springys


class SpringysTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.springys'
        self.png = (Path(__file__).resolve().parents[1] / 'Ruby/icon.png').read_bytes()
        self.manifest = {'format': springys.FORMAT, 'id': 'me.example.test', 'name': 'Test', 'version': '1.0',
                         'description': 'A test package.', 'author': 'Example', 'hook': 'test.settings',
                         'icon': 'assets/icon.png', 'previews': ['assets/screen.png']}

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, manifest=None, extras=()):
        with zipfile.ZipFile(self.path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('manifest.json', json.dumps(manifest or self.manifest))
            z.writestr('assets/icon.png', self.png)
            z.writestr('assets/screen.png', self.png)
            for name, value in extras:
                z.writestr(name, value)

    def test_metadata_and_artwork(self):
        self.make()
        sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        metadata, art = springys.inspect(self.path, sha)
        self.assertEqual(metadata['description'], 'A test package.')
        self.assertEqual(metadata['previews'], ['assets/screen.png'])
        self.assertEqual(art['assets/icon.png'], self.png)
        with self.assertRaises(springys.PackageError):
            springys.inspect(self.path, '0' * 64)

    def test_traversal_and_unreferenced_files_are_rejected(self):
        self.make(extras=[('assets/../escape.png', self.png)])
        with self.assertRaises(springys.PackageError):
            springys.inspect(self.path)
        self.make(extras=[('assets/unlisted.png', self.png)])
        with self.assertRaises(springys.PackageError):
            springys.inspect(self.path)

    def test_invalid_identity_and_artwork_are_rejected(self):
        bad = dict(self.manifest, id='../bad')
        self.make(bad)
        with self.assertRaises(springys.PackageError):
            springys.inspect(self.path)
        self.png = b'not an image'
        self.make()
        with self.assertRaises(springys.PackageError):
            springys.inspect(self.path)

    def test_symlink_rejected(self):
        self.make()
        with zipfile.ZipFile(self.path, 'a') as z:
            i = zipfile.ZipInfo('assets/link.png')
            i.create_system = 3
            i.external_attr = (0o120777 << 16)
            z.writestr(i, 'target')
        with self.assertRaises(springys.PackageError):
            springys.inspect(self.path)


if __name__ == '__main__':
    unittest.main()
