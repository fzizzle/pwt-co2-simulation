from pathlib import Path

import pytest

from pwt.deck.content import load, parse
from pwt.deck.structure import CORNERS, SECTIONS, SLIDES, lap_position


def test_order_and_count():
    expected = ("title sim sim-model sim-cars sim-changed cmp cmp-all cmp-wltc "
                "A A-terms A-steps A-1 A-2 A-3 A-end B B-1 B-2 B-3 B-end C C-1 C-2 C-3 C-end lim lim-rows questions")
    assert [slide.id for slide in SLIDES] == expected.split()
    assert len(SLIDES) == 28


def test_parse_fields_and_notes():
    text = "Intro\n## cmp-all\nheadline: Hi\n> comment\nnotes: a\nb\n"
    assert parse(text) == {"cmp-all": {"headline": "Hi", "notes": "a\nb"}}


def test_unknown_slide_id_fails():
    with pytest.raises(ValueError, match="cmp-al"):
        parse("## cmp-al\nheadline: x")


def test_unknown_field_fails():
    with pytest.raises(ValueError) as error:
        parse("## cmp-all\nheadlin: x")
    assert all(word in str(error.value) for word in ("headlin", "cmp-all"))


def test_lap_positions():
    assert lap_position(0) is None
    positions = [lap_position(i) for i in range(1, len(SLIDES))]
    assert all(a < b for a, b in zip(positions, positions[1:]))
    for index, slide in enumerate(SLIDES):
        if slide.layout == "opener":
            assert lap_position(index) == CORNERS[SECTIONS[slide.section][0]]
    lim_rows = [s.id for s in SLIDES].index("lim-rows")
    assert lap_position(lim_rows) == (CORNERS["bus_stop"] + CORNERS["finish"]) / 2
    assert positions[-1] == CORNERS["finish"]


def test_slides_file_parses_with_every_slide_and_field():
    """Owners fill fields in as they go, so only the ids and field names are fixed."""
    content = load(Path("docs/deck/slides.md"))
    assert {k: set(v) for k, v in content.items()} == {
        slide.id: set(slide.fields) for slide in SLIDES
    }


def test_missing_file(tmp_path):
    assert load(tmp_path / "absent.md") == {}
