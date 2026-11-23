import argparse
from pathlib import Path

from pwt.deck.content import load
from pwt.deck.render import build


def main():
    parser = argparse.ArgumentParser(
        description="Build the first-draft group presentation."
    )
    parser.add_argument("--theme", choices=("dark", "light", "both"), default="both")
    parser.add_argument("--content", type=Path, default=Path("docs/deck/slides.md"))
    parser.add_argument("--out", type=Path, default=Path("docs/deck/build"))
    args = parser.parse_args()
    content = load(args.content)
    for theme in ("dark", "light") if args.theme == "both" else (args.theme,):
        print(build(theme, content, args.out))


if __name__ == "__main__":
    main()
