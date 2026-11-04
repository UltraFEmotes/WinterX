"""Stage WinterX's red navigation-bar theme in Spring's private data."""
from pathlib import Path
from io import BytesIO
import colorsys
import re
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def recolor(payload, color):
    """Retint a red bar asset while keeping its shading, size and alpha."""
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Color must be a six-digit hex value, such as #3478C8')
    from PIL import Image
    selected = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, saturation, value = colorsys.rgb_to_hsv(*selected)
    with Image.open(BytesIO(payload)) as image:
        image = image.convert('RGBA')
        pixels = []
        for r, g, b, a in image.getdata():
            old_h, old_s, old_v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            # Retain the source asset's highlight and shadow ratios.
            rr, gg, bb = colorsys.hsv_to_rgb(hue, saturation * old_s, old_v * value)
            pixels.append((round(rr * 255), round(gg * 255), round(bb * 255), a))
        image.putdata(pixels)
        output = BytesIO()
        image.save(output, format='PNG')
        return output.getvalue()


def stage(data, source=ROOT / 'themes/red', color=None):
    source = Path(source).resolve(strict=True)
    target = Path(data) / 'files/ruby/theme'
    if target.is_symlink():
        raise ValueError('Theme directory is a symlink')
    paths = sorted(source.glob('ios*/uikit/UINavigationBar*.png'))
    if not paths:
        raise ValueError('WinterX navigation-bar theme assets are missing')
    for path in paths:
        relative = path.relative_to(source)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError('Invalid theme asset')
        destination = target / relative
        for part in (target, target / relative.parts[0], target / relative.parts[0] / relative.parts[1]):
            if part.is_symlink() or (part.exists() and not part.is_dir()):
                raise ValueError('Unexpected theme directory')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink():
            raise ValueError('Unexpected theme asset symlink')
        fd, temporary = tempfile.mkstemp(prefix='.winterx-', dir=destination.parent)
        try:
            with os.fdopen(fd, 'wb') as out:
                payload = path.read_bytes()
                out.write(recolor(payload, color) if color is not None else payload)
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return len(paths)
