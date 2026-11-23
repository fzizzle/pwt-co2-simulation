"""Render each approved mockup SVG at its original design size."""

import argparse
from pathlib import Path
from functools import cache
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--theme", required=True, choices=("dark", "light"))
    args = parser.parse_args()
    dest = (args.out / args.theme).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        sys.argv = [
            str(HERE / name)
            for name in ("mock16.py", "track.json", "cycles.json", "mock4.py")
        ]
        sys.argv += [str(work / "grid.html")] + [
            str(HERE / name) for name in ("mock10.py", "mock15.py", "co2.json")
        ]
        # Load the design functions without rendering the surrounding two-theme gallery.
        source = Path(sys.argv[0]).read_text().split("\ndk=run(", 1)[0]
        design = {}
        exec(compile(source, sys.argv[0], "exec"), design)
        # placement() requests the identical north-up coordinates for each candidate.
        design["unit"] = cache(design["unit"])
        dark = args.theme == "dark"
        slides = design["run"](dark, 0.14 if dark else 0.20, "d" if dark else "l")
        for i, (_, svg) in enumerate(slides, 1):
            html = work / "slide.html"
            # The review page's rounded corners and shadow frame are outside the slide.
            html.write_text(
                '<meta charset="utf-8"><style>*{margin:0}svg{border-radius:0!important}</style>'
                + svg
            )
            subprocess.run(
                [
                    "chromium",
                    "--headless=new",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--force-device-scale-factor=1",
                    f"--user-data-dir={work / 'profile'}",
                    "--window-size=1600,900",
                    f"--screenshot={dest / f'{i:02}.png'}",
                    html.as_uri(),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
    main()
