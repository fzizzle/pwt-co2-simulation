"""The Sizing page must run and state what the sweep found."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.sizing_charts import crossover

SIZING = str(ROOT / "dashboard" / "pages" / "7_Sizing.py")


@pytest.fixture(scope="module")
def app():
    app = AppTest.from_file(SIZING, default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def test_tiles_come_from_the_model(app):
    assert app.metric[0].value == "+23%"
    assert app.metric[1].value == "91%"
    assert app.metric[2].value == "1.5 kWh"


def test_table_view_is_available(app):
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert len(app.dataframe) == 2


def test_crossover_finds_where_the_band_falls_behind():
    band = pd.Series({1.0: 100.0, 0.9: 110.0, 0.8: 130.0})
    rule = pd.Series({1.0: 105.0, 0.9: 115.0, 0.8: 120.0})
    at, _ = crossover(band, rule)
    assert 0.8 < at < 0.9


def test_no_crossover_when_the_band_always_wins():
    band = pd.Series({1.0: 100.0, 0.8: 110.0})
    assert crossover(band, band + 5) is None
