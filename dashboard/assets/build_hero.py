"""Build compact dark and light Spa-Francorchamps hero images from `pwt.deck.art`.

Run with the deck environment (which has matplotlib and Pillow):
    .venv/bin/python -m dashboard.assets.build_hero

Outputs `dashboard/assets/spa-hero-dark.png` and `dashboard/assets/spa-hero-light.png`
so Streamlit Cloud can serve the north-up Spa lap with faded relief without installing
matplotlib or contourpy at runtime.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from pwt.deck.art import title_art

ASSETS = Path(__file__).resolve().parent
# Tight crop around the north-up lap and its faded relief in title_art's 3200x1800 canvas:
# lap spans roughly y=140..1360, x=1220..1980, bottom fade finishes cleanly by y=1460.
CROP_BOX = (760, 70, 2440, 1450)  # 1680 x 1380 -> 960 x 788 (compact, retina-crisp)
TARGET_WIDTH = 960


def build() -> list[Path]:
    written: list[Path] = []
    with tempfile.TemporaryDirectory() as tmp:
        for theme in ("dark", "light"):
            raw = Path(tmp) / f"title-{theme}.png"
            title_art(theme, raw)
            img = Image.open(raw).crop(CROP_BOX)
            height = round(img.height * TARGET_WIDTH / img.width)
            resized = img.resize((TARGET_WIDTH, height), Image.Resampling.LANCZOS)
            out = ASSETS / f"spa-hero-{theme}.png"
            resized.save(out, optimize=True)
            written.append(out)
    return written


if __name__ == "__main__":
    for path in build():
        print(f"wrote {path} ({path.stat().st_size // 1024} KB)")
