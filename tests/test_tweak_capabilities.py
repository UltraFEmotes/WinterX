import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import tweak_runtime


class CapabilityTests(unittest.TestCase):
    def test_missing_or_old_engine_is_not_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / 'engine.apk'
            self.assertFalse(tweak_runtime.supported_by(apk))
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'old engine')
                archive.writestr('classes3.dex', b'winterx/tweaks/TweakHost winterx/tweaks/TweakSettings')
            self.assertFalse(tweak_runtime.supported_by(apk))
            self.assertFalse(tweak_runtime.coloredbar_supported_by(apk))

    def test_active_engine_requires_matching_checksum_and_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            apk = state / 'engine.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'winterxCreate winterx/coloredbar/ColoredBar')
                archive.writestr('classes3.dex', b'winterx/tweaks/TweakHost winterx/tweaks/TweakSettings coloredbar.exclusions.json')
            sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            self.assertTrue(tweak_runtime.supported_by(apk))
            self.assertTrue(tweak_runtime.coloredbar_supported_by(apk))
            (state / 'active.json').write_text(json.dumps({'apk': str(apk), 'apk_sha256': sha, 'pid': 123}))
            self.assertIsNone(tweak_runtime.active_engine(state, lambda *args: False))
            self.assertEqual(tweak_runtime.active_engine(state, lambda *args: True), apk)
            (state / 'active.json').write_text(json.dumps({'apk': str(apk), 'apk_sha256': 'bad', 'pid': 123}))
            self.assertIsNone(tweak_runtime.active_engine(state, lambda *args: True))

    def test_messageplus_needs_both_versioned_helper_and_native_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / 'engine.apk'
            for native, helper, supported in (
                (b'old engine', b'messageplus-settings-photo-v1 winterx/messages/MessagePlus', False),
                (b'winterx/messages/MessagePlus', b'winterx/messages/MessagePlus', False),
                (b'winterx/messages/MessagePlus', b'messageplus-settings-photo-v1 winterx/messages/MessagePlus', True),
            ):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes.dex', native)
                    archive.writestr('classes3.dex', helper)
                self.assertEqual(tweak_runtime.messageplus_supported_by(apk), supported)

    def test_app_commands_require_native_accessors_and_keep_neofetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / 'engine.apk'
            native = b'winterxSappManager winterxInstallArchive'
            helper = (b'winterx-ssh-app-v1 winterx-spring-app-actions-v1 winterx-ssh-info-v1 winterx/ssh/AppCommand winterx/ssh/SshActions '
                      b'winterx-sshd-auth-v1 winterx/ssh/SshServerEngine org/apache/sshd/server/SshServer winterx/ssh/SshSettings winterx/tweaks/TweakSettings')
            for primary, runtime, expected in ((native, helper, True), (b'old', helper, False),
                    (native, helper.replace(b'winterx-ssh-info-v1', b'old-info'), False),
                    (native, helper.replace(b'winterx/ssh/AppCommand', b'old-command'), False)):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes.dex', primary); archive.writestr('classes3.dex', runtime)
                self.assertEqual(tweak_runtime.ssh_actions_supported_by(apk), expected)

    def test_prompt_requires_the_real_prompt_abi_and_guarded_app_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / 'engine.apk'
            from unittest.mock import patch
            for helper, actions, expected in ((b'winterx-ssh-prompt-v1 winterx/ssh/BuiltinShell', True, True),
                    (b'winterx/ssh/BuiltinShell', True, False), (b'winterx-ssh-prompt-v1', True, False),
                    (b'winterx-ssh-prompt-v1 winterx/ssh/BuiltinShell', False, False)):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes3.dex', helper)
                with patch.object(tweak_runtime, 'ssh_actions_supported_by', return_value=actions):
                    self.assertEqual(tweak_runtime.ssh_prompt_supported_by(apk), expected)


if __name__ == '__main__':
    unittest.main()
