from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'patches/icon_positions')); sys.path.insert(0, str(ROOT / 'tools'))
import patch_snowy
from patch_smali import method, replace_once
import tweak_runtime


class SnowyPatchTests(unittest.TestCase):
    def fixture(self):
        text = '\n'.join(signature + '\n    .locals ' + str(locals) + '\n    return-void\n.end method\n'
                         for signature, locals in ((patch_snowy.ICON, 4), (patch_snowy.LABEL, 22), (patch_snowy.DRAW, 18), (patch_snowy.EDIT, 36)))
        return text + patch_snowy.CONTENT + '\n    .locals 31\n' + (
            '    iget-object v4, v1, LE1/a;->c:Ljava/lang/String;\n\n    .line 389\n'
            '    move-object/from16 v11, p5\n\n    .line 390\n'
            '    invoke-virtual {v11, v4}, Ljava/util/concurrent/ConcurrentHashMap;->get(Ljava/lang/Object;)Ljava/lang/Object;\n'
            '    move-result-object v4\n    move-object v6, v4\n    return-void\n.end method\n')

    def test_hooks_keep_stock_fallback_and_bypass_not_destroy_precomposed_cache(self):
        values = {patch_snowy.RENDER: self.fixture()}; patch_snowy.apply(values, method, replace_once)
        result = values[patch_snowy.RENDER]
        self.assertEqual(result.count(patch_snowy.ICON), 1); self.assertIn('->winterxStockIcon(', result)
        self.assertIn('hiddenLabels()Z', result); self.assertIn('->artwork(', result); self.assertIn('move-object/16 p7, v0', result)
        self.assertIn('invoke-static {v1, v4, v6, v11}, LI1/h0;->c(', result)
        self.assertNotIn('->clear()', result); self.assertNotIn('->setPixels(', result)
        for anchor in (patch_snowy.LABEL, patch_snowy.DRAW, patch_snowy.EDIT, patch_snowy.CONTENT):
            values = {patch_snowy.RENDER: self.fixture().replace(anchor, anchor.replace('public', 'private'))}; before = dict(values)
            with self.assertRaises(ValueError): patch_snowy.apply(values, method, replace_once)
            self.assertEqual(values, before)

    def test_folder_lookup_requires_the_exact_native_registers(self):
        for old, new in (('v11, p5', 'v11, p6'), ('{v11, v4}', '{v11, v5}')):
            values = {patch_snowy.RENDER: self.fixture().replace(old, new)}; before = dict(values)
            with self.assertRaises(ValueError): patch_snowy.apply(values, method, replace_once)
            self.assertEqual(values, before)

    def test_helpers_without_packaged_renderer_hooks_and_alpha8_are_not_capable(self):
        with tempfile.TemporaryDirectory() as name:
            apk = Path(name) / 'fixture.apk'
            helpers = b'snowyhome-render-v1 winterx/snowy/SnowySettings'
            for primary, expected in ((b'winterx/layout/DockIn', False), (b'winterx/snowy/SnowyHome winterxStockIcon hiddenLabels artwork', True)):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes3.dex', helpers); archive.writestr('classes.dex', primary)
                self.assertEqual(tweak_runtime.snowyhome_supported_by(apk), expected)
