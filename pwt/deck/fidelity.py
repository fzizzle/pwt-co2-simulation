"""Measure rendered PowerPoint slides against the independent design reference."""

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from pwt.deck.content import load
from pwt.deck.render import build

ROOT = Path(__file__).resolve().parents[2]
MOCKUPS = ROOT / "docs/superpowers/specs/deck-mockups"


def render_deck(pptx: Path, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # LibreOffice can report success on a conversion error. Stage the PDF so an
    # earlier successful export can never be measured as the current deck.
    with tempfile.TemporaryDirectory(dir=out_dir) as temp:
        work = Path(temp).resolve()
        subprocess.run(
            [
                "soffice",
                f"-env:UserInstallation={(work / 'profile').as_uri()}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                work,
                pptx,
            ],
            check=True,
        )
        pdf = work / (pptx.stem + ".pdf")
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-scale-to-x",
                "1600",
                "-scale-to-y",
                "900",
                pdf,
                work / "slide",
            ],
            check=True,
        )
        pdf.replace(out_dir / pdf.name)
        return [
            path.replace(out_dir / path.name)
            for path in sorted(work.glob("slide-*.png"))
        ]


def similarity(a: Path, b: Path) -> float:
    images = []
    for path in (a, b):
        with Image.open(path) as image:
            if image.size != (1600, 900):
                raise ValueError(f"Wrong slide dimensions in {path}: {image.size}")
            images.append(
                np.asarray(
                    image.convert("RGB").filter(ImageFilter.GaussianBlur(1.5)),
                    dtype=np.int16,
                )
            )
    return float((np.abs(images[0] - images[1]).max(axis=2) <= 16).mean())


def report(theme: str, out_dir: Path) -> list[tuple[int, float]]:
    deck_dir = out_dir / theme
    reference = out_dir / "reference"
    pptx = build(theme, load(ROOT / "tests/fixtures/deck-mockup.md"), deck_dir)
    renders = render_deck(pptx, deck_dir)
    subprocess.run(
        [
            sys.executable,
            "-I",
            MOCKUPS / "reference.py",
            "--out",
            reference,
            "--theme",
            theme,
        ],
        check=True,
    )
    scores = []
    for i, render in enumerate(renders, 1):
        ref = reference / theme / f"{i:02}.png"
        scores.append((i, similarity(ref, render)))
        with Image.open(ref) as a, Image.open(render) as b:
            panel = Image.new("RGB", (4800, 900))
            a, b = a.convert("RGB"), b.convert("RGB")
            for j, image in enumerate((a, b, ImageChops.difference(a, b))):
                panel.paste(image, (1600 * j, 0))
            panel.save(deck_dir / f"diff-{i:02}.png")
    if len(scores) != 23:
        raise ValueError(f"Expected 23 slides, rendered {len(scores)}")
    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=("dark", "light", "both"), default="both")
    args = parser.parse_args()
    themes = ("dark", "light") if args.theme == "both" else (args.theme,)
    results = [report(t, ROOT / "docs/deck/build/fidelity") for t in themes]
    print("slide", *themes)
    for i, row in enumerate(zip(*results), 1):
        print(i, *(f"{score:.6f}" for _, score in row))
    return int(any(score < 0.99 for rows in results for _, score in rows))


if __name__ == "__main__":
    sys.exit(main())
