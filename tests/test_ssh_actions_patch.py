from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches/icon_positions'))
import patch_actions as p
from patch_smali import method, replace_once


def fixture():
    return {
        p.LAUNCHER: '.class public Lcom/guille/spring/LauncherActivity;\n.field private sappApps:LJ1/y;\n',
        p.MANAGER: '.class public LJ1/y;\n.field public final g:LJ1/P;\n.method public final g()V\n    .locals 21\n    return-void\n.end method\n',
        p.PACKAGE: '.method public final b(Ljava/io/File;LJ1/x;)LJ1/N;\n    .locals 17\n    return-object v0\n.end method\n',
    }


class SshActionsPatchTests(unittest.TestCase):
    def test_native_getter_and_single_archive_delegation_keep_native_installer_unchanged(self):
        values = fixture()
        before = dict(values)
        p.apply(values, method, replace_once)
        self.assertEqual(values[p.PACKAGE], before[p.PACKAGE])
        self.assertTrue(values[p.LAUNCHER].startswith(before[p.LAUNCHER]))
        self.assertTrue(values[p.MANAGER].startswith(before[p.MANAGER]))
        self.assertIn('winterxSappManager()LJ1/y;', values[p.LAUNCHER])
        self.assertIn('winterxInstallArchive(Ljava/io/File;)Ljava/lang/String;', values[p.MANAGER])
        self.assertIn('const/4 v2, 0x2', values[p.MANAGER])
        self.assertIn('LJ1/P;->b(Ljava/io/File;LJ1/x;)LJ1/N;', values[p.MANAGER])
        self.assertIn('LJ1/y;->g()V', values[p.MANAGER])
        for forbidden in ('->h()V', '->N(', 'onHomePressed', 'Ljava/lang/Runtime;', '/system/bin/sh', 'delete', 'sapps-inbox'):
            self.assertNotIn(forbidden, values[p.LAUNCHER] + values[p.MANAGER])

    def test_all_native_anchors_validate_before_any_in_memory_mutation(self):
        for path, old, new in ((p.LAUNCHER, '.field private sappApps:LJ1/y;', '.field public sappApps:LJ1/y;'),
                               (p.MANAGER, '.field public final g:LJ1/P;', '.field public final h:LJ1/P;'),
                               (p.MANAGER, '.method public final g()V', '.method public final G()V'),
                               (p.PACKAGE, '.locals 17', '.locals 16')):
            with self.subTest(anchor=old):
                values = fixture()
                values[path] = values[path].replace(old, new)
                before = dict(values)
                with self.assertRaises(ValueError):
                    p.apply(values, method, replace_once)
                self.assertEqual(values, before)
        values = fixture()
        p.apply(values, method, replace_once)
        before = dict(values)
        with self.assertRaises(ValueError):
            p.apply(values, method, replace_once)
        self.assertEqual(values, before)


if __name__ == '__main__':
    unittest.main()
