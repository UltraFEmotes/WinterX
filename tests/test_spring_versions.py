"""Supported Spring versions: the name translator, the manifest field and the register liveness check."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_package
import smali_live
import spring_map

MAP = {'classes': {'x1/i1': 'r1/E1', 'E1/o6': 'y1/a7', 'E1/a7': 'q/q'},
       'methods': {'Lx1/i1;->H1(Ljava/lang/String;)V': 'Lr1/E1;->c2(Ljava/lang/String;)V'},
       'fields': {'Lx1/i1;->Y:LE1/o6;': 'Lr1/E1;->X:Ly1/a7;'}}


class TranslatorTests(unittest.TestCase):
    def setUp(self): self.t = spring_map.Translator(MAP)

    def test_references_are_renamed_once(self):
        # E1/o6 -> y1/a7; an *old* class also called y1/a7 must not be renamed again.
        self.assertEqual(self.t.text('    iget-object v0, v1, Lx1/i1;->Y:LE1/o6;'), '    iget-object v0, v1, Lr1/E1;->X:Ly1/a7;')
        self.assertEqual(self.t.text('    invoke-virtual {v1, v0}, Lx1/i1;->H1(Ljava/lang/String;)V'),
                         '    invoke-virtual {v1, v0}, Lr1/E1;->c2(Ljava/lang/String;)V')

    def test_hook_signatures_in_strings_and_constants(self):
        self.assertEqual(self.t.text('    const-string v0, "Lx1/i1;->H1(Ljava/lang/String;)V"'),
                         '    const-string v0, "Lr1/E1;->c2(Ljava/lang/String;)V"')
        smali = ('.class public final Lme/Tweak;\n.super Ljava/lang/Object;\n'
                 '.field static final TYPE:Ljava/lang/String; = "Lx1/i1;->H1(Ljava/lang/String;)V"\n')
        self.assertIn('= "Lr1/E1;->c2(Ljava/lang/String;)V"', self.t.smali(smali))

    def test_declarations_of_a_renamed_class(self):
        out = self.t.smali('.class public final Lx1/i1;\n.super Ljava/lang/Object;\n.field public Y:LE1/o6;\n'
                           '.method public final H1(Ljava/lang/String;)V\n    return-void\n.end method')
        self.assertIn('.class public final Lr1/E1;', out)
        self.assertIn('.field public X:Ly1/a7;', out)
        self.assertIn('.method public final c2(Ljava/lang/String;)V', out)

    def test_unmapped_obfuscated_member_is_reported(self):
        self.t.text('    invoke-virtual {v0}, Lx1/i1;->Q2()V')
        self.assertIn('Lx1/i1;->Q2()V', self.t.missing)


class ManifestTests(unittest.TestCase):
    def test_versions_need_their_own_code(self):
        self.assertEqual(native_package.version_code({}), [])
        self.assertEqual(native_package.version_code({'spring': ['0.8.1']}), [])
        self.assertEqual(native_package.version_code({'spring': ['0.8.1', '0.9-preview1']}),
                         ['code/0.9-preview1/classes.dex', 'code/0.9-preview1/classes.jar'])

    def test_invalid_version_lists(self):
        for bad in ([], ['0.8.1', '0.8.1'], ['../0.9'], ['0.9 Preview 1'], '0.8.1', [1]):
            with self.assertRaises(ValueError): native_package.version_code({'spring': bad})


class LivenessTests(unittest.TestCase):
    BODY = ('.method public final f()V\n    .locals 3\n    :start\n'
            '    const/4 v0, 0x1\n    add-int/2addr v1, v0\n    if-eqz v1, :done\n    move v2, v1\n'
            '    :done\n    return-void\n.end method')

    def test_written_before_read_is_dead(self):
        lines, labels = smali_live.parse(self.BODY)
        self.assertEqual(smali_live.dead(self.BODY, labels[':start'] + 1, ['v0', 'v1', 'v2']), {'v0', 'v2'})


class JailbreakVersionTests(unittest.TestCase):
    """The WinterX app's request names a Spring version; the bridge starts that version's core."""
    def setUp(self):
        import tempfile, ruby_bridge, mac_core
        self.bridge, self.core = ruby_bridge, mac_core
        self.dir = Path(tempfile.mkdtemp()); (self.dir / 'requests').mkdir(); (self.dir / 'results').mkdir()
        self.switched = []
        self.saved = mac_core.switch, mac_core.jailbreak.STATE
        mac_core.switch = lambda version: self.switched.append(version) or {'ok': True, 'message': 'Successfully Jailbroken', 'springVersion': version}
        mac_core.jailbreak.STATE = self.dir / 'state'; mac_core.jailbreak.STATE.mkdir()

    def tearDown(self):
        import shutil
        self.core.switch, self.core.jailbreak.STATE = self.saved
        shutil.rmtree(self.dir)

    def request(self, inbox=None, **record):
        record = {'id': '1-2', **record}
        path = self.dir / 'requests/1-2.json'; path.write_text(json.dumps(record))
        self.bridge.process_jailbreak(path, self.dir, inbox)
        return json.loads((self.dir / 'results/1-2.json').read_text())

    def test_preview_starts_its_core(self):
        reply = self.request(action='jailbreak', version='0.9-preview1')
        self.assertEqual((reply['ok'], reply['action'], self.switched), (True, 'jailbreak', ['0.9-preview1']))

    def test_prepared_081_core_is_started_the_same_way(self):
        (self.core.jailbreak.STATE / 'core-plan.json').write_text('{}')
        self.assertTrue(self.request(action='jailbreak', version='0.8.1')['ok'])
        self.assertEqual(self.switched, ['0.8.1'])

    def test_unknown_version_is_refused(self):
        reply = self.request(action='jailbreak', version='0.9')
        self.assertFalse(reply['ok']); self.assertIn('does not support', reply['message']); self.assertEqual(self.switched, [])

    def test_other_versions_cannot_install_ruby(self):
        self.assertFalse(self.request(action='install_ruby')['ok'])

    def test_every_supported_version_has_a_data_folder(self):
        self.assertEqual(set(self.bridge.SPRING_FOLDERS), set(self.core.SPRING_SOURCES.values()))


if __name__ == '__main__': unittest.main()
