"""Workbook pages show reported values only, in the workbook's own units, with dashes for gaps.

Task 3 of docs/superpowers/plans/2026-11-27-dashboard-polish.md. Owner decision D2 (27 Nov
2026): Compare's computed "Difference" and "Change" columns go.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.loaders import trace_for
from dashboard.theme import DARK
from dashboard.track_charts import _car_label, metric_strip
from pwt.catalog import CATALOG

COMPARE = str(ROOT / "dashboard" / "views" / "4_Compare.py")
DATA = str(ROOT / "dashboard" / "views" / "5_Data.py")
TIMEOUT = 120


def _index(powertrain: str, cycle: str) -> int:
    return next(i for i, e in enumerate(CATALOG) if e.powertrain == powertrain and e.cycle == cycle)


@pytest.fixture(scope="module")
def compare_app():
    app = AppTest.from_file(COMPARE, default_timeout=TIMEOUT).run()
    app.selectbox(key="cmp_left").set_value(_index("petrol", "franco_eco")).run()
    app.selectbox(key="cmp_right").set_value(_index("phev", "franco_eco")).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def _frame(element) -> pd.DataFrame:
    value = element.value
    return value.data if hasattr(value, "data") else value


def test_compare_reports_only_reported_values(compare_app):
    figures = _frame(compare_app.dataframe[0])
    assert list(figures.columns) == [
        "Figure", "Petrol · Francorchamps — eco", "Plug-in hybrid · Francorchamps — eco",
    ]


def test_compare_parameter_gaps_show_a_dash(compare_app):
    for element in compare_app.dataframe:
        frame = _frame(element)
        for value in frame.to_numpy().ravel():
            assert value is not None
            assert str(value) not in ("None", "nan", "NaN", "<NA>")
    params = _frame(compare_app.dataframe[1]).set_index("Parameter")
    battery = [p for p in params.index if p.startswith("Battery energy")]
    assert battery, list(params.index)
    assert params.loc[battery[0], "Petrol · Francorchamps — eco"] == "—"


def test_workbook_strip_keeps_metres():
    lap = trace_for.__wrapped__("petrol", "franco_eco")
    fig = metric_strip(lap, lap["speed_kph"], "Speed", "km/h", False, DARK, distance_unit="m")
    assert max(fig.data[0].x) == pytest.approx(lap["distance_m"].max())
    assert fig.layout.xaxis.title.text == "Lap distance (m)"
    assert _car_label(lap.iloc[3], distance_unit="m").split("·")[0].strip().endswith(" m")


def test_model_strip_still_uses_kilometres():
    lap = trace_for.__wrapped__("petrol", "franco_eco")
    fig = metric_strip(lap, lap["speed_kph"], "Speed", "km/h", False, DARK)
    assert max(fig.data[0].x) == pytest.approx(lap["distance_m"].max() / 1000)


def test_data_column_picker_uses_display_names():
    from dashboard.labels import column
    from dashboard.layout import CANONICAL_QUANTITIES

    for code, (name, unit) in CANONICAL_QUANTITIES.items():
        assert column(code, with_unit=False) == name
        assert unit in column(code)
