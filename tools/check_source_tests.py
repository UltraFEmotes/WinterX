#!/usr/bin/env python3
"""Run the source-only Python suite; explicitly omit SDK/APK/generated-theme integration fixtures."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_INPUTS = {'test_ruby_theme': 'original Spring APK and locally generated theme',
                   'test_sapp_lifecycle': 'separately obtained Spring SDK r10'}


def main():
    print('Source-only suite; full discovery and packaged/live checks remain separate.', flush=True)
    for module, reason in EXTERNAL_INPUTS.items():
        print('Omitting ' + module + ': requires ' + reason, flush=True)
    suite = unittest.TestSuite()
    for path in sorted((ROOT / 'tests').glob('test_*.py')):
        if path.stem not in EXTERNAL_INPUTS:
            suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=path.name))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__': raise SystemExit(main())
