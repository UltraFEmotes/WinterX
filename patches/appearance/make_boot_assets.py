#!/usr/bin/env python3
"""Make the WinterX snowflake splash assets used by the Spring 0.8.1 patch."""
from math import cos, sin, pi
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
scale = 2
image = Image.new('RGBA', (768 * scale, 768 * scale), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
center = (384 * scale, 300 * scale)
white = (238, 247, 255, 255)

def line(points, width):
    draw.line([(round(x * scale), round(y * scale)) for x, y in points], fill=white, width=width * scale, joint='curve')
    for x, y in (points[0], points[-1]):
        radius = width * scale / 2
        draw.ellipse((x * scale-radius, y * scale-radius, x * scale+radius, y * scale+radius), fill=white)

for n in range(6):
    angle = pi * n / 3 - pi / 2
    unit = (cos(angle), sin(angle))
    x0, y0 = 384, 300
    end = (x0 + unit[0]*145, y0 + unit[1]*145)
    line([(x0, y0), end], 15)
    for sign in (-1, 1):
        base = (x0 + unit[0]*94, y0 + unit[1]*94)
        a = angle + sign*pi/3
        line([base, (base[0]+cos(a)*47, base[1]+sin(a)*47)], 12)
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 65 * scale)
small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 23 * scale)
draw.text((384*scale, 500*scale), 'WinterX', font=font, fill=white, anchor='mm')
draw.text((384*scale, 555*scale), 'by WeirdMM', font=small, fill=(190, 210, 231, 255), anchor='mm')
image = image.resize((768,768), Image.Resampling.LANCZOS)
image.save(HERE / 'winterx-boot.webp', 'WEBP', lossless=True)
