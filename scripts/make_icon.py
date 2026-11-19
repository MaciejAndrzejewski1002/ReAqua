import os
import sys

from PIL import Image, ImageDraw


def draw(size: int = 128) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 128.0
    d.ellipse([12 * s, 12 * s, 116 * s, 116 * s], fill=(31, 111, 139, 255))
    drop = [(64 * s, 22 * s), (88 * s, 62 * s), (92 * s, 78 * s), (86 * s, 92 * s), (74 * s, 102 * s),
            (64 * s, 105 * s), (54 * s, 102 * s), (42 * s, 92 * s), (36 * s, 78 * s), (40 * s, 62 * s)]
    d.polygon(drop, fill=(255, 255, 255, 255))
    d.ellipse([50 * s, 70 * s, 62 * s, 86 * s], fill=(153, 194, 77, 255))
    return img


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join("src", "reaqua", "icon.png")
    draw(64).save(target)
