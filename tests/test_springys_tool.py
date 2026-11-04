import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import springys
import springys_tool


class BuildTests(unittest.TestCase):
    def test_build_and_inspect_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'test.springys'
            result = springys_tool.build(ROOT / 'examples/settings-test', output)
            loaded, artwork = springys.inspect(output)
            self.assertEqual(result, loaded)
            self.assertEqual(result['hook'], 'test.settings')
            self.assertIn('assets/icon.png', artwork)
            with self.assertRaises(ValueError):
                springys_tool.build(ROOT / 'examples/settings-test', output)

    def test_reject_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'package'
            root.mkdir()
            (root / 'manifest.json').write_text(json.dumps({'icon': 'assets/../secret.png'}))
            with self.assertRaises(ValueError):
                springys_tool.build(root, Path(tmp) / 'out.springys')
            self.assertFalse((Path(tmp) / 'out.springys').exists())


if __name__ == '__main__':
    unittest.main()
