"""Numbers quoted in docs/study-c-cornering.md match the saved results."""

import re
from pathlib import Path

import pandas as pd
import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
REPORT = (DOCS / "study-c-cornering.md").read_text(encoding="utf-8")
RESULTS = pd.read_csv(DOCS / "study-c-results.csv")


def _row(variant, powertrain, value):
    column = "grip_factor" if variant == "grip" else "scz_m2"
    rows = RESULTS[(RESULTS.variant == variant) & (RESULTS.powertrain == powertrain)
                   & (RESULTS[column].round(2) == value)]
    assert len(rows) == 1
    return rows.iloc[0]


@pytest.mark.parametrize("label, variant, value", [
    ("Grip ×0.9", "grip", 0.9), (r"Grip ×1.0 \(baseline\)", "grip", 1.0), ("Grip ×1.1", "grip", 1.1),
    ("Grip ×1.3", "grip", 1.3), ("Spoiler SCz 0.2", "spoiler", 0.2), ("Spoiler SCz 0.4", "spoiler", 0.4),
])
def test_results_table_matches_the_csv(label, variant, value):
    match = re.search(rf"^\| {label} \| ([\d.]+) s \| ([\d.]+) \|$", REPORT, re.M)
    assert match, label
    row = _row(variant, "petrol", value)
    assert float(match[1]) == round(row.lap_time_s, 1)
    assert float(match[2]) == round(row.co2_eu, 1)


def test_baseline_sentence_matches_the_csv():
    row = _row("grip", "petrol", 1.0)
    assert f"{row.lap_time_s:.1f} s and {row.co2_eu:.1f} g CO2/km for petrol" in REPORT
    assert (RESULTS.short_steps == 0).all() == ("`short_steps` is 0 everywhere" in REPORT)


def test_tyre_ranges_match_the_csv():
    steps = [RESULTS[(RESULTS.variant == "grip") & (RESULTS.powertrain == p)].sort_values("grip_factor")
             for p in ("petrol", "hybrid")]
    seconds = pd.concat([-s.lap_time_s.diff().dropna() for s in steps])
    grams = pd.concat([-s.co2_eu.diff().dropna() for s in steps])
    quoted = (f"saves {seconds.min():.1f} to {seconds.max():.1f} s and "
              f"{grams.min():.1f} to {grams.max():.1f} g/km (petrol, hybrid)")
    assert quoted in REPORT


def test_bev_level_matches_the_csv():
    bev = RESULTS[(RESULTS.variant == "grip") & (RESULTS.powertrain == "bev")].co2_eu
    assert round(bev.mean()) == 132 and "about 132 g/km" in REPORT
