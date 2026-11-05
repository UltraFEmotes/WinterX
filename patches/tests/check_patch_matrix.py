#!/usr/bin/env python3
"""Validate native patch composition/atomic rejection for all six optional flags against decoded stock."""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'patches/icon_positions'))
import patch_smali as native

FLAGS = ('ANIMAPER', 'TRUSTED_FILES', 'INBOX', 'SNOWYHOME', 'MESSAGEPLUS', 'SSH_ACTIONS')
PATHS = set((native.RENDER, native.CONTROLLER, native.SPRING, native.STATUS, native.FILES,
             native.SAPP_MANAGER, native.POINTER, native.patch_dockin.DOCK_RENDER, native.patch_dockin.MODEL)
            + native.patch_rendering.PATHS + native.patch_messageplus.PATHS + native.patch_actions.PATHS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path, help='Unmodified Spring 0.8.1 decoded input')
    parser.add_argument('--artifacts', type=Path, required=True, help='New report directory')
    args = parser.parse_args()
    stock = args.decoded.resolve(strict=True)
    report = args.artifacts.resolve()
    report.mkdir(parents=True, exist_ok=False)
    originals = {name: (stock / name).read_text() for name in PATHS}
    results = []
    with tempfile.TemporaryDirectory(prefix='winterx-patch-matrix-', dir=report) as name:
        base = Path(name)
        for path in PATHS:
            (base / path).parent.mkdir(parents=True, exist_ok=True)

        def restore():
            for path, value in originals.items():
                (base / path).write_text(value)

        def hashes():
            return {path: hashlib.sha256((base / path).read_bytes()).hexdigest() for path in PATHS}

        for bits in itertools.product((False, True), repeat=len(FLAGS)):
            flags = {key: value for key, value in zip(FLAGS, bits)}
            restore()
            with patch.dict(os.environ, {'WINTERX_BUILD_' + key: '1' if value else '0' for key, value in flags.items()}):
                native.apply(base)
            renderer = (base / native.RENDER).read_text()
            manager = (base / native.SAPP_MANAGER).read_text()
            launcher = (base / native.patch_actions.LAUNCHER).read_text()
            assert ('->beginFrame(' in renderer) == flags['ANIMAPER']
            assert ('->artwork(' in renderer) == flags['SNOWYHOME']
            assert ('->winterxStockIcon(' in renderer) == flags['SNOWYHOME']
            assert ('->start(LJ1/y;)V' in manager) == flags['INBOX']
            assert ('winterxInstallArchive(' in manager) == flags['SSH_ACTIONS']
            assert ('winterxSappManager(' in launcher) == flags['SSH_ACTIONS']
            assert renderer.count(native.patch_rendering.K) == 1
            assert renderer.count(native.patch_snowy.DRAW) == 1
            assert 'move-object/from16 v0, p9\n    invoke-static {v0}, Lwinterx/layout/RenderPolicy;->tiles' in renderer
            if flags['ANIMAPER']:
                for signature in ('Lwinterx/animaper/Animaper;->endFrame(Ljava/lang/Object;)V', 'Lwinterx/animaper/Animaper;->endIcon(Landroid/graphics/Canvas;I)V'):
                    assert renderer.count(signature) == 2
            results.append({'flags': flags, 'passed': True, 'patched_sha256': hashes()})

        mutations = (
            (native.RENDER, '    check-cast v3, LI1/b0;', '    check-cast v4, LI1/b0;'),
            (native.patch_actions.LAUNCHER, '.field private sappApps:LJ1/y;', '.field public sappApps:LJ1/y;'),
            (native.patch_actions.PACKAGE, '.method public final b(Ljava/io/File;LJ1/x;)LJ1/N;\n    .locals 17', '.method public final b(Ljava/io/File;LJ1/x;)LJ1/N;\n    .locals 16'),
            (native.patch_rendering.QUEUED, '    iput-boolean v2, v0, LI1/T0;->R:Z', '    iput-boolean v3, v0, LI1/T0;->R:Z'),
        )
        for path, old, new in mutations:
            restore()
            if path == native.RENDER:
                changed = native.method(originals[path], native.patch_rendering.K, lambda body: native.replace_once(body, old, new))
            else:
                changed = native.replace_once(originals[path], old, new)
            (base / path).write_text(changed)
            before = hashes()
            try:
                with patch.dict(os.environ, {'WINTERX_BUILD_' + key: '1' for key in FLAGS}):
                    native.apply(base)
            except ValueError:
                assert hashes() == before, 'Partial on-disk patch after a failed native anchor'
            else:
                raise AssertionError('Mutated native anchor accepted: ' + path)
    (report / 'report.json').write_text(json.dumps({'stock_sha256': {path: hashlib.sha256(value.encode()).hexdigest() for path, value in originals.items()},
        'results': results, 'atomic_rejections': len(mutations)}, indent=2) + '\n')
    print('64/64 optional native patch combinations and 4/4 atomic no-write rejection checks passed')


if __name__ == '__main__':
    main()
