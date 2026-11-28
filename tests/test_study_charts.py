"""Study A and C chart ergonomics. Task 7 of the dashboard polish plan.

Layout only: the studies' numbers, hollow provisional markers and captions are unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.cornering_charts import response_chart, rows_for
from dashboard.sizing_charts import best_by_battery, phev_lines
from dashboard.theme import DARK
from pwt.sweep import sizing

RESULTS = ROOT / "docs/study-c-results.csv"


@pytest.mark.parametrize("variant, baseline", [("grip", 1.0), ("spoiler", 0.0)])
def test_cornering_responses_share_one_axis(variant, baseline):
    rows = rows_for(pd.read_csv(RESULTS), "petrol", variant)
    fig = response_chart(rows, variant, "co2_eu", "petrol", DARK)
    assert len(fig.data) == 2
    assert fig.data[0].xaxis == "x" and fig.data[1].xaxis == "x2"
    assert fig.layout.xaxis.matches == "x2" or fig.layout.xaxis2.matches == "x"
    lines = [s for s in fig.layout.shapes if s.type == "line" and s.x0 == s.x1]
    assert any(s.x0 == baseline for s in lines)
    # Hollow provisional markers survive.
    assert all(isinstance(t.marker.symbol, (list, tuple)) for t in fig.data)


@pytest.fixture(scope="module")
def sizing_frame():
    return sizing()


@pytest.mark.parametrize("cycle", ["wltc", "franco_sport_generated"])
def test_phev_legend_has_one_entry_per_grid(sizing_frame, cycle):
    eu = best_by_battery(sizing_frame, "phev", cycle, "co2_eu")
    fr = best_by_battery(sizing_frame, "phev", cycle, "co2_fr")
    fig = phev_lines(
        eu, fr, 400.0, None, DARK,
        eu_feasible=best_by_battery(sizing_frame, "phev", cycle, "co2_eu", feasible_only=True),
        fr_feasible=best_by_battery(sizing_frame, "phev", cycle, "co2_fr", feasible_only=True),
    )
    shown = {t.legendgroup for t in fig.data if t.showlegend is not False}
    assert shown == {"EU grid, 250 g/kWh", "French grid, 73 g/kWh"}
