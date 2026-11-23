"""Find the Inter font files and measure text in them.

The deck is set in Inter and presented from the machine that builds it, so the fonts are
looked up through fontconfig (`fc-list`), the same way LibreOffice finds them. Matplotlib's
own font cache is not used: it does not see fonts in ~/.local/share/fonts.
"""

from __future__ import annotations

import subprocess
from functools import cache
from pathlib import Path

from PIL import ImageFont

#: Weight -> Inter's style name, as in its file names (Inter-SemiBold.otf …).
STYLES = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
#: The family names a PowerPoint run uses for each weight (bold is a flag on "Inter").
FAMILIES = {400: "Inter", 500: "Inter Medium", 600: "Inter SemiBold", 700: "Inter"}


@cache
def _files() -> dict[str, Path]:
    try:
        out = subprocess.run(
            ["fc-list", "-f", "%{file}\n", "Inter"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("fontconfig (fc-list) is needed to find the Inter font") from error
    files = {Path(line).stem: Path(line) for line in out.splitlines() if line.strip()}
    if "Inter-Regular" not in files:
        raise RuntimeError(
            "Inter is not installed. Install the static Inter fonts (rsms.me/inter) and rebuild."
        )
    return files


def inter_file(weight: int = 400, italic: bool = False) -> Path:
    """The Inter font file for `weight` (400, 500, 600 or 700) and slant."""
    style = STYLES[weight]
    if italic:
        style = "Italic" if style == "Regular" else style + "Italic"
    return _files()[f"Inter-{style}"]


@cache
def _font(weight: int, italic: bool) -> ImageFont.FreeTypeFont:
    # Measured at 100 px; widths scale linearly with size.
    return ImageFont.truetype(str(inter_file(weight, italic)), 100)


def text_width(text: str, size: float, weight: int = 400, italic: bool = False,
               spacing: float = 0) -> float:
    """Advance width of one line of `text` at `size` px (design units), with letter spacing."""
    if not text:
        return 0.0
    return _font(weight, italic).getlength(text) * size / 100 + spacing * (len(text) - 1)
