#!/usr/bin/env python3
"""
Packs a folder of turntable frames (000.webp, 001.webp, ...) into one looping
animated WebP for the README:  python tools/turntable.py <frames-dir>
Only needed when the avatar changes; the result is committed as assets/avatar.webp.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1])
STEP, HEIGHT, MS = 2, 420, 45  # every 2nd frame, 420px tall, ~5.4s per full turn

files = sorted(src.glob("*.webp"))[::STEP]
frames = [Image.open(f).convert("RGBA") for f in files]

# one shared crop box (union of every frame's visible pixels) so the figure doesn't jitter
box = None
for im in frames:
    b = im.getbbox()
    box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
pad = 8
box = (max(0, box[0] - pad), max(0, box[1] - pad), box[2] + pad, box[3] + pad)
w = round((box[2] - box[0]) * HEIGHT / (box[3] - box[1]))
frames = [im.crop(box).resize((w, HEIGHT), Image.LANCZOS) for im in frames]

out = ROOT / "assets" / "avatar.webp"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=MS, loop=0, quality=72, method=6,
               lossless=False, allow_mixed=False)
print(f"{len(frames)} frames, {w}x{HEIGHT}, {out.stat().st_size / 1024:.0f} KB -> {out.relative_to(ROOT)}")
