"""No cut-off labels, one name for the generated lap, one heading per page.

Task 5 of docs/superpowers/plans/2026-11-27-dashboard-polish.md.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.theme import POWERTRAIN_ORDER
from pwt.catalog import POWERTRAIN_NAMES
from pwt.sweep import CYCLES

VIEWS = ROOT / "dashboard" / "views"
TIMEOUT = 240
GENERATED_NAME = CYCLES["franco_sport_generated"]


def run(name: str) -> AppTest:
    app = AppTest.from_file(str(VIEWS / name), default_timeout=TIMEOUT).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


@pytest.fixture(scope="module")
def model():
    return run("6_Model.py")


@pytest.fixture(scope="module")
def sizing():
    return run("7_Sizing.py")


@pytest.fixture(scope="module")
def track():
    return run("8_Track_Map.py")


def test_metric_css_wraps_instead_of_truncating(monkeypatch):
    from dashboard import layout
    from dashboard.theme import DARK

    seen = []
    monkeypatch.setattr(layout.st, "html", lambda body: seen.append(body))
    layout.inject_css(DARK)
    css = "".join(seen)
    rule = css.split('[data-testid="stMetricLabel"]', 1)[1].split("}", 1)[0]
    assert "white-space: normal" in rule
    # The value element itself and everything inside it: a long text value such as
    # "Peak engine efficiency" ran into the next tile when only its child div wrapped.
    rule = css.split('[data-testid="stMetricValue"] *', 1)[1].split("}", 1)[0]
    assert "white-space: normal" in rule
    assert "overflow-wrap: anywhere" in rule


@pytest.mark.parametrize("fixture", ["model", "sizing", "track"])
def test_metric_labels_fit(fixture, request):
    app = request.getfixturevalue(fixture)
    for metric in app.metric:
        assert len(metric.label) <= 30, metric.label


def test_model_scenario_headers_fit_and_rows_follow_the_chart(model):
    table = model.dataframe[0].value
    assert list(table.columns[:2]) == ["Powertrain", "Cycle"]
    for header in table.columns[2:]:
        assert len(header) <= 22, header
    names = [POWERTRAIN_NAMES[p] for p in POWERTRAIN_ORDER]
    seen = list(dict.fromkeys(table["Powertrain"]))
    assert seen == names


def test_model_generated_lap_states_its_scenario(model):
    assert model.selectbox(key="model_cycle").value == "franco_sport_generated"
    keys = [s.key for s in model.selectbox]
    assert "model_scenario" not in keys
    captions = " ".join(c.value for c in model.caption)
    assert "4 · Assignment" in captions


def test_sizing_grammar_and_lap_name(sizing):
    text = " ".join(c.value for c in sizing.caption)
    assert "a 80 kW" not in text and "a 8 kW" not in text and "a 18 kW" not in text
    labels = " ".join(m.label for m in sizing.metric)
    assert "Francorchamps — sport" not in labels


def test_generated_lap_has_one_name():
    for name in ("6_Model.py", "7_Sizing.py"):
        source = (VIEWS / name).read_text(encoding="utf-8")
        assert "Francorchamps — sport, generated" not in source
        assert '"Francorchamps sport, generated": "Francorchamps — sport"' not in source


def test_no_car_label_on_study_controls():
    for name in ("9_CO2_Sensitivity.py", "10_Cornering_Speed.py"):
        tree = ast.parse((VIEWS / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "selectbox":
                assert not (node.args and isinstance(node.args[0], ast.Constant)
                            and node.args[0].value == "Car"), name


def test_trace_explorer_axis_sits_beside_the_run():
    app = run("3_Trace_Explorer.py")
    assert len(app.sidebar.selectbox) == 0
    assert app.title[0].value == "Trace explorer"


@pytest.mark.parametrize("name", ["9_CO2_Sensitivity.py", "10_Cornering_Speed.py"])
def test_reports_do_not_add_a_second_h1(name):
    app = run(name)
    h1 = [m.value for m in app.markdown if m.value.lstrip().startswith("# ")]
    assert h1 == []


def _decimals(value) -> int:
    text = f"{value!r}"
    return len(text.split(".", 1)[1]) if "." in text and "e" not in text else 0


@pytest.mark.parametrize("name", ["9_CO2_Sensitivity.py", "10_Cornering_Speed.py"])
def test_study_tables_show_sensible_precision(name):
    app = run(name)
    frame = app.dataframe[0].value
    for column in frame.select_dtypes("number").columns:
        limit = 2 if "lastic" in column else 1
        worst = max((_decimals(v) for v in frame[column].dropna()), default=0)
        assert worst <= limit, (column, worst)
