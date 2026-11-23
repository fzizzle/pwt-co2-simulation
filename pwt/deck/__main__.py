import argparse
from pathlib import Path

from pwt.deck.content import load
from pwt.deck.render import WARNINGS, build


def main():
    parser = argparse.ArgumentParser(
        description="Build the first-draft group presentation."
    )
    parser.add_argument("--theme", choices=("dark", "light", "both"), default="both")
    parser.add_argument("--content", type=Path, default=Path("docs/deck/slides.md"))
    parser.add_argument("--out", type=Path, default=Path("docs/deck/build"))
    args = parser.parse_args()
    content = load(args.content)
    warnings: list[str] = []
    for theme in ("dark", "light") if args.theme == "both" else (args.theme,):
        print(build(theme, content, args.out))
        warnings += [w for w in WARNINGS if w not in warnings]
    for warning in warnings:
        print(f"warning: {warning}")


if __name__ == "__main__":
    main()
