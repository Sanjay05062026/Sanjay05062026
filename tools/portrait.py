"""Turns a transparent-background photo cutout into a halftone dot grid (needs Pillow + numpy).
Only used when you run `python tools/build.py --portrait your-cutout.png`."""
from __future__ import annotations


def sample(path: str, grid: int = 70) -> dict:
    import numpy as np
    from PIL import Image, ImageFilter, ImageOps

    im = Image.open(path).convert("RGBA")
    side = min(im.size)
    im = im.crop((0, 0, side, side))
    alpha = im.split()[3]
    lum = ImageOps.grayscale(im.convert("RGB"))
    # local contrast so eyes / nose / jaw survive the downsampling
    lum = lum.filter(ImageFilter.UnsharpMask(radius=side // 60, percent=140, threshold=0))

    a = np.asarray(alpha, dtype=float) / 255
    L = np.asarray(lum, dtype=float) / 255
    inside = L[a > 0.5]
    lo, hi = np.percentile(inside, 2), np.percentile(inside, 98)
    L = np.clip((L - lo) / (hi - lo + 1e-6), 0, 1) ** 0.8

    # box-downsample with alpha premultiplied so edges don't pick up a dark fringe
    pre = Image.fromarray((L * a * 255).astype("uint8")).resize((grid, grid), Image.BOX)
    P = np.asarray(pre, dtype=float) / 255
    A = np.asarray(alpha.resize((grid, grid), Image.BOX), dtype=float) / 255

    dots = []
    for r in range(grid):
        for c in range(grid):
            if A[r, c] < 0.35:
                continue
            lv = P[r, c] / max(A[r, c], 1e-6)
            cover = min(1.0, (A[r, c] - 0.35) / 0.4)
            size = 0.5 * (0.16 + 0.84 * lv) * cover  # radius in cell units (max 0.5)
            if size > 0.05:
                dots.append([c, r, round(size, 3)])
    return {"grid": grid, "dots": dots}
