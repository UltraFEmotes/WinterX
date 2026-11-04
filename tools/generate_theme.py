#!/usr/bin/env python3
"""Generate local color-test resources from your own Spring APK."""
import argparse
from io import BytesIO
from pathlib import Path
import re
import zipfile
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]

def generate(apk, output):
    output = Path(output)
    if output.exists():
        raise ValueError('Output already exists; remove or rename it first')
    with zipfile.ZipFile(apk) as archive:
        names = [name for name in archive.namelist() if re.fullmatch(r'assets/ios[46]/uikit/UINavigationBar[^/]*\.png', name)]
        if not names:
            raise ValueError('No Spring navigation-bar resources found')
        for name in names:
            with Image.open(BytesIO(archive.read(name))) as source:
                image = source.convert('RGBA')
                result = ImageOps.colorize(ImageOps.grayscale(image), '#33000a', '#ffd6df').convert('RGBA')
                result.putalpha(image.getchannel('A'))
                target = output / Path(name).relative_to('assets')
                target.parent.mkdir(parents=True, exist_ok=True)
                result.save(target)
    print('Generated', len(names), 'local resources in', output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk')
    parser.add_argument('--output', default=ROOT / 'themes/red')
    args = parser.parse_args()
    generate(args.apk, args.output)
