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
        return '\n'.join(signature + '\n    .locals ' + str(locals) + '\n    return-void\n.end method\n'
                         for signature, locals in ((patch_snowy.ICON, 4), (patch_snowy.LABEL, 22), (patch_snowy.DRAW, 18), (patch_snowy.EDIT, 36)))

    def test_hooks_keep_stock_fallback_and_bypass_not_destroy_precomposed_cache(self):
        values = {patch_snowy.RENDER: self.fixture()}; patch_snowy.apply(values, method, replace_once)
        result = values[patch_snowy.RENDER]
        self.assertEqual(result.count(patch_snowy.ICON), 1); self.assertIn('->winterxStockIcon(', result)
        self.assertIn('hiddenLabels()Z', result); self.assertIn('->artwork(', result); self.assertIn('move-object/16 p7, v0', result)
        self.assertNotIn('->clear()', result); self.assertNotIn('->setPixels(', result)
        for anchor in (patch_snowy.LABEL, patch_snowy.DRAW, patch_snowy.EDIT):
            values = {patch_snowy.RENDER: self.fixture().replace(anchor, anchor.replace('public', 'private'))}; before = dict(values)
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
