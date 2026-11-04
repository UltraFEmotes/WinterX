from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import iconpack


class IconPackTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'source'; (source / 'icons').mkdir(parents=True)
        Image.new('RGBA', (64, 64), (23, 45, 200, 160)).save(source / 'icons/mail.png')
        manifest = {'format': iconpack.FORMAT, 'id': 'me.example.icons', 'name': 'Fixture', 'author': 'Test',
                    'version': '0.1.0', 'icons': {'mail': {'file': 'icons/mail.png'}, 'sapp:me.example.app': {'file': 'icons/mail.png'}}}
        (source / 'manifest.json').write_text(json.dumps(manifest)); return source

    def test_deterministic_build_inspect_and_new_directory_export(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = self.fixture(root)
            first = iconpack.build(source, root / 'first.zip'); second = iconpack.build(source, root / 'second.zip')
            self.assertEqual(first[3], second[3]); self.assertEqual(first[0]['icons']['mail'], first[0]['icons']['sapp:me.example.app'])
            target = iconpack.export(root / 'first.zip', root / 'export')
            self.assertEqual(target.name, first[3]); self.assertEqual((target / 'icons/mail.png').read_bytes(), first[2]['icons/mail.png'])
            self.assertEqual((target / 'manifest.sha256').read_text(), iconpack.hashlib.sha256(first[1]).hexdigest())
            with self.assertRaises(ValueError): iconpack.export(root / 'first.zip', root / 'export')
            with self.assertRaises(ValueError): iconpack.build(source, root / 'first.zip')

    def test_pack_traversal_links_duplicate_code_and_tampered_images_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = self.fixture(root); result = iconpack.build(source, root / 'good.zip')
            for bad in ('../escape.png', 'icons/../escape.png', 'icons/bad.js', 'icons/CON.png', 'icons/LPT1.png'):
                value = json.loads(result[1]); value['icons']['mail']['file'] = bad
                with self.subTest(path=bad), self.assertRaises(ValueError): iconpack.manifest(json.dumps(value).encode())
            for n, extras in enumerate(({'icons/mail.png': b'corrupt'}, {'code/main.js': b'not allowed'}, {'manifest.json': b'{}'})):
                target = root / f'bad{n}.zip'
                with zipfile.ZipFile(target, 'w') as archive:
                    for file, data in {'manifest.json': result[1], **result[2], **extras}.items(): archive.writestr(file, data)
                with self.assertRaises(ValueError): iconpack.inspect(target)
            for app in ('folder:1', 'folder-utilities', '../x', 'bad\nname'):
                value = json.loads(result[1]); value['icons'] = {app: value['icons']['mail']}
                with self.subTest(app=app), self.assertRaises(ValueError): iconpack.manifest(json.dumps(value).encode())

    def test_image_bounds_real_decoding_and_animation_refused(self):
        for size in ((8, 8), (64, 32), (1025, 1025)):
            raw = BytesIO(); Image.new('RGBA', size).save(raw, format='PNG')
            with self.subTest(size=size), self.assertRaises(ValueError): iconpack.image(raw.getvalue())
        raw = BytesIO(); Image.new('RGBA', (64, 64)).save(raw, format='PNG')
        with self.assertRaises((ValueError, OSError)): iconpack.image(raw.getvalue()[:24])
        raw = BytesIO(); Image.new('RGBA', (64, 64)).save(raw, format='PNG', save_all=True,
            append_images=[Image.new('RGBA', (64, 64), 'red')], duration=100, loop=0)
        with self.assertRaises(ValueError): iconpack.image(raw.getvalue())

    def test_zip_duplicates_case_collisions_links_and_expansion_limit(self):
        import warnings
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = self.fixture(root); result = iconpack.build(source, root / 'good.zip')
            for i, extra in enumerate(('manifest.json', 'icons/Mail.png', 'link')):
                target = root / f'bad{i}.zip'
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    with zipfile.ZipFile(target, 'w') as archive:
                        for file, data in {'manifest.json': result[1], **result[2]}.items(): archive.writestr(file, data)
                        if extra == 'link':
                            entry = zipfile.ZipInfo('icons/link.png'); entry.external_attr = 0o120777 << 16
                            archive.writestr(entry, b'/outside/icon.png')
                        else: archive.writestr(extra, result[1] if extra == 'manifest.json' else result[2]['icons/mail.png'])
                with self.subTest(extra=extra), self.assertRaises(ValueError): iconpack.inspect(target)
            with zipfile.ZipFile(root / 'oversize.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('manifest.json', result[1]); archive.writestr('icons/mail.png', b'x' * (iconpack.MAX_ICON + 1))
            with self.assertRaises(ValueError): iconpack.inspect(root / 'oversize.zip')

    def test_source_limits_symlinks_duplicate_json_and_output_preservation(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = self.fixture(root); path = source / 'manifest.json'; raw = path.read_bytes()
            duplicate = raw[:-1] + b',"name":"duplicate"}'
            path.write_bytes(duplicate)
            with self.assertRaises(ValueError): iconpack.build(source, root / 'duplicate.zip')
            path.write_bytes(raw); icon = source / 'icons/mail.png'; outside = root / 'outside.png'
            icon.rename(outside); icon.symlink_to(outside)
            with self.assertRaises(ValueError): iconpack.build(source, root / 'linked.zip')
            self.assertFalse((root / 'linked.zip').exists()); icon.unlink(); outside.rename(icon)
            value = json.loads(raw); value['icons'] = {str(i): {'file': 'icons/mail.png'} for i in range(129)}
            path.write_text(json.dumps(value))
            with patch.object(iconpack, 'image') as decode, self.assertRaises(ValueError): iconpack.build(source, root / 'too-many.zip')
            decode.assert_not_called()
            self.assertFalse((root / 'too-many.zip').exists())
