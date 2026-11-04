from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1] / 'patches/icon_positions'
sys.path.insert(0, str(HERE))
import patch_dockin
from patch_smali import method, replace_once


def smali(signature, body):
    return signature + '\n' + body + '\n.end method\n'


def fixture():
    return {
        'smali/x1.1/i1.1.smali': (
            smali('.method public final f0(I)LM1/b;', '    .locals 4\n    return-object v0') +
            smali('.method public final o1(FF)LE1/A0;', '    .locals 10\n    :cond_5\n    return-object v0') +
            smali('.method public final I(FF)Ljava/lang/String;', '    .locals 7\n    :cond_1\n    return-object v0') +
             smali('.method public final a6(J)Z', '    .locals 18\n    const/4 v5, 0x4\n    return v0') +
             smali('.method public final a0()LE1/q6;', '    .locals 125\n    invoke-direct {v1, v0, v8}, LE1/F1;-><init>(Ljava/util/ArrayList;Ljava/util/ArrayList;)V\n    return-object v0') +
             smali('.method public static S2(Lx1/i1;LE1/a;IIZZI)V', '    .locals 19\n    iget v13, v2, LE1/i6;->e:I\n    return-void') +
             smali('.method public final R2(LE1/A0;LE1/a;)V', '    .locals 21\n' + '    iget v15, v5, LE1/i6;->e:I\n' * 3 + '    return-void') +
             smali('.method public final N(Ljava/lang/String;Z)Z', '    .locals 18\n    iget v8, v2, LE1/i6;->e:I\n    return v0') +
            smali('.method public final untouched()I', '    .locals 1\n    const/4 v5, 0x4\n    return v0')),
        patch_dockin.MODEL: smali('.method public static R(LE1/i2;LE1/i2;Ljava/util/LinkedHashMap;I)LE1/i2;',
                                  '    .locals 20\n    const/4 v5, 0x4\n    return-object v0'),
        patch_dockin.DOCK_RENDER: smali('.method public static e(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;Ljava/util/concurrent/ConcurrentHashMap;Landroid/graphics/Bitmap;Ljava/util/Map;LI1/I0;Ljava/util/Map;)V',
                                        '    .locals 30\n    iget v0, v7, LE1/i6;->j:I\n    :goto_b\n    return-void'),
        'smali/I1/h0.1.smali': smali('.method public static p(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;LI1/I0;Ljava/util/Map;Ljava/util/Map;FFF)V',
                                    '    .locals 30\n    invoke-static/range {v0 .. v6}, LI1/h0;->L(Landroid/graphics/Canvas;Landroid/graphics/Paint;Ljava/util/Map;Landroid/graphics/Bitmap;IIF)V\n'
                                    '    invoke-static/range {v0 .. v12}, LI1/h0;->E(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/i6;LI1/I0;Ljava/util/Map;Landroid/graphics/Bitmap;Ljava/lang/String;IIZZLI1/Z;Ljava/lang/String;)V\n    return-void') +
            smali('.method public final r(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;LA/o;LE1/G1;ZF)V', '    .locals 36\n    return-void'),
    }


class DockInPatchTests(unittest.TestCase):
    def test_hooks_are_scoped_and_both_render_paths_restore_canvas(self):
        contents = fixture()
        untouched = smali('.method public final untouched()I', '    .locals 1\n    const/4 v5, 0x4\n    return v0')
        patch_dockin.apply(contents, method, replace_once)
        self.assertIn(untouched, contents['smali/x1.1/i1.1.smali'])
        self.assertIn('normalizeCapacity', contents[patch_dockin.MODEL])
        self.assertIn('editCapacity', contents['smali/x1.1/i1.1.smali'])
        self.assertEqual(contents[patch_dockin.DOCK_RENDER].count('->beginLegacy('), 1)
        self.assertEqual(contents[patch_dockin.DOCK_RENDER].count('->endIcon('), 1)
        self.assertEqual(contents['smali/I1/h0.1.smali'].count('->beginNative('), 2)
        self.assertEqual(contents['smali/I1/h0.1.smali'].count('->endIcon('), 2)
        self.assertIn('.locals 34', contents['smali/I1/h0.1.smali'])
        self.assertEqual(contents['smali/I1/h0.1.smali'].count('.catchall'), 2)
        self.assertEqual(contents[patch_dockin.DOCK_RENDER].count('.catchall'), 1)
        self.assertIn('->winterxStockR(', contents['smali/I1/h0.1.smali'])
        self.assertIn('->frame(', contents['smali/x1.1/i1.1.smali'])
        self.assertEqual(contents['smali/x1.1/i1.1.smali'].count('->launchSize('), 5)
        self.assertNotIn('LE1/S1;', contents['smali/x1.1/i1.1.smali'])

    def test_changed_or_duplicate_capacity_anchor_is_rejected(self):
        for replacement in ('    const/4 v5, 0x5', '    const/4 v5, 0x4\n    const/4 v5, 0x4'):
            contents = fixture()
            contents[patch_dockin.MODEL] = contents[patch_dockin.MODEL].replace('    const/4 v5, 0x4', replacement)
            with self.assertRaisesRegex(ValueError, 'Expected one patch anchor'):
                patch_dockin.apply(contents, method, replace_once)

    def test_reapplying_is_rejected_not_duplicated(self):
        contents = fixture()
        patch_dockin.apply(contents, method, replace_once)
        with self.assertRaises(ValueError):
            patch_dockin.apply(contents, method, replace_once)

    def test_incomplete_renderer_signature_is_rejected(self):
        contents = fixture()
        contents[patch_dockin.DOCK_RENDER] = contents[patch_dockin.DOCK_RENDER].replace('    .locals 30', '    .locals 29')
        with self.assertRaises(ValueError):
                patch_dockin.apply(contents, method, replace_once)

    def test_missing_launch_anchor_is_rejected(self):
        contents = fixture()
        contents['smali/x1.1/i1.1.smali'] = contents['smali/x1.1/i1.1.smali'].replace('iget v13, v2, LE1/i6;->e:I', 'iget v13, v2, LE1/i6;->b:I')
        with self.assertRaisesRegex(ValueError, 'app-launch size anchors'):
            patch_dockin.apply(contents, method, replace_once)


if __name__ == '__main__':
    unittest.main()
