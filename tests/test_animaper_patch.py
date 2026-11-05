from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches/icon_positions'))
import patch_animaper
from patch_smali import method, replace_once


def fixture():
    return {patch_animaper.RENDER: (
        patch_animaper.K + '\n    .locals 33\n'
        '    check-cast v3, LI1/b0;\n\n    .line 12\n'
        '    iget v9, v3, LI1/b0;->b:I\n'
        '    const-wide/16 v4, 0x0\n    return-void\n.end method\n' +
        patch_animaper.DRAW + '\n    .locals 18\n    return-void\n.end method\n')}


class AnimaperPatchTests(unittest.TestCase):
    def test_native_delegation_and_cleanup_cover_normal_and_exception_paths(self):
        values = fixture()
        patch_animaper.apply(values, method, replace_once)
        result = values[patch_animaper.RENDER]
        self.assertEqual(result.count(patch_animaper.K), 1)
        self.assertEqual(result.count(patch_animaper.DRAW), 1)
        self.assertIn('invoke-static/range {p0 .. p15}, LI1/h0;->winterxStockK(', result)
        self.assertIn('invoke-static/range {p0 .. p12}, LI1/h0;->winterxStockArtwork(', result)
        self.assertEqual(result.count('->endFrame(Ljava/lang/Object;)V'), 2)
        self.assertEqual(result.count('->endIcon(Landroid/graphics/Canvas;I)V'), 2)
        self.assertEqual(result.count('.catchall {'), 2)
        self.assertEqual(result.count('    throw v1'), 2)
        self.assertIn('move-object/from16 v0, p15\n    move-wide/from16 v1, p1', result)
        self.assertIn('move-object/from16 v3, p7\n    move-object/from16 v4, p8', result)
        self.assertIn('invoke-static {p0, p2, p7, p8}', result)
        self.assertIn('iget v9, v3, LI1/b0;->b:I', result)
        for forbidden in ('->clear()', '->recycle()', '->setPixels(', 'Ljava/lang/reflect/', '->save(Ljava/io/File;'):
            self.assertNotIn(forbidden, result)

    def test_missing_duplicate_or_changed_native_registers_fail_atomically(self):
        changes = (
            ('    .locals 33', '    .locals 32'),
            ('    .locals 18', '    .locals 17'),
            ('check-cast v3, LI1/b0;', 'check-cast v4, LI1/b0;'),
            ('iget v9, v3, LI1/b0;->b:I', 'iget v8, v3, LI1/b0;->b:I'),
            ('    check-cast v3, LI1/b0;', '    check-cast v3, LI1/b0;\n    check-cast v3, LI1/b0;'),
            (patch_animaper.DRAW, patch_animaper.DRAW.replace('public', 'private')),
        )
        for old, new in changes:
            with self.subTest(anchor=old):
                values = fixture()
                values[patch_animaper.RENDER] = values[patch_animaper.RENDER].replace(old, new)
                original = dict(values)
                with self.assertRaises(ValueError):
                    patch_animaper.apply(values, method, replace_once)
                self.assertEqual(values, original)

    def test_line_metadata_is_not_a_required_anchor_and_double_patch_is_rejected(self):
        values = fixture()
        values[patch_animaper.RENDER] = values[patch_animaper.RENDER].replace('    .line 12\n', '')
        patch_animaper.apply(values, method, replace_once)
        original = dict(values)
        with self.assertRaises(ValueError):
            patch_animaper.apply(values, method, replace_once)
        self.assertEqual(values, original)


if __name__ == '__main__':
    unittest.main()
