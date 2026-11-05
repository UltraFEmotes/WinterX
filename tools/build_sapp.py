#!/usr/bin/env python3
"""Build a .sapp with the exact reviewed script bytes used by WinterX's trusted-app pins."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(source, output, sdk=ROOT / 'SpringSDK-r10/tools/spring_pack.py'):
    source = Path(source).resolve(strict=True); output = Path(output)
    if output.exists(): raise ValueError('Choose a new output file; the existing app archive is preserved')
    spec = importlib.util.spec_from_file_location('spring_pack', sdk)
    pack = importlib.util.module_from_spec(spec); spec.loader.exec_module(pack)
    pack.check_dir(str(source))
    script = (source / 'main.js').read_bytes()
    with tempfile.TemporaryDirectory(prefix='winterx-sapp-') as name:
        temporary = Path(name) / 'sdk.sapp'
        pack.pack(str(source), str(temporary))
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(temporary) as before, zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as after:
            for info in before.infolist():
                after.writestr(info, script if info.filename == 'main.js' else before.read(info.filename))
    pack.check_zip(str(output))
    return {'file': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'script_sha256': hashlib.sha256(script).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--sdk', type=Path, default=ROOT / 'SpringSDK-r10/tools/spring_pack.py')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.sdk), indent=2))
