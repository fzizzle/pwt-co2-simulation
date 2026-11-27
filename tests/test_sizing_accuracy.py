"""Accuracy tests for Hybrid sizing: feasibility fields, provisional styling, and cold load."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.sizing_charts import (
    PROVISIONAL_LABEL,
    best_by_battery,
    best_selection,
    phev_lines,
    size_heatmap,
)
from dashboard.theme import DARK
from pwt.sweep import sizing

SIZING_VIEW = ROOT / "dashboard" / "views" / "7_Sizing.py"


@pytest.fixture(scope="module")
def sizing_frame() -> pd.DataFrame:
    return sizing()


def test_best_by_battery_carries_motor_and_shortfall_fields(sizing_frame):
    """Every plotted PHEV point keeps its winning motor, short_steps, short_kw and flag."""
    wltc_all = best_by_battery(sizing_frame, "phev", "wltc", "co2_eu")
    expected_cols = {"battery_kwh", "motor_kw", "co2", "short_steps", "short_kw", "provisional"}
    assert expected_cols <= set(wltc_all.columns)
    assert len(wltc_all) == 11
    assert (wltc_all["short_steps"] > 0).all()
    assert (wltc_all["short_kw"] > 0).all()
    assert wltc_all["provisional"].all()
    # Feasible-only set on WLTC PHEV is empty.
    wltc_feas = best_by_battery(sizing_frame, "phev", "wltc", "co2_eu", feasible_only=True)
    assert wltc_feas.empty
    assert expected_cols <= set(wltc_feas.columns)


def test_best_by_battery_separates_feasible_and_provisional_on_sport(sizing_frame):
    """On Francorchamps sport, 1.5–4 kWh have lower provisional motors and higher feasible ones."""
    sport_all = best_by_battery(sizing_frame, "phev", "franco_sport_generated", "co2_eu")
    sport_feas = best_by_battery(
        sizing_frame, "phev", "franco_sport_generated", "co2_eu", feasible_only=True
    )
    # 1 kWh has no feasible motor; 1.5–20 kWh do (10 points).
    assert 1.0 not in set(sport_feas["battery_kwh"])
    assert len(sport_feas) == 10
    assert (sport_feas["short_steps"] == 0).all()
    # At 4 kWh, overall min is provisional (80 kW), feasible min is 50 kW.
    all_4 = sport_all[sport_all["battery_kwh"] == 4.0].iloc[0]
    feas_4 = sport_feas[sport_feas["battery_kwh"] == 4.0].iloc[0]
    assert all_4["provisional"]
    assert all_4["short_steps"] > 0 and all_4["short_kw"] > 0
    assert not feas_4["provisional"]
    assert feas_4["motor_kw"] != all_4["motor_kw"]
    # At 6 kWh, both agree and pass the engine check.
    all_6 = sport_all[sport_all["battery_kwh"] == 6.0].iloc[0]
    feas_6 = sport_feas[sport_feas["battery_kwh"] == 6.0].iloc[0]
    assert not all_6["provisional"]
    assert all_6["motor_kw"] == feas_6["motor_kw"] == 80


def test_best_selection_reports_empty_feasible_set_and_separate_optima(sizing_frame):
    wltc_phev = sizing_frame[
        (sizing_frame["powertrain"] == "phev") & (sizing_frame["cycle"] == "wltc")
    ]
    sel = best_selection(wltc_phev)
    assert sel["feasible"] is None
    assert sel["feasible_count"] == 0
    assert sel["provisional"] is not None
    assert sel["provisional"]["short_steps"] > 0

    wltc_hybrid = sizing_frame[
        (sizing_frame["powertrain"] == "hybrid") & (sizing_frame["cycle"] == "wltc")
    ]
    hyb_sel = best_selection(wltc_hybrid)
    assert hyb_sel["feasible"] is not None
    assert hyb_sel["provisional"] is None
    assert hyb_sel["feasible_count"] == hyb_sel["buildable_count"]


def test_phev_lines_marks_infeasible_points_and_empty_feasible_set(sizing_frame):
    """WLTC PHEV has zero feasible points: hollow markers, dashed/dotted lines, provisional label."""
    eu_all = best_by_battery(sizing_frame, "phev", "wltc", "co2_eu")
    fr_all = best_by_battery(sizing_frame, "phev", "wltc", "co2_fr")
    eu_feas = best_by_battery(sizing_frame, "phev", "wltc", "co2_eu", feasible_only=True)
    fr_feas = best_by_battery(sizing_frame, "phev", "wltc", "co2_fr", feasible_only=True)
    fig = phev_lines(
        eu_all, fr_all, ymax=150.0, note=None, pal=DARK,
        eu_feasible=eu_feas, fr_feasible=fr_feas,
    )
    assert len(fig.data) >= 2
    for trace in fig.data:
        assert trace.marker.symbol.endswith("-open"), f"Expected hollow marker, got {trace.marker.symbol}"
        assert trace.line.dash in ("dash", "dot", "dashdot"), f"Expected dashed line, got {trace.line.dash}"
        assert "kW" in trace.hovertemplate or "motor" in trace.hovertemplate.lower()
        assert "short" in trace.hovertemplate.lower()
    annotations = " ".join(a.text for a in fig.layout.annotations).lower()
    assert PROVISIONAL_LABEL.lower() in annotations or "no feasible" in annotations


def test_phev_lines_sport_distinguishes_feasible_and_provisional(sizing_frame):
    """Sport PHEV draws feasible points solid/filled and provisional points dashed/hollow."""
    eu_all = best_by_battery(sizing_frame, "phev", "franco_sport_generated", "co2_eu")
    fr_all = best_by_battery(sizing_frame, "phev", "franco_sport_generated", "co2_fr")
    eu_feas = best_by_battery(
        sizing_frame, "phev", "franco_sport_generated", "co2_eu", feasible_only=True
    )
    fr_feas = best_by_battery(
        sizing_frame, "phev", "franco_sport_generated", "co2_fr", feasible_only=True
    )
    fig = phev_lines(
        eu_all, fr_all, ymax=400.0, note=(6.0, "6 kWh"), pal=DARK,
        eu_feasible=eu_feas, fr_feasible=fr_feas,
    )
    filled = [t for t in fig.data if t.marker.symbol and not str(t.marker.symbol).endswith("-open")]
    hollow = [t for t in fig.data if t.marker.symbol and str(t.marker.symbol).endswith("-open")]
    assert filled, "Expected solid/filled feasible traces"
    assert hollow, "Expected dashed/hollow provisional traces"
    for trace in hollow:
        assert trace.line.dash in ("dash", "dot", "dashdot")


def test_size_heatmap_does_not_silently_pick_infeasible_best():
    """If a lower-CO2 cell has short_steps > 0, Best must pick the lowest feasible cell."""
    synthetic = pd.DataFrame([
        {"battery_kwh": 2.0, "motor_kw": 20.0, "co2_eu": 110.0, "buildable": True, "short_steps": 0, "short_kw": 0.0},
        {"battery_kwh": 2.0, "motor_kw": 40.0, "co2_eu": 95.0, "buildable": True, "short_steps": 8, "short_kw": 12.4},
        {"battery_kwh": 4.0, "motor_kw": 20.0, "co2_eu": 120.0, "buildable": True, "short_steps": 0, "short_kw": 0.0},
        {"battery_kwh": 4.0, "motor_kw": 40.0, "co2_eu": 105.0, "buildable": True, "short_steps": 0, "short_kw": 0.0},
    ])
    fig = size_heatmap(synthetic, DARK)
    # Best feasible is (4 kWh, 40 kW, 105 g/km), NOT the infeasible (2 kWh, 40 kW, 95 g/km).
    ann_texts = [a.text for a in fig.layout.annotations]
    best_ann = next(t for t in ann_texts if "Best" in t or "Lowest" in t)
    assert "4 kWh" in best_ann and "40 kW" in best_ann
    # Infeasible cells must be marked visibly with hollow overlay markers.
    scatter_traces = [t for t in fig.data if t.type == "scatter"]
    assert any(
        "provisional" in (t.name or "").lower() or "short" in (t.name or "").lower()
        for t in scatter_traces
    )


def test_size_heatmap_flags_provisional_when_no_feasible_cell_exists():
    """When all buildable cells are infeasible, the lowest cell is visibly flagged provisional."""
    synthetic = pd.DataFrame([
        {"battery_kwh": 2.0, "motor_kw": 20.0, "co2_eu": 110.0, "buildable": True, "short_steps": 5, "short_kw": 6.2},
        {"battery_kwh": 2.0, "motor_kw": 40.0, "co2_eu": 95.0, "buildable": True, "short_steps": 8, "short_kw": 12.4},
    ])
    fig = size_heatmap(synthetic, DARK)
    ann_text = " ".join(a.text for a in fig.layout.annotations).lower()
    assert "provisional" in ann_text
    assert "no feasible" in ann_text or "short" in ann_text


def test_sizing_page_renders_title_and_intro_before_cached_sweeps():
    """Cold-load UX: st.title and intro must execute before sizes() and storage()."""
    source = SIZING_VIEW.read_text()
    tree = ast.parse(source)
    title_line = None
    sweep_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "title":
                title_line = min(title_line or node.lineno, node.lineno)
            elif isinstance(func, ast.Name) and func.id in ("sizes", "storage"):
                sweep_lines.append(node.lineno)
    assert title_line is not None and sweep_lines
    assert title_line < min(sweep_lines), (
        f"st.title (line {title_line}) must appear before cached sweep calls ({sweep_lines})"
    )


def test_sizing_page_smoke_surfaces_empty_feasible_set_and_provisional_status():
    """Smoke test via AppTest: WLTC PHEV empty feasible set and provisional label appear."""
    app = AppTest.from_file(str(SIZING_VIEW), default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    all_text = "\n".join([
        *(w.value for w in app.warning),
        *(i.value for i in app.info),
        *(m.value for m in app.markdown),
        *(c.value for c in app.caption),
    ]).lower()
    assert "provisional" in all_text
    assert "no feasible" in all_text or "0 of" in all_text or "empty" in all_text
