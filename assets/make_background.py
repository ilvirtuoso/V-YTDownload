#!/usr/bin/env python3
"""Generate assets/background.png - pale lavender starfield wallpaper.

Recreates the reference artwork: muted periwinkle-gray sky, dense tiny
stars, a few bright sparkle stars with cross flares, faint diagonal
nebula wisps, and a pale planet limb rising in the bottom-left corner.
Deterministic (fixed seed) so it regenerates identically.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 1600, 900
BASE_TOP = (185, 186, 211)
BASE_BOT = (168, 169, 198)

rng = random.Random(20261012)


def vgrad():
    im = Image.new("RGB", (W, H))
    px = im.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(BASE_TOP[0] + (BASE_BOT[0] - BASE_TOP[0]) * t)
        g = int(BASE_TOP[1] + (BASE_BOT[1] - BASE_TOP[1]) * t)
        b = int(BASE_TOP[2] + (BASE_BOT[2] - BASE_TOP[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return im


def grain(im, amount=6):
    px = im.load()
    for _ in range(W * H // 40):
        x = rng.randrange(W)
        y = rng.randrange(H)
        r, g, b = px[x, y]
        d = rng.randint(-amount, amount)
        px[x, y] = (max(0, min(255, r + d)), max(0, min(255, g + d)),
                    max(0, min(255, b + d)))
    return im


def nebula_wisps(im):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # soft diagonal bands, like the reference's faint milky streaks
    for (x0, y0, x1, y1, wdt, alpha) in [
        (80, 640, 620, 900, 90, 26),
        (150, 600, 700, 880, 46, 30),
        (230, 660, 560, 900, 26, 34),
        (300, 120, 900, 300, 120, 12),
        (900, 700, 1500, 560, 100, 10),
    ]:
        d.line([x0, y0, x1, y1], fill=(235, 236, 245, alpha), width=wdt)
    layer = layer.filter(ImageFilter.GaussianBlur(28))
    im = im.convert("RGBA")
    im = Image.alpha_composite(im, layer)
    return im.convert("RGB")


def planet(im):
    # big pale sphere whose limb glows in the bottom-left corner
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy, R = -260, 1180, 640
    # body
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(206, 207, 224, 255))
    # soft inner shading (terminator on the lower-left)
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shade)
    ds.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(150, 151, 180, 70))
    shade = shade.filter(ImageFilter.GaussianBlur(60))
    layer = Image.alpha_composite(layer, shade)
    layer = layer.filter(ImageFilter.GaussianBlur(2))
    im = im.convert("RGBA")
    im = Image.alpha_composite(im, layer)
    # bright rim along the limb
    d2 = ImageDraw.Draw(im)
    for extra, alpha, width in [(0, 235, 5), (4, 150, 9), (10, 80, 16)]:
        d2.arc([cx - R - extra, cy - R - extra, cx + R + extra, cy + R + extra],
               start=262, end=332, fill=(245, 246, 252, alpha), width=width)
    im = im.filter(ImageFilter.GaussianBlur(1))
    return im.convert("RGB")


def sparkle(draw, x, y, r, alpha=255):
    # cross flare + soft core
    c = (255, 255, 255, alpha)
    draw.line([x - r * 3, y, x + r * 3, y], fill=c, width=max(1, r // 3))
    draw.line([x, y - r * 3, x, y + r * 3], fill=c, width=max(1, r // 3))
    draw.line([x - r * 2, y - r * 2, x + r * 2, y + r * 2],
              fill=(255, 255, 255, alpha // 3), width=1)
    draw.line([x - r * 2, y + r * 2, x + r * 2, y - r * 2],
              fill=(255, 255, 255, alpha // 3), width=1)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=c)


def stars(im):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # dense tiny field
    for _ in range(1500):
        x = rng.randrange(W)
        y = rng.randrange(H)
        a = rng.randint(40, 130)
        r = 1 if rng.random() < 0.85 else 2
        v = rng.randint(225, 255)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(v, v, 255, a))
    # medium stars
    for _ in range(70):
        x = rng.randrange(W)
        y = rng.randrange(H)
        r = rng.randint(2, 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 200))
    # hero sparkles with flares (a few, like the reference)
    for _ in range(11):
        x = rng.randrange(60, W - 60)
        y = rng.randrange(40, H - 120)
        sparkle(d, x, y, rng.randint(3, 6), rng.randint(170, 255))
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    im = im.convert("RGBA")
    im = Image.alpha_composite(im, layer)
    return im.convert("RGB")


def main():
    im = vgrad()
    im = nebula_wisps(im)
    im = planet(im)
    im = stars(im)
    im = grain(im)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "background.png")
    im.save(out, "PNG")
    print("wrote", out, im.size)


if __name__ == "__main__":
    main()
