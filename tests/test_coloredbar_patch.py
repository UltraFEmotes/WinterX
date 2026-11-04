import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coloredbar_patch', ROOT / 'patches/coloredbar.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class ColoredBarPatchTests(unittest.TestCase):
    def test_settings_saves_key_and_tints_both_lazy_loader_returns(self):
        stock = ('.method public final get(Ljava/lang/Object;)Ljava/lang/Object;\n'
                 '    .locals 2\n    move-result-object p1\n    return-object v1\n'
                 '    move-object p1, v1\n    return-object p1\n.end method\n')
        result = patch.patch_settings(stock)
        self.assertIn('    .locals 4\n    move-object v2, p1', result)
        self.assertEqual(result.count('->settingsAsset('), 2)
        self.assertIn('    move-result-object v1\n    return-object v1', result)
        self.assertIn('    move-result-object p1\n    return-object p1', result)
        with self.assertRaises(ValueError): patch.patch_settings(result)
        with self.assertRaises(ValueError): patch.patch_settings(stock.replace('return-object v1', 'return-object v0'))

    def test_appstore_wraps_deferred_map_with_explicit_app_identity(self):
        stock = ('.method private final d(Ljava/lang/Object;)Ljava/lang/Object;\n'
                 '    .locals 95\n    iget-object v8, v2, LI1/T0;->p:Ljava/util/Map;\n'
                 '    const-string v2, "ios6/apps/appstore/NavBar.png"\n.end method\n')
        result = patch.patch_appstore(stock)
        self.assertIn('    .locals 97\n    const-string v96, "appstore"', result)
        self.assertIn('invoke-static/range {v95 .. v96}', result)
        self.assertIn('move-result-object v8', result)
        self.assertNotIn('iput-object', result, 'shared renderer map was overwritten')
        with self.assertRaises(ValueError): patch.patch_appstore(result)
        with self.assertRaises(ValueError): patch.patch_appstore(stock.replace('NavBar.png', 'Other.png'))

    def test_dispatchers_keep_rendered_app_identity_for_transition_frames(self):
        stock = ''
        for name, suffix, count in (('g', '', 14), ('m', 'Z', 18)):
            stock += ('.method public final ' + name + '(Landroid/graphics/Canvas;LE1/q6;LI1/I0;Ljava/lang/String;J' + suffix + ')V\n'
                      '    .locals 36\n' + '    iget-object v8, v9, LI1/T0;->p:Ljava/util/Map;\n' * count + '.end method\n')
        result = patch.patch(stock)
        self.assertEqual(result.count('move-object/16 v37, p4'), 2)
        self.assertEqual(result.count('RubyAppearance;->assets('), 32)
        self.assertEqual(result.count('ColoredBar;->assets('), 32)
        self.assertNotIn('iput-object', result)
        with self.assertRaises(ValueError): patch.patch(stock.replace('->p:Ljava/util/Map;', '->p:Ljava/util/HashMap;', 1))


if __name__ == '__main__': unittest.main()
