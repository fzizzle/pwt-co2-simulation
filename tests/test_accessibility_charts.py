"""Tests for accessibility & responsive chart fixes in Study B and Hybrid sizing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.sensitivity_charts import elasticity_panels, tornado
from dashboard.sizing_charts import _RAMP, efficiency_lines, petrol_gap, size_heatmap
from dashboard.theme import DARK, LIGHT, POWERTRAIN_ORDER
from pwt.sensitivity import swings

SIZING_VIEW = str(ROOT / "dashboard" / "views" / "7_Sizing.py")


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(c1: str, c2: str) -> float:
    l1, l2 = sorted((_luminance(c1), _luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _blend(fg: str, bg: str, alpha: float) -> str:
    f = [int(fg.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(alpha * fc + (1 - alpha) * bc):02x}" for fc, bc in zip(f, b))


@pytest.fixture(scope="module")
def study_b_ranked() -> pd.DataFrame:
    return swings(pd.read_csv(ROOT / "docs" / "study-b-results.csv"))


def test_tornado_bar_opacity_and_contrast_meet_wcag_aa(study_b_ranked):
    for pt in POWERTRAIN_ORDER:
        group = study_b_ranked[
            (study_b_ranked.powertrain == pt)
            & (study_b_ranked.cycle == "franco_sport_generated")
        ]
        fig = tornado(group, pt, DARK)
        bar = fig.data[0]
        opacity = bar.marker.opacity if bar.marker.opacity is not None else 1.0
        assert opacity >= 0.8, f"Tornado bar opacity {opacity} < 0.8 for {pt}"
        blended = _blend(bar.marker.color, DARK.surface, opacity)
        assert _contrast(blended, DARK.surface) >= 3.0, f"{pt} tornado bar fails 3:1 on dark"


@pytest.mark.parametrize("across", ["cars", "cycles"])
def test_elasticity_panels_uses_single_column_for_mobile_readability(study_b_ranked, across):
    fig = elasticity_panels(study_b_ranked, across, DARK)
    # Single-column layout: every panel x-axis spans full width [0.0, 1.0].
    for key in ("xaxis", "xaxis2", "xaxis3", "xaxis4"):
        domain = tuple(fig.layout[key].domain)
        assert domain == (0.0, 1.0), f"{key} domain {domain} is not full-width single column"
    assert len(fig.layout.annotations) == 4


def test_petrol_gap_prevents_label_clipping_and_keeps_stem_contrast():
    free = {"NEDC": -26.0, "WLTC Class 3": -18.0, "Francorchamps eco": -8.0, "Francorchamps sport": -5.0}
    lossy = {"NEDC": -8.0, "WLTC Class 3": -11.0, "Francorchamps eco": 0.6, "Francorchamps sport": 2.6}
    fig = petrol_gap(free, lossy, DARK)

    # Both marker+text traces must disable cliponaxis so "-26 %" never clips behind the y-axis.
    labeled_traces = [t for t in fig.data if t.mode == "markers+text"]
    assert len(labeled_traces) == 2
    for trace in labeled_traces:
        assert trace.cliponaxis is False

    # Generous padding on both sides of the data range.
    x0, x1 = fig.layout.xaxis.range
    assert x0 <= -36.0, f"Left x-range {x0} too tight for '-26 %' label"
    assert x1 >= 12.0, f"Right x-range {x1} too tight for right-side label"

    # Reference annotation at x=0 must anchor right so it stays inside the plot area.
    ref_ann = next(a for a in fig.layout.annotations if a.x == 0)
    assert ref_ann.xanchor == "right"

    # Dumbbell connector stems must meet 3:1 graphical contrast on dark surface.
    stem_traces = [t for t in fig.data if t.mode == "lines"]
    assert stem_traces
    for stem in stem_traces:
        assert _contrast(stem.line.color, DARK.surface) >= 3.0


def test_efficiency_lines_avoids_label_and_crossover_clipping():
    band = pd.Series({1.0: 105.0, 0.95: 112.0, 0.9: 120.0, 0.85: 128.0, 0.8: 136.0})
    rule = pd.Series({1.0: 118.0, 0.95: 118.0, 0.9: 119.0, 0.85: 120.0, 0.8: 121.0})
    fig = efficiency_lines(band, rule, 145.0, DARK)
    assert (fig.layout.margin.r or 0) >= 100
    cross_ann = next(a for a in fig.layout.annotations if a.showarrow)
    assert cross_ann.ax > 0, "Crossover callout must not point left into the y-axis"


def test_sizing_heatmap_ramp_contrast_and_colorbar_on_both_heatmaps():
    for _, colour in _RAMP:
        assert _contrast(colour, DARK.surface) >= 3.0, f"Ramp stop {colour} fails 3:1 vs dark"

    synthetic = pd.DataFrame([
        {"battery_kwh": 2.0, "motor_kw": 20.0, "co2_eu": 110.0, "buildable": True, "short_steps": 0, "short_kw": 0.0},
        {"battery_kwh": 4.0, "motor_kw": 40.0, "co2_eu": 105.0, "buildable": True, "short_steps": 0, "short_kw": 0.0},
    ])
    fig = size_heatmap(synthetic, DARK, show_scale=True)
    hm = next(t for t in fig.data if t.type == "heatmap")
    assert hm.showscale is True
    assert hm.colorbar.tickfont.size >= 12

    app = AppTest.from_file(SIZING_VIEW, default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    heatmaps = []
    for chart in app.get("plotly_chart"):
        spec = json.loads(chart.proto.spec)
        for trace in spec.get("data", []):
            if trace.get("type") == "heatmap":
                heatmaps.append(trace)
    assert len(heatmaps) == 2
    for hm_spec in heatmaps:
        assert hm_spec.get("showscale") is not False, "Both sizing heatmaps must show a colourbar"
