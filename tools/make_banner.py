#!/usr/bin/env python3
r"""Compose the repository banner: Flanders' portrait beside the wordmark.

The banner is a single raster image on purpose. GitHub will not load a remote
image from inside an SVG, and a raster banner renders identically everywhere.

Run from the project root:

    .\.venv\Scripts\python.exe tools\make_banner.py

Output: docs/banner.png (2400x600, displayed at 1200x300).
"""

from __future__ import annotations

import io
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "banner.png"

SOURCE_URL = "https://s3.crackedcdn.com/phpimages/article/6/9/4/915694.jpg"

WIDTH, HEIGHT = 2400, 600
BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
REGULAR = r"C:\Windows\Fonts\segoeui.ttf"

# Same three stops as the old SVG, along the diagonal.
STOPS = [
    (0.00, (15, 32, 39)),  # #0f2027
    (0.55, (32, 58, 67)),  # #203a43
    (1.00, (44, 83, 100)),  # #2c5364
]

# Where the portrait card sits.
CARD_X, CARD_Y = 1700, 40
CARD_W, CARD_H = 560, 520
CARD_RADIUS = 48
CARD_BORDER = (126, 231, 135)  # #7ee787


def gradient(width: int, height: int) -> Image.Image:
    xs = np.linspace(0.0, 1.0, width)[None, :]
    ys = np.linspace(0.0, 1.0, height)[:, None]
    t = xs * 0.6 + ys * 0.4
    t = np.clip(t, 0.0, 1.0)

    positions = np.array([stop[0] for stop in STOPS])
    colours = np.array([stop[1] for stop in STOPS], dtype=float)

    channels = [np.interp(t, positions, colours[:, i]) for i in range(3)]
    rgb = np.stack(channels, axis=-1).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def portrait() -> Image.Image:
    """Fetch the source picture and crop it to the card shape."""
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
        raw = response.read()
    source = Image.open(io.BytesIO(raw)).convert("RGB")

    # The subject sits slightly right of centre; bias the crop that way.
    aspect = CARD_W / CARD_H
    crop_h = source.height
    crop_w = int(crop_h * aspect)
    centre_x = int(source.width * 0.44)
    left = max(0, min(source.width - crop_w, centre_x - crop_w // 2))
    box = (left, 0, left + crop_w, crop_h)

    return source.crop(box).resize((CARD_W, CARD_H), Image.LANCZOS)


def rounded_mask(width: int, height: int, radius: int) -> Image.Image:
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    return mask


def main() -> int:
    banner = gradient(WIDTH, HEIGHT)
    draw = ImageDraw.Draw(banner)

    title_font = ImageFont.truetype(BOLD, 176)
    subtitle_font = ImageFont.truetype(REGULAR, 56)
    tagline_font = ImageFont.truetype(REGULAR, 40)

    draw.text((160, 96), "FLANDERS", font=title_font, fill=(255, 255, 255))
    draw.text(
        (164, 316),
        "A neighbourly voice for task delegation",
        font=subtitle_font,
        fill=(169, 214, 229),
    )
    draw.text((166, 420), "Okily dokily!", font=tagline_font, fill=(126, 231, 135))

    # Soft accent rule under the wordmark.
    draw.rounded_rectangle((166, 292, 766, 298), radius=3, fill=(94, 180, 200))

    picture = portrait()
    banner.paste(picture, (CARD_X, CARD_Y), rounded_mask(CARD_W, CARD_H, CARD_RADIUS))
    draw.rounded_rectangle(
        (CARD_X, CARD_Y, CARD_X + CARD_W - 1, CARD_Y + CARD_H - 1),
        radius=CARD_RADIUS,
        outline=CARD_BORDER,
        width=4,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    banner.save(OUT, format="PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
