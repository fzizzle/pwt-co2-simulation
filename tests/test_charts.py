"""Figure-level checks for the rules the charts are built to.

These run without Streamlit's runtime, so they are fast and catch styling regressions that a
page-level test would not notice.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from dashboard import charts
from dashboard.loaders import trace_for
from dashboard.theme import DARK, LIGHT, POWERTRAIN_ORDER, style_axes
from pwt.build import runs_frame
from pwt.catalog import CATALOG, course_file
from pwt.workbook import read_run


@pytest.fixture(scope="module")
def runs():
    return runs_frame([read_run(course_file(e.filename)) for e in CATALOG])


@pytest.fixture(scope="module")
def lap():
    return trace_for.__wrapped__("petrol", "franco_eco")


@pytest.mark.parametrize("pal", [LIGHT, DARK], ids=["light", "dark"])
def test_stacked_subplots_title_only_the_bottom_axis(lap, pal):
    """A shared-x subplot figure must print its x label once, not once per row."""
    fig = charts.speed_and_altitude(lap, "distance_m", pal)
    style_axes(fig, pal, x_title="Distance (m)")
    # fig.layout does not iterate in axis order, so sort by axis number as the code does.
    keys = sorted(
        (k for k in fig.layout if k.startswith("xaxis")),
        key=lambda k: int(k.removeprefix("xaxis") or 1),
    )
    titles = [fig.layout[k].title.text for k in keys]
    assert titles.count("Distance (m)") == 1
    assert titles[-1] == "Distance (m)", "the label belongs on the bottom axis"
    assert titles[0] is None, "the shared upper axis must not repeat the label"


@pytest.mark.parametrize("pal", [LIGHT, DARK], ids=["light", "dark"])
def test_style_axes_keeps_per_row_y_titles(lap, pal):
    """style_axes must not wipe the titles a subplot figure set for itself."""
    fig = charts.speed_and_altitude(lap, "distance_m", pal)
    style_axes(fig, pal)
    assert fig.layout.yaxis.title.text == "Speed (kph)"
    assert fig.layout.yaxis2.title.text == "Altitude (m)"


def test_template_is_pinned_so_placeholder_colours_cannot_leak(lap):
    """Importing Streamlit registers a template whose colorway is placeholders (#000001…)."""
    fig = charts.gear_steps(lap, "distance_m", DARK)
    style_axes(fig, DARK)
    assert fig.layout.template.layout.colorway is None


@pytest.mark.parametrize("pal", [LIGHT, DARK], ids=["light", "dark"])
def test_bars_carry_a_surface_gap_and_value_labels(runs, pal):
    """The 2px surface outline and the value labels are obligations, not decoration.

    The labels are the required relief for the light palette's sub-3:1 slots, so removing them
    would break contrast compliance the moment the theme is switched back.
    """
    fig = charts.grouped_totals(runs, "co2_g_per_km", pal, unit="g CO₂/km")
    assert len(fig.data) == len(POWERTRAIN_ORDER)
    for bar in fig.data:
        assert bar.marker.line.color == pal.surface
        assert bar.marker.line.width == 2
        assert bar.marker.cornerradius == 4
        assert bar.text is not None and any(t for t in bar.text)
        # Text wears text tokens, never the series colour.
        assert bar.textfont.color == pal.text_secondary


def test_colour_follows_the_powertrain_not_its_rank(runs):
    """Filtering the view must not repaint the survivors."""
    everything = charts.grouped_totals(runs, "co2_g_per_km", DARK, unit="g")
    without_petrol = charts.grouped_totals(
        runs[runs["powertrain"] != "petrol"], "co2_g_per_km", DARK, unit="g"
    )
    colours = {b.name: b.marker.color for b in everything.data}
    for bar in without_petrol.data:
        assert bar.marker.color == colours[bar.name]


def test_no_chart_uses_a_second_y_axis(runs, lap):
    """One scale per frame; two measures get two charts, never two axes."""
    figures = [
        charts.grouped_totals(runs, "co2_g_per_km", DARK, unit="g"),
        charts.gear_steps(lap, "distance_m", DARK),
        charts.force_breakdown(lap, "distance_m", DARK),
        charts.trace_lines(lap, ["engine_power_w", "speed_kph"], "distance_m", DARK),
    ]
    for fig in figures:
        for trace in fig.data:
            assert getattr(trace, "yaxis", None) in (None, "y")


# --- deployment resilience ---------------------------------------------------------------------


def test_loaders_recovers_from_a_stale_pwt_workbook(monkeypatch):
    """Streamlit Cloud keeps `pwt/` cached from boot, so a newly added function goes missing.

    Simulates that by hiding `read_block` on the loaded module, then re-importing loaders: the
    guard must reload `pwt.workbook` and come back with the name rather than raising
    ImportError, which is what forced a manual app reboot.
    """
    import importlib
    import sys

    import dashboard.loaders

    workbook_module = sys.modules["pwt.workbook"]
    monkeypatch.delattr(workbook_module, "read_block")
    assert not hasattr(workbook_module, "read_block")

    reloaded = importlib.reload(dashboard.loaders)

    assert hasattr(reloaded, "read_block"), "loaders did not recover the missing name"
    assert callable(reloaded.read_block)


def test_gap_bars_are_labelled_rather_than_showing_a_zero(runs):
    """A zero-height bar with "0.000" beside it reads as a result; it must say so instead."""
    gaps = {("phev", "nedc")}
    fig = charts.grouped_totals(runs, "co2_g_per_km", DARK, unit="g", gaps=gaps)
    phev = next(b for b in fig.data if b.name == "Plug-in hybrid")
    labels = list(phev.text)
    assert "to be filled" in labels
    assert labels.count("to be filled") == 1  # only the flagged cycle
    # the other powertrains are untouched
    petrol = next(b for b in fig.data if b.name == "Petrol")
    assert "to be filled" not in petrol.text


def test_no_gap_labels_when_none_are_flagged(runs):
    fig = charts.grouped_totals(runs, "co2_g_per_km", DARK, unit="g")
    for bar in fig.data:
        assert "to be filled" not in list(bar.text)
