import subprocess
import sys

import pytest
from pptx import Presentation
from pptx.enum.dml import MSO_FILL

from pwt.deck.render import build


@pytest.fixture(scope="module")
def deck(tmp_path_factory):
    path = build("dark", {}, tmp_path_factory.mktemp("deck"))
    return Presentation(path)


def test_builds_without_content(deck):
    assert len(deck.slides) == 23
    assert {"placeholder:subtitle", "placeholder:byline"} <= {
        s.name for s in deck.slides[0].shapes
    }
    assert "placeholder:headline" in [s.name for s in deck.slides[6].shapes]


def test_bars_and_flags(deck):
    for index, count, outlined in [
        (6, 16, {"petrol:wltc", "phev:wltc", "phev:nedc"}),
        (7, 4, {"petrol:wltc", "phev:wltc"}),
    ]:
        bars = [s for s in deck.slides[index].shapes if s.name.startswith("bar:")]
        assert len(bars) == count
        assert {
            s.name[4:] for s in bars if s.fill.type == MSO_FILL.BACKGROUND
        } == outlined


def test_lap_label_is_slide_number(deck):
    for i, slide in enumerate(deck.slides, 1):
        assert [s.text for s in slide.shapes if s.name == "lap-label"] == (
            [] if i == 1 else [str(i)]
        )


def test_tags_filled(tmp_path):
    path = build(
        "light", {"cmp-wltc": {"headline": "Petrol {co2.petrol.wltc}"}}, tmp_path
    )
    assert any(
        s.has_text_frame and s.text == "Petrol 145.1 g CO2/km"
        for s in Presentation(path).slides[7].shapes
    )


@pytest.mark.parametrize("themes", [("light",), ("dark", "light")])
def test_cli_writes_only_build_dir(tmp_path, themes):
    out = tmp_path / "build"
    args = ["--theme", themes[0]] if len(themes) == 1 else []
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pwt.deck",
            "--out",
            out,
            "--content",
            tmp_path / "missing",
            *args,
        ],
        check=True,
    )
    assert list(tmp_path.iterdir()) == [out]
    assert {p.stem for p in out.glob("*.pptx")} == {f"group-deck-{t}" for t in themes}
