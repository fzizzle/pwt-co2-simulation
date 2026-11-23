import numpy as np
import pandas as pd
import pytest
from PIL import Image
from pptx import Presentation

from pwt.deck import figures
from pwt.deck.render import build

SWINGS = pd.read_csv("docs/study-b-swings.csv")
CORNERING = pd.read_csv("docs/study-c-results.csv")


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("name", sorted(figures.FIGURES))
def test_every_chart_renders_on_a_clear_background(tmp_path, name, theme):
    path = figures.render(name, theme, tmp_path)
    with Image.open(path) as image:
        assert image.size == (2200, 1040)
        pixels = np.asarray(image.convert("RGBA"))
    assert pixels[0, 0, 3] == 0  # the slide shows through
    assert (pixels[..., 3] > 0).mean() > 0.01  # something was drawn


def test_charts_match_the_study_figures():
    assert set(figures.FIGURES) == {
        "study-b-combustion", "study-b-electric", "study-b-plugin", "study-b-provisional",
        "study-c-lap-time", "study-c-co2", "study-c-comparison",
    }


@pytest.mark.parametrize("powertrain, cycle, factors", [
    ("petrol", "wltc", 5), ("hybrid", "wltc", 5), ("bev", "nedc", 4), ("bev", "wltc", 4),
])
def test_tornado_rows_come_from_the_saved_swings(powertrain, cycle, factors):
    rows = figures.tornado_rows(powertrain, cycle)
    assert len(rows) == factors
    assert list(rows["rank"]) == sorted(rows["rank"])
    saved = SWINGS[(SWINGS.powertrain == powertrain) & (SWINGS.cycle == cycle)]
    assert rows.baseline.iloc[0] == pytest.approx(saved.baseline.iloc[0])


def test_petrol_wltc_baseline_is_flagged():
    # The engine is short of the WLTC trace at baseline (145.1 g CO2/km in the plan).
    rows = figures.tornado_rows("petrol", "wltc")
    assert round(rows.baseline.iloc[0], 1) == 145.1
    assert rows.baseline_short_steps.iloc[0] > 0
    assert not rows.engine_check_pass.any()


def test_cornering_lap_time_is_shared_by_all_cars():
    # One lap per grip or spoiler setting, so the lap-time chart draws one line.
    assert figures.shared_lap_time(CORNERING)


def test_unknown_chart_names_the_choices(tmp_path):
    with pytest.raises(ValueError, match="study-b-combustion"):
        figures.render("study-b-typo", "dark", tmp_path)


def test_slot_takes_a_themed_chart(tmp_path):
    path = build("dark", {"B-1": {"figure": "chart:study-b-combustion"}}, tmp_path)
    slide = Presentation(path).slides[13]
    assert [s.name for s in slide.shapes if s.name.startswith("chart:")] == [
        "chart:study-b-combustion"
    ]
    assert "docs/study-b-swings.csv" in slide.notes_slide.notes_text_frame.text
    assert (tmp_path / "dark-study-b-combustion.png").is_file()


def test_comparison_reads_every_radius_method():
    frame = pd.read_csv("docs/study-c-comparison.csv")
    assert set(frame.radius_method) <= set(figures.RADIUS_TITLES)
    assert frame.delta_co2_eu.notna().all()
