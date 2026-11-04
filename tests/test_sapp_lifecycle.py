import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sapp_lifecycle
import ruby_bridge

class SappLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files, self.inbox, self.state = (self.root / x for x in ('files', 'inbox', 'state'))
        self.files.mkdir()
        self.running = True
        self.life = sapp_lifecycle.Lifecycle(self.files, self.inbox, self.state,
                                             ruby_bridge.pack.check_zip, lambda: self.running)
        self.app = self.root / 'IExplored.sapp'
        ruby_bridge.pack.pack(str(ROOT / 'IExplored'), str(self.app))

    def test_waits_for_spring_then_confirms_installed_build(self):
        result = self.life.queue_install('com.winterx.iexplored', self.app)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(self.life.reconcile()['installed'], {})
        (self.inbox / 'ruby-app-com.winterx.iexplored-4.sapp').unlink()
        manifest = self.files / 'sapps/com.winterx.iexplored/4/app.json'
        manifest.parent.mkdir(parents=True)
        with zipfile.ZipFile(self.app) as archive: archive.extractall(manifest.parent)
        state = self.life.reconcile()
        self.assertEqual(state['installed']['com.winterx.iexplored']['build'], 4)
        self.assertEqual(state['pending'], {})

    def test_remove_is_deferred_and_preserves_data_and_backup(self):
        self.life.queue_install('com.winterx.iexplored', self.app)
        (self.inbox / 'ruby-app-com.winterx.iexplored-4.sapp').unlink()
        manifest = self.files / 'sapps/com.winterx.iexplored/4/app.json'
        manifest.parent.mkdir(parents=True)
        with zipfile.ZipFile(self.app) as archive: archive.extractall(manifest.parent)
        data = self.files / 'sapps-data/com.winterx.iexplored/files/user.txt'
        data.parent.mkdir(parents=True); data.write_text('keep')
        self.life.reconcile()
        self.life.queue_remove('com.winterx.iexplored')
        self.life.reconcile()
        self.assertTrue(manifest.exists())
        self.running = False
        result = self.life.reconcile()
        self.assertFalse(manifest.exists())
        self.assertEqual(data.read_text(), 'keep')
        self.assertEqual(result['installed'], {})
        self.assertEqual(len(list((self.state / 'removed').iterdir())), 1)

    def test_ruby_bridge_queue_reports_pending(self):
        app_files = self.root / 'ruby'
        request = app_files / 'requests/123-456.json'
        request.parent.mkdir(parents=True)
        request.write_text(json.dumps({'id':'123-456', 'action':'queue_app_install',
                                       'appId':'com.winterx.iexplored'}))
        with patch.object(ruby_bridge, 'app_lifecycle', return_value=self.life):
            ruby_bridge.process(request, app_files, self.inbox)
        result = json.loads((app_files / 'results/123-456.json').read_text())
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(self.life.reconcile()['installed'], {})
        self.assertTrue((self.inbox / 'ruby-app-com.winterx.iexplored-4.sapp').exists())

    def test_wrong_id_and_conflicting_operations_rejected(self):
        with self.assertRaises(ValueError): self.life.queue_install('com.example.other', self.app)
        self.life.queue_install('com.winterx.iexplored', self.app)
        with self.assertRaises(ValueError): self.life.queue_install('com.winterx.iexplored', self.app)
        with self.assertRaises(ValueError): self.life.queue_remove('com.unknown.app')

if __name__ == '__main__': unittest.main()
