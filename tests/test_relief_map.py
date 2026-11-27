"""Track map on the deck's relief contours instead of street tiles.

Task 6 of docs/superpowers/plans/2026-11-27-dashboard-polish.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go

from dashboard.loaders import trace_for
from dashboard.theme import DARK
from dashboard.track_charts import COMPACT_LANDMARKS, lap_map, metrics
from pwt.trackmap import LANDMARKS


@pytest.fixture(scope="module")
def lap():
    return trace_for.__wrapped__("petrol", "franco_eco")


def _map(lap, **kw):
    values, unit, diverging = metrics(lap, source="workbook")["Speed"]
    return lap_map(lap, values, "Speed", unit, diverging, DARK, source="workbook", **kw)


def test_relief_map_has_no_tiles(lap):
    fig = _map(lap)
    assert not any(isinstance(t, go.Scattermap) for t in fig.data)
    assert fig.layout.map.style is None
    assert fig.layout.yaxis.scaleanchor == "x"


def test_relief_map_draws_contours_below_the_lap(lap):
    fig = _map(lap)
    names = [t.name for t in fig.data]
    first_contour = names.index("relief")
    first_lap = next(i for i, t in enumerate(fig.data) if t.name == "lap")
    assert first_contour < first_lap
    assert fig.data[first_contour].line.color == DARK.grid


def test_tiles_remain_available(lap):
    fig = _map(lap, basemap="tiles")
    assert any(isinstance(t, go.Scattermap) for t in fig.data)


def test_compact_labels_are_used(lap):
    fig = _map(lap, width_px=390)
    shown = {text for t in fig.data if t.mode and "text" in t.mode for text in (t.text or ())}
    assert shown and shown <= set(COMPACT_LANDMARKS)
    assert shown != set(LANDMARKS.values())


def test_track_map_controls_precede_map():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "dashboard" / "views" / "8_Track_Map.py"),
                            default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    source = (ROOT / "dashboard" / "track_charts.py").read_text(encoding="utf-8")
    assert "ctrl_col, map_col = st.columns(" in source


def test_metric_rows_pair_up_on_phones(monkeypatch):
    from dashboard import layout

    seen = []
    monkeypatch.setattr(layout.st, "html", lambda body: seen.append(body))
    layout.inject_css(DARK)
    css = "".join(seen)
    block = css.split("@media (max-width: 640px)", 1)[1]
    assert ':has([data-testid="stMetric"])' in block
    assert "flex-wrap: wrap" in block
