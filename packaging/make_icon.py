"""Draw the app icon (a sun over a map grid; no game art) as packaging/icon.icns.

    python3 packaging/make_icon.py
"""

import math
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))


def draw(size):
    s = size / 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40 * s, 40 * s, 984 * s, 984 * s], radius=200 * s, fill=(24, 36, 70, 255))
    for i in range(1, 8):  # the map grid
        t = 40 * s + i * 118 * s
        d.line([(t, 120 * s), (t, 904 * s)], fill=(60, 90, 150, 255), width=max(1, int(6 * s)))
        d.line([(120 * s, t), (904 * s, t)], fill=(60, 90, 150, 255), width=max(1, int(6 * s)))
    cx, cy, r = 512 * s, 470 * s, 190 * s
    for k in range(12):  # rays
        a = k * math.pi / 6
        p = [(cx + math.cos(a - 0.13) * r * 1.15, cy + math.sin(a - 0.13) * r * 1.15),
             (cx + math.cos(a) * r * 1.75, cy + math.sin(a) * r * 1.75),
             (cx + math.cos(a + 0.13) * r * 1.15, cy + math.sin(a + 0.13) * r * 1.15)]
        d.polygon(p, fill=(240, 180, 40, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 205, 60, 255), outline=(255, 235, 150, 255), width=max(1, int(10 * s)))
    d.rounded_rectangle([250 * s, 780 * s, 774 * s, 880 * s], radius=30 * s, fill=(96, 180, 90, 255))
    return img


def main():
    tmp = tempfile.mkdtemp()
    iconset = os.path.join(tmp, "icon.iconset")
    os.makedirs(iconset)
    for px in (16, 32, 128, 256, 512):
        draw(px).save(os.path.join(iconset, f"icon_{px}x{px}.png"))
        draw(px * 2).save(os.path.join(iconset, f"icon_{px}x{px}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(HERE, "icon.icns")], check=True)
    draw(512).save(os.path.join(HERE, "icon.png"))
    shutil.rmtree(tmp)
    print("packaging/icon.icns")


if __name__ == "__main__":
    main()
