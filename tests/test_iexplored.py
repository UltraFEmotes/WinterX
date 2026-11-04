import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import iexplored
import ruby_bridge

class ExplorerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = self.root / 'files'
        self.files.mkdir()
        self.explorer = iexplored.Explorer(self.files, self.root / 'trash')

    def test_browse_edit_trash_and_restore(self):
        self.explorer.mkdir('notes')
        self.explorer.write('notes/hello.txt', 'hello')
        self.assertEqual(self.explorer.read('notes/hello.txt'), 'hello')
        self.assertEqual(self.explorer.list('notes')[0]['name'], 'hello.txt')
        token = self.explorer.move_to_trash('notes/hello.txt')
        self.assertFalse((self.files/'notes/hello.txt').exists())
        self.explorer.restore(token)
        self.assertEqual(self.explorer.read('notes/hello.txt'), 'hello')

    def test_escape_and_symlinks_rejected(self):
        (self.files / 'outside').symlink_to(self.root)
        for path in ('../other', '/etc/passwd', 'outside/secret', 'a/../secret'):
            with self.subTest(path=path), self.assertRaises(ValueError): self.explorer.read(path)
        with self.assertRaises(ValueError): self.explorer.move_to_trash('')

    def test_restore_does_not_overwrite(self):
        self.explorer.write('a.txt', 'old')
        token = self.explorer.move_to_trash('a.txt')
        self.explorer.write('a.txt', 'new')
        with self.assertRaisesRegex(ValueError, 'already exists'): self.explorer.restore(token)
        self.assertEqual(self.explorer.read('a.txt'), 'new')

    def test_bridge_requests(self):
        data = self.root / 'app'
        request = data/'requests/123-456.json'
        request.parent.mkdir(parents=True)
        request.write_text(json.dumps({'id':'123-456','action':'list','path':''}))
        self.explorer.write('test.txt', 'content')
        ruby_bridge.process_explorer(request, data, self.files, self.root/'trash')
        reply = json.loads((data/'results/123-456.json').read_text())
        self.assertTrue(reply['ok'])
        self.assertEqual(reply['items'][0]['name'], 'test.txt')

if __name__ == '__main__': unittest.main()
