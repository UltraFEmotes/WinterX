from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ruby_theme

class ThemeTests(unittest.TestCase):
    def test_red_bar_preserves_dimensions_and_alpha(self):
        asset = 'assets/ios6/uikit/UINavigationBarDefaultBackground.png'
        with zipfile.ZipFile(ROOT / 'Spring-0.8.1.apk') as apk:
            original = Image.open(BytesIO(apk.read(asset))).convert('RGBA')
        themed = Image.open(ROOT / 'themes/red/ios6/uikit/UINavigationBarDefaultBackground.png').convert('RGBA')
        self.assertEqual(original.size, themed.size)
        self.assertEqual(original.getchannel('A').tobytes(), themed.getchannel('A').tobytes())
        self.assertTrue(any(r > g and r > b for r, g, b, a in themed.getdata() if a))

    def test_stages_assets_in_expected_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            count = ruby_theme.stage(root)
            self.assertGreater(count, 0)
            expected = root / 'files/ruby/theme/ios6/uikit/UINavigationBarDefaultBackground.png'
            self.assertEqual(expected.read_bytes(), (ROOT / 'themes/red/ios6/uikit/UINavigationBarDefaultBackground.png').read_bytes())
    def test_custom_color_preserves_size_and_alpha(self):
        original = (ROOT / 'themes/red/ios6/uikit/UINavigationBarDefaultBackground.png').read_bytes()
        with Image.open(BytesIO(original)) as source:
            source = source.convert('RGBA')
        with Image.open(BytesIO(ruby_theme.recolor(original, '#2175D9'))) as result:
            result = result.convert('RGBA')
        self.assertEqual(source.size, result.size)
        self.assertEqual(source.getchannel('A').tobytes(), result.getchannel('A').tobytes())
        self.assertTrue(any(b > r and b > g for r, g, b, a in result.getdata() if a))
        with self.assertRaises(ValueError): ruby_theme.recolor(original, 'blue')

    def test_rejects_theme_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / 'files/ruby'; parent.mkdir(parents=True)
            (parent / 'theme').symlink_to(root)
            with self.assertRaises(ValueError): ruby_theme.stage(root)
