"""The Model page must run, and show the model's figures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

MODEL = str(ROOT / "dashboard" / "pages" / "6_Model.py")


@pytest.fixture(scope="module")
def app():
    app = AppTest.from_file(MODEL, default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def test_scenario_table_shows_the_model(app):
    table = app.dataframe[0].value.set_index(["powertrain", "cycle"])
    assert table.loc[("Petrol", "Francorchamps — eco"), "exact"] == "245.7"
    assert table.loc[("Petrol", "Francorchamps — eco"), "harmonised"] == "203.0"


@pytest.mark.parametrize(
    "powertrain, cycle",
    [("phev", "wltc"), ("hybrid", "franco_sport_generated"), ("bev", "nedc")],
)
def test_one_run_renders(app, powertrain, cycle):
    app.selectbox(key="model_powertrain").set_value(powertrain)
    app.selectbox(key="model_cycle").set_value(cycle).run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.metric) == 3
