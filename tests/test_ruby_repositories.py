import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ruby_packages
import ruby_repositories
import springys_tool

ROOT = Path(__file__).resolve().parents[1]

class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        package = self.root / 'test.springys'
        springys_tool.build(ROOT / 'examples/settings-test', package)
        self.raw = package.read_bytes()
        self.url = 'https://example.test/repo/index.json'
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.files = self.root / 'files'
        self.package_ops = ruby_packages.Packages(self.files, self.root / 'settings-enabled', lambda enabled: {'ok': True})
        self.index = {'format': 'winterx.repository/1', 'name': 'Example', 'packages': [{'url': 'test.springys', 'sha256': self.sha}]}
        self.repo = ruby_repositories.Repositories(self.files, self.package_ops, self.fetch)

    def fetch(self, url, limit):
        if url == self.url:
            return json.dumps(self.index).encode()
        if url == 'https://example.test/repo/test.springys':
            return self.raw
        raise OSError('Not found')

    def test_add_refresh_install_update_remove(self):
        data = self.repo.add(self.url)
        self.assertEqual(data['sources'][0]['name'], 'Example')
        item = data['packages'][0]
        self.assertEqual(item['id'], 'me.weirdmm.settings-test')
        self.assertTrue((self.files / item['icon']).is_file())
        with Image.open(self.files / item['icon']) as icon:
            self.assertEqual(icon.size, (64, 64))
        self.package_ops.install(item['filename'])
        installed = self.package_ops.scan()['installed'][0]
        with Image.open(self.files / 'package-registry' / installed['icon']) as icon:
            self.assertEqual(icon.size, (64, 64))
        self.assertEqual(self.repo.refresh()['packages'][0]['installedSha256'], self.sha)
        self.package_ops.uninstall(item['id'])
        self.assertEqual(self.repo.remove(self.url)['sources'], [])

    def test_builtin_source_contains_valid_local_packages(self):
        repo = ruby_repositories.Repositories(self.files, self.package_ops, self.fetch,
                                                builtin_root=ROOT / 'builtin-repo')
        data = repo.refresh()
        self.assertTrue(data['sources'][0]['builtIn'])
        self.assertEqual(data['sources'][0]['name'], "Ruby's Built-in Repository")
        self.assertEqual([p['id'] for p in data['packages']], ['me.weirdmm.animaper', 'me.weirdmm.coloredbar', 'com.winterx.dockin',
            'com.winterx.freeme', 'com.winterx.messageplus', 'com.winterx.snowyhome', 'com.winterx.ssh',
            'com.winterx.gravity', 'com.winterx.harlemshake', 'com.winterx.androidkeyboard',
            'com.winterx.legacybooter', 'com.winterx.livepaper'])
        self.assertEqual({p['format'] for p in data['packages']}, {'winterx.springys/3'})
        self.assertTrue(all(p['sourceCode'].startswith('https://github.com/UltraFEmotes/Ruby-Repo/') for p in data['packages']))
        self.assertIsNone(data['sources'][0]['error'])

    def test_rejects_bad_hash_without_installing(self):
        self.index['packages'][0]['sha256'] = '0' * 64
        data = self.repo.add(self.url)
        self.assertEqual(data['packages'], [])
        self.assertIn('checksum', data['sources'][0]['error'])
        self.assertEqual(self.package_ops.registry.list(), {})

    def test_rejects_insecure_source(self):
        with self.assertRaises(ValueError):
            self.repo.add('http://example.test/repo.json')
        self.assertFalse(self.repo.sources.exists())

if __name__ == '__main__':
    unittest.main()
