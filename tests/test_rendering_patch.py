from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches/icon_positions'))
import patch_rendering as p
from patch_smali import method, replace_once


def smali(signature, locals_count, body='    return-void'):
    return signature + '\n    .locals ' + str(locals_count) + '\n' + body + '\n.end method\n'


def fixture():
    tiles = (
        ('.method public m(LE1/i6;LI1/I0;Ljava/util/Map;Landroid/graphics/Bitmap;Ljava/lang/String;Ljava/lang/String;ZZLjava/lang/String;)LI1/e0;', 22),
        ('.method public i(LE1/i6;LI1/I0;LE1/q6;Ljava/util/Map;LZ1/l;)LC1/D1;', 16),
        ('.method public v(LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Paint;)V', 19),
    )
    layers = (
        ('.method public final c(LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Bitmap;)Z', 17),
        ('.method public static d(LE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Landroid/graphics/Bitmap;)Ljava/util/List;', 19),
        ('.method public final b(ILE1/q6;LI1/I0;Ljava/util/concurrent/ConcurrentHashMap;Ljava/util/Map;Landroid/graphics/Bitmap;LI1/X;)V', 15),
    )
    scene = '.method public static o(LI1/T0;Landroid/graphics/Canvas;LE1/q6;LI1/I0;FFLI1/d0;LE1/S1;FFLjava/lang/Long;JFI)Z'
    return {
        p.RENDER: smali(p.K, 33) + smali(p.FAST, 33, '    const/4 v0, 0x1\n    return v0') +
            smali(p.UPPER, 17, '    invoke-virtual {v0, v3}, LE1/q6;->d(I)Ljava/util/List;\n    return-void') +
            smali(p.LOWER, 18, '    invoke-virtual {v3, v1}, LE1/q6;->d(I)Ljava/util/List;\n    return-void'),
        p.GEOMETRY: smali(p.FOLDER, 17, '    invoke-virtual {v0, v6}, LE1/q6;->d(I)Ljava/util/List;\n    return-object v0'),
        p.TILES: ''.join(smali(signature, count, '    const-string v0, "native-producer"\n    return-void') for signature, count in tiles),
        p.LAYERS: ''.join(smali(signature, count, '    const-string v0, "retained-layer"\n    return-void') for signature, count in layers),
        p.SCENE: smali(scene, 33, '    const-string v3, "full-native-fallback"\n    iget-object v4, v0, LI1/T0;->Z:LA/o;\n    const/4 v0, 0x1\n    return v0') +
            smali('.method public final P(LE1/q6;)V', 14, '    iget-object v0, p1, LE1/q6;->f0:LE1/U1;\n'
                '    if-eqz v0, :cond_0\n    iget-object v0, v0, LE1/U1;->h:Ljava/lang/String;\n'
                '    iput-object v0, p0, LI1/T0;->G:Ljava/lang/String;\n    return-void\n'
                '    :cond_0\n    invoke-virtual {p1}, LE1/q6;->b()I\n    return-void'),
        p.QUEUED: smali('.method public final run()V', 19, '    const/4 v2, 0x0\n'
            '    iput-boolean v2, v0, LI1/T0;->R:Z\n    iget-object v2, v0, LI1/T0;->Q:LE1/q6;\n    return-void'),
    }


class RenderingPatchTests(unittest.TestCase):
    def test_both_cache_consumers_and_producers_are_gated_without_clearing(self):
        values = fixture()
        p.apply(values, method, replace_once)
        text = '\n'.join(values.values())
        self.assertEqual(text.count('->tilesAllowed()Z'), 4)
        self.assertEqual(text.count('->folderLayersAllowed()Z'), 5)
        self.assertEqual(text.count('->tiles(LA/o;)LA/o;'), 2)
        self.assertIn('move-object/from16 v0, p9', values[p.RENDER])
        self.assertNotIn('move-object/from16 v0, p8', values[p.RENDER])
        for signature in (' m(', ' i(', ' v('):
            method_body = values[p.TILES].split('.method public' + signature)[1].split('.end method')[0]
            self.assertLess(method_body.index('->tilesAllowed()Z'), method_body.index('native-producer'))
        for forbidden in ('->clear()', '->recycle()', '->setPixels(', '->remove(', 'freeme-slots', 'pages.json'):
            self.assertNotIn(forbidden, text)

    def test_sparse_folder_lists_are_resolved_before_filtering_without_reindexing(self):
        values = fixture()
        p.apply(values, method, replace_once)
        self.assertEqual('\n'.join(values.values()).count('->folderEntries(LE1/q6;)Ljava/util/List;'), 3)
        for path in (p.RENDER, p.GEOMETRY):
            self.assertNotIn('->d(I)Ljava/util/List;', values[path])
        self.assertNotIn('Ljava/util/Collections;->sort', '\n'.join(values.values()))

    def test_full_scene_fallback_and_open_folder_bookkeeping_are_preserved(self):
        values = fixture()
        p.apply(values, method, replace_once)
        body = values[p.SCENE]
        self.assertIn('full-native-fallback', body)
        self.assertIn('    const/4 v0, 0x1\n    return v0', body)
        self.assertLess(body.index('->G:Ljava/lang/String;'), body.index('->folderLayersAllowed()Z'))
        queued = values[p.QUEUED]
        self.assertLess(queued.index('->R:Z'), queued.index('->folderLayersAllowed()Z'))
        self.assertIn('    const/4 v2, 0x0\n    iput-object v2, v0, LI1/T0;->Q:LE1/q6;\n    return-void', queued)
        self.assertNotIn('LI1/Y;->', queued)

    def test_changed_native_anchors_and_second_application_are_rejected(self):
        changes = ((p.RENDER, '.locals 33', '.locals 32'),
                   (p.TILES, '.locals 22', '.locals 21'),
                   (p.GEOMETRY, '{v0, v6}', '{v0, v5}'),
                   (p.SCENE, 'iget-object v4, v0, LI1/T0;->Z', 'iget-object v5, v0, LI1/T0;->Z'),
                   (p.QUEUED, 'iput-boolean v2, v0, LI1/T0;->R', 'iput-boolean v3, v0, LI1/T0;->R'))
        for path, old, new in changes:
            with self.subTest(anchor=old):
                values = fixture()
                values[path] = values[path].replace(old, new)
                with self.assertRaises(ValueError):
                    p.apply(values, method, replace_once)
        values = fixture()
        p.apply(values, method, replace_once)
        with self.assertRaises(ValueError):
            p.apply(values, method, replace_once)


if __name__ == '__main__':
    unittest.main()
