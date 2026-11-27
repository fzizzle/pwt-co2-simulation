"""Chart chrome: one helper owns the toolbar, legends clear corner labels, honest colours.

Task 2 of docs/superpowers/plans/2026-11-27-dashboard-polish.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import plotly.graph_objects as go
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import charts
from dashboard.layout import elevation_strip
from dashboard.loaders import trace_for
from dashboard.theme import CAR_COLOURS, DARK, LIGHT
from dashboard.track_charts import mark_corners


@pytest.fixture(scope="module")
def lap():
    return trace_for.__wrapped__("petrol", "franco_eco")


def test_no_direct_plotly_chart_calls():
    """Only layout.show_chart may call st.plotly_chart, so no page can bring back a toolbar."""
    offenders = []
    for path in (ROOT / "dashboard").rglob("*.py"):
        if path.name == "layout.py":
            continue
        # Any container's .plotly_chart, not just st.plotly_chart: left.plotly_chart(...) too.
        if re.search(r"\.plotly_chart\(", path.read_text(encoding="utf-8")):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_show_chart_hides_the_toolbar_by_default(monkeypatch):
    from dashboard import layout

    calls = []
    monkeypatch.setattr(layout.st, "plotly_chart", lambda fig, **kw: calls.append(kw))
    layout.show_chart(go.Figure())
    layout.show_chart(go.Figure(), toolbar=True, key="k")
    assert calls[0]["config"]["displayModeBar"] is False
    assert calls[0]["theme"] is None
    assert calls[1]["config"]["displayModeBar"] == "hover"
    assert calls[1]["key"] == "k"


def test_corner_labels_clear_the_legend(lap):
    fig = go.Figure(go.Scatter(x=lap["distance_m"], y=lap["speed_kph"], name="a"))
    fig.add_scatter(x=lap["distance_m"], y=lap["speed_kph"], name="b")
    fig.update_layout(showlegend=True, legend=dict(y=1.02))
    mark_corners(fig, lap, "distance_m", DARK)
    assert fig.layout.legend.y >= 1.14
    assert fig.layout.margin.t >= 76


def test_corner_labels_without_a_legend_keep_a_small_margin(lap):
    fig = go.Figure(go.Scatter(x=lap["distance_m"], y=lap["speed_kph"]))
    fig.update_layout(showlegend=False)
    mark_corners(fig, lap, "distance_m", DARK)
    assert 44 <= fig.layout.margin.t < 76


@pytest.mark.parametrize("pal", [DARK, LIGHT], ids=["dark", "light"])
def test_single_run_traces_use_the_given_colour(lap, pal):
    colour = CAR_COLOURS["petrol"]
    fig = charts.speed_and_altitude(lap, "distance_m", pal, colour=colour)
    assert fig.data[0].line.color == colour
    gear = charts.gear_steps(lap, "distance_m", pal, colour=colour)
    assert gear.data[0].line.color == colour


def test_car_independent_traces_are_neutral(lap):
    fig = charts.speed_and_altitude(lap, "distance_m", DARK)
    assert fig.data[0].line.color == DARK.text_secondary
    assert all(t.line.color != CAR_COLOURS["bev"] for t in fig.data)


def test_elevation_strip_has_scale_and_neutral_stroke(lap):
    fig = elevation_strip(lap, DARK)
    assert fig.layout.xaxis.visible is not False
    assert fig.layout.yaxis.visible is not False
    low, high = round(lap["altitude_m"].min()), round(lap["altitude_m"].max())
    ticks = [str(t) for t in fig.layout.yaxis.ticktext]
    assert any(str(low) in t for t in ticks) and any(str(high) in t for t in ticks)
    assert all(" m" in t for t in ticks)
    assert fig.data[0].line.color == DARK.text_secondary
