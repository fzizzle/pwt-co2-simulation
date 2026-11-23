"""Read author-written slide fields from the deck's Markdown template."""

import re
from pathlib import Path

from pwt.deck.structure import SLIDES


def parse(text: str) -> dict[str, dict[str, str]]:
    allowed = {slide.id: slide.fields for slide in SLIDES}
    result: dict[str, dict[str, str]] = {}
    slide_id = field = None
    for line in text.splitlines():
        if line.startswith(">"):
            continue
        if re.match(r"^##(?:\s|$)", line):
            slide_id = line[2:].strip()
            if slide_id not in allowed:
                raise ValueError(f"Unknown slide id {slide_id!r}")
            if slide_id in result:
                raise ValueError(f"Duplicate slide id {slide_id!r}")
            result[slide_id] = {}
            field = None
        elif slide_id is not None:
            match = re.match(r"^([\w.-]+):(.*)$", line)
            if match:
                field, value = match.groups()
                if field not in allowed[slide_id]:
                    raise ValueError(f"Unknown field {field!r} on slide {slide_id!r}")
                if field in result[slide_id]:
                    raise ValueError(f"Duplicate field {field!r} on slide {slide_id!r}")
                result[slide_id][field] = value.strip()
            elif field is not None:
                result[slide_id][field] += "\n" + line
            elif line.strip():
                raise ValueError(f"Expected a field on slide {slide_id!r}: {line!r}")
    return {key: {name: value.strip() for name, value in fields.items()}
            for key, fields in result.items()}


def load(path: Path) -> dict[str, dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    return parse(text)
