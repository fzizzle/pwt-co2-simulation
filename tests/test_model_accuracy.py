"""Accuracy and cold-load tests for the Model page: shortfall reporting, deck-convention bars, lazy laps."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

MODEL_VIEW = ROOT / "dashboard" / "views" / "6_Model.py"


@pytest.fixture(scope="module")
def app() -> AppTest:
    at = AppTest.from_file(str(MODEL_VIEW), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _bar_chart_spec(at: AppTest) -> dict:
    for chart in at.get("plotly_chart"):
        spec = json.loads(chart.proto.spec)
        if any(trace.get("type") == "bar" for trace in spec.get("data", [])):
            return spec
    raise AssertionError("No bar chart rendered on the Model page")


def test_scenario_feasibility_table_keeps_shortfall_and_marks_exact_unchecked(app):
    """Model page keeps shortfall dict from scenario_cells and labels exact as unchecked."""
    # Dataframe 0 is the CO2 table (locked by test_model_page.py); dataframe 1 is feasibility.
    assert len(app.dataframe) >= 2
    feas = app.dataframe[1].value.set_index(["powertrain", "cycle"])
    exact_col = "1 · Workbook vehicles, 250 g/kWh grid"
    lossy_col = "5 · With storage losses"
    assert (feas[exact_col] == "unchecked").all()
    # Petrol Francorchamps sport under storage losses: 15 short steps, ~88.3 kW.
    petrol_sport = feas.loc[("Petrol", "Francorchamps — sport"), lossy_col]
    assert "15" in petrol_sport and "88" in petrol_sport and "kW" in petrol_sport
    # PHEV WLTC under storage losses: 34 short steps, ~13.1 kW.
    phev_wltc = feas.loc[("Plug-in hybrid", "WLTC Class 3"), lossy_col]
    assert "34" in phev_wltc and "13" in phev_wltc and "kW" in phev_wltc
    # Petrol NEDC passes the engine check.
    assert feas.loc[("Petrol", "NEDC"), lossy_col] == "pass"


def test_scenario_bar_chart_uses_deck_convention_for_infeasible_bars(app):
    """Infeasible bars are hollow/outlined with '*' on their labels; feasible bars are solid."""
    spec = _bar_chart_spec(app)
    bars = [t for t in spec["data"] if t.get("type") == "bar"]
    assert len(bars) == 4  # one trace per powertrain

    petrol = next(t for t in bars if t.get("name") == "Petrol")
    bev = next(t for t in bars if t.get("name") == "Battery electric")

    # Under default "storage losses", Petrol is feasible on NEDC (index 0) and infeasible on
    # Francorchamps eco/sport and WLTC (indices 1, 2, 3).
    assert not str(petrol["text"][0]).endswith("*")
    assert str(petrol["text"][2]).endswith("*")
    assert str(petrol["text"][3]).endswith("*")

    colors = petrol["marker"]["color"]
    line_widths = petrol["marker"]["line"]["width"]
    # Feasible bar has solid fill; infeasible bar has transparent/hollow fill and positive outline.
    assert colors[0] != "rgba(0,0,0,0)"
    assert colors[2] == "rgba(0,0,0,0)"
    assert line_widths[2] > 0

    # BEV has no engine shortfall -> all solid, no '*'.
    assert all(not str(lbl).endswith("*") for lbl in bev["text"])
    assert all(c != "rgba(0,0,0,0)" for c in bev["marker"]["color"])

    # Hover carries short steps and worst shortfall kW.
    assert "short" in petrol.get("hovertemplate", "").lower() or any(
        "kW" in str(cd) for cd in petrol.get("customdata", [])
    )


def test_scenario_bar_chart_marks_exact_scenario_unchecked():
    """Switching the scenario bar chart to exact labels it unchecked and uses no '*'."""
    at = AppTest.from_file(str(MODEL_VIEW), default_timeout=180).run()
    at.selectbox(key="model_bar_scenario").set_value("exact").run()
    assert not at.exception, [e.value for e in at.exception]
    spec = _bar_chart_spec(at)
    bars = [t for t in spec["data"] if t.get("type") == "bar"]
    for trace in bars:
        assert all(not str(lbl).endswith("*") for lbl in trace["text"])
        assert any("unchecked" in str(cd).lower() for cd in trace.get("customdata", []))
    captions = " ".join(c.value for c in at.caption).lower()
    assert "unchecked" in captions


def test_single_drive_surfaces_shortfall_and_unchecked_state():
    """Single-drive headlines show shortfall details when affected and unchecked for exact."""
    at = AppTest.from_file(str(MODEL_VIEW), default_timeout=180).run()
    # Select Petrol on supplied Francorchamps sport (run first to enable scenario picker).
    at.selectbox(key="model_powertrain").set_value("petrol")
    at.selectbox(key="model_cycle").set_value("franco_sport").run()
    assert not at.exception, [e.value for e in at.exception]
    at.selectbox(key="model_scenario").set_value("storage losses").run()
    assert not at.exception, [e.value for e in at.exception]
    warnings = " ".join(w.value for w in at.warning)
    assert "15" in warnings and "88" in warnings and "kW" in warnings

    # Switching to exact reports unchecked.
    at.selectbox(key="model_scenario").set_value("exact").run()
    assert not at.exception, [e.value for e in at.exception]
    captions = " ".join(c.value for c in at.caption).lower()
    assert "unchecked" in captions


def test_generated_laps_not_run_until_user_toggles():
    """Cold-load speedup: laps() must be gated behind a toggle, not run eagerly in the expander."""
    source = MODEL_VIEW.read_text()
    tree = ast.parse(source)
    # Check that laps() is called inside an `if st.toggle(...)` block, not unconditionally.
    toggle_guarded = False
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_src = ast.unparse(node.test)
            body_calls = [
                n.func.id for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            if "toggle" in test_src and "laps" in body_calls:
                toggle_guarded = True
    assert toggle_guarded, "laps() must be gated behind st.toggle so cold loads skip it"

    # AppTest check: initial load has no generated-laps dataframe; enabling toggle adds it.
    at = AppTest.from_file(str(MODEL_VIEW), default_timeout=180).run()
    before = len(at.dataframe)
    toggle = at.toggle(key="model_show_laps")
    assert toggle.value is False
    toggle.set_value(True).run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.dataframe) == before + 1
