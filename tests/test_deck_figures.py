from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image
from pptx import Presentation

from pwt.deck import figures
from pwt.deck.render import build
from pwt.deck.structure import SLIDES


def _index(slide_id: str) -> int:
    return [s.id for s in SLIDES].index(slide_id)

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
        "phase-3-storage", "phase-3-hybrid", "phase-3-plugin",
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
    slide = Presentation(path).slides[_index("B-1")]
    assert [s.name for s in slide.shapes if s.name.startswith("chart:")] == [
        "chart:study-b-combustion"
    ]
    assert "docs/study-b-swings.csv" in slide.notes_slide.notes_text_frame.text
    assert (tmp_path / "dark-study-b-combustion.png").is_file()


def test_comparison_reads_every_radius_method():
    frame = pd.read_csv("docs/study-c-comparison.csv")
    assert set(frame.radius_method) <= set(figures.RADIUS_TITLES)
    assert frame.delta_co2_eu.notna().all()


# Study A: the saved sizing results reproduce docs/phase-3-sizing.md.
@pytest.mark.parametrize("powertrain, cycle, battery, motor, co2", [
    ("hybrid", "wltc", 1.5, 30, 128.1),
    ("hybrid", "franco_sport_generated", 4, 80, 374.0),
    ("phev", "franco_eco_generated", 4, 80, 77.5),
])
def test_sizing_lowest_matches_the_study(powertrain, cycle, battery, motor, co2):
    rows = figures.best_by_battery(powertrain, cycle)
    top = rows.loc[rows.co2_eu.idxmin()]
    assert (top.battery_kwh, top.motor_kw, round(top.co2_eu, 1)) == (battery, motor, co2)


def test_sizing_rows_are_buildable_and_complete():
    for powertrain in ("hybrid", "phev"):
        for cycle in figures.data.CYCLE_KEYS:
            rows = figures.best_by_battery(powertrain, cycle)
            assert list(rows.battery_kwh) == [1, 1.5, 2, 3, 4, 6, 8, 10, 12, 15, 20]
            assert (rows.motor_kw / rows.battery_kwh <= 20).all()
            assert rows.co2_eu.notna().all()


def test_plugin_wltc_large_pack_is_flagged():
    # The study's table: 20 kWh on WLTC Class 3 leaves the engine 35 steps short.
    rows = figures.best_by_battery("phev", "wltc")
    assert rows.set_index("battery_kwh").short_steps[20] == 35


def test_storage_at_the_assumption_is_the_deck_baseline():
    # 85 % each way with the band is the shared "storage losses" full hybrid.
    for cycle in figures.data.CYCLE_KEYS:
        rows = figures.storage_rows(cycle)
        band = rows[(rows.strategy == "band")
                    & (rows.storage_efficiency == figures.ASSUMED_STORAGE)]
        assert band.co2_eu.iloc[0] == round(figures.data.cell("hybrid", cycle).co2_eu, 1)


def test_storage_direction():
    # Less storage loss, less CO2, for both strategies on every cycle.
    for cycle in figures.data.CYCLE_KEYS:
        for _, d in figures.storage_rows(cycle).groupby("strategy"):
            assert d.co2_eu.is_monotonic_decreasing


def test_study_a_chart_names_its_study_document(tmp_path):
    path = build("dark", {"A-2": {"figure": "chart:phase-3-hybrid"}}, tmp_path)
    notes = Presentation(path).slides[_index("A-2")].notes_slide.notes_text_frame.text
    assert "docs/phase-3-sizing.csv" in notes
    assert "docs/phase-3-sizing.md" in notes


# The Study A headlines in docs/deck/slides.md quote these results.
def test_study_a_headlines_match_the_data():
    from pwt.sweep import MOTOR_KW
    text = open("docs/deck/slides.md").read()
    # A-1: at 85 % the band strategy emits more on WLTC; only the band-strategy car keeps up.
    assert "With 85 % storage, the band strategy costs CO2 on WLTC, yet only it keeps up" in text
    assert figures.storage_gap("wltc")[figures.ASSUMED_STORAGE] > 0
    for cycle in figures.SHOWN_CYCLES:
        rows = figures.storage_rows(cycle)
        assert (rows[rows.strategy == "band"].short_steps == 0).all()
        assert (rows[rows.strategy == "sheets' rule"].short_steps > 0).all()
    # A-2: WLTC flat (within 1.5 g) from 1 to 3 kWh; the sport lap's lowest uses the top motor.
    assert "Full hybrid: WLTC is flat up to 3 kWh; the sport lap wants maximum motor" in text
    wltc = figures.best_by_battery("hybrid", "wltc").set_index("battery_kwh").co2_eu
    assert wltc.loc[1:3].max() - wltc.loc[1:3].min() < 1.5
    sport = figures.best_by_battery("hybrid", "franco_sport_generated")
    assert sport.loc[sport.co2_eu.idxmin()].motor_kw == max(MOTOR_KW)
    # A-3: the plug-in hybrid's sport-lap CO2 bottoms out at 6 kWh, then rises.
    assert "Plug-in on the sport lap: past 6 kWh, the pack only adds mass" in text
    phev = figures.best_by_battery("phev", "franco_sport_generated").set_index("battery_kwh")
    assert phev.co2_eu.idxmin() == 6 and phev.co2_eu.loc[6:].is_monotonic_increasing


def test_study_a_charts_show_two_cycles():
    assert figures.SHOWN_CYCLES == ("wltc", "franco_sport_generated")


def test_study_a_dataflow_counts_match_the_saved_results():
    # The arrows on A-steps quote run counts; they must match the CSVs the charts read.
    from pwt.sweep import BATTERY_KWH, MOTOR_KW, POWERTRAINS
    text = open("docs/deck/slides.md").read()
    cars = len(BATTERY_KWH) * len(MOTOR_KW) * len(POWERTRAINS)
    assert f"edge.grid.sim: {cars} cars" in text and cars == 154
    assert f"edge.sim.runs: {len(figures._sizing())} runs" in text
    assert f"edge.sweep.storage: {len(figures._storage())} runs" in text
    assert f"node.grid: Factorial sweep | tries all {len(BATTERY_KWH)} packs × {len(MOTOR_KW)} motors" in text


def test_dataflow_fields_are_known_and_drawn(tmp_path):
    from pwt.deck.content import load
    from pwt.deck.structure import DATAFLOW_EDGES, DATAFLOW_NODES
    content = load(Path("docs/deck/slides.md"))  # fails loudly on an unknown field
    assert all(f"node.{n[0]}" in content["A-steps"] for n in DATAFLOW_NODES)
    assert all(f"edge.{a}.{b}" in content["A-steps"] for a, b in DATAFLOW_EDGES)
    path = build("dark", content, tmp_path)
    slide = Presentation(path).slides[_index("A-steps")]
    texts = [s.text_frame.text for s in slide.shapes if s.has_text_frame]
    assert "Backward sim" in texts and "616 runs" in texts


def test_study_a_wrapup_quotes_match_the_data():
    # A-end quotes model results; check each against the saved results.
    from pwt.deck.content import load
    from pwt.sweep import MAX_C_RATE, MOTOR_KW
    end = load(Path("docs/deck/slides.md"))["A-end"]
    assert "CO2 barely moves from 1 to 3 kWh" in end["point1"]
    wltc = figures.best_by_battery("hybrid", "wltc").set_index("battery_kwh").co2_eu
    assert wltc.loc[1:3].max() - wltc.loc[1:3].min() < 1.5
    assert "lowest sits at our 80 kW and 20C limits" in end["point2"]
    sport = figures.best_by_battery("hybrid", "franco_sport_generated")
    top = sport.loc[sport.co2_eu.idxmin()]
    assert top.motor_kw == max(MOTOR_KW) == 80
    assert top.motor_kw / top.battery_kwh == MAX_C_RATE == 20
    assert "costs CO2 on WLTC Class 3" in end["point3"]
    assert figures.storage_gap("wltc")[0.85] > 0
    assert "past 6 kWh the pack only adds mass" in end["open3"]


def test_empty_wrapup_shows_the_owners_placeholders(tmp_path):
    path = build("dark", {}, tmp_path)
    slide = Presentation(path).slides[_index("B-end")]
    texts = [s.text_frame.text for s in slide.shapes if s.has_text_frame]
    assert "Study B owner's conclusion" in texts
