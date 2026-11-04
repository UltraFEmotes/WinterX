from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import animaper
class AnimaperTests(unittest.TestCase):
    def test_valid_modes_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for mode in animaper.MODES:
                self.assertTrue(animaper.set_mode(root,mode)['ok'])
                self.assertEqual((root/'files/ruby/animaper.mode').read_text().strip(),mode)
            with self.assertRaises(ValueError): animaper.set_mode(root,'../../nope')
    def test_engine_support_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk=Path(tmp)/'spring.apk'
            with zipfile.ZipFile(apk,'w') as z:
                z.writestr('classes.dex',b'old')
                z.writestr('classes3.dex',b'winterx/animaper/Animaper')
            self.assertFalse(animaper.supported_by(apk))
            with zipfile.ZipFile(apk,'w') as z:
                z.writestr('classes.dex',b'winterx/animaper/Animaper')
                z.writestr('classes3.dex',b'winterx/animaper/Animaper')
            self.assertTrue(animaper.supported_by(apk))
if __name__=='__main__': unittest.main()
