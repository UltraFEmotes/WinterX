from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches'))
import preview_boot
import settings_test

class PreviewBootstrapTests(unittest.TestCase):
    def test_injects_only_verified_boot_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activity = root / 'smali/com/guille/spring/LauncherActivity.smali'
            activity.parent.mkdir(parents=True)
            activity.write_text('.method public onCreate(Landroid/os/Bundle;)V\n' + settings_test.BOOT_MARKER + '\n' + (settings_test.CONTENT_CALL + '\n') * 3 + '.end method\n')
            preview_boot.apply(root)
            text = activity.read_text()
            self.assertEqual(text.count('Lruby/RubyHooks;->showBoot'), 3)
            self.assertEqual(text.count('Lruby/RubyHooks;->boot'), 1)
            hooks = (root / 'smali/ruby/RubyHooks.smali').read_text()
            self.assertNotIn('showWelcome', hooks)
            self.assertNotIn('settingsEnabled', hooks)
            with self.assertRaises(ValueError):
                preview_boot.apply(root)

    def test_rejects_different_activity_without_mutating_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activity = root / 'smali/com/guille/spring/LauncherActivity.smali'
            activity.parent.mkdir(parents=True)
            activity.write_text('not the expected code')
            with self.assertRaises(ValueError):
                preview_boot.apply(root)
            self.assertEqual(activity.read_text(), 'not the expected code')
            self.assertFalse((root / 'smali/ruby').exists())
