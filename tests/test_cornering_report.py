"""Numbers quoted in docs/study-c-cornering.md match the saved results."""

import re
from pathlib import Path

import pandas as pd
import pytest

from pwt.cornering import KG_PER_SCZ, OUTLINE_SEARCH_WINDOW_M, SCZS, outline_stats

DOCS = Path(__file__).resolve().parents[1] / "docs"
REPORT = (DOCS / "study-c-cornering.md").read_text(encoding="utf-8")
RESULTS = pd.read_csv(DOCS / "study-c-results.csv")
RESULTS_OUTLINE = pd.read_csv(DOCS / "study-c-results-outline.csv")
CORNERS = pd.read_csv(DOCS / "study-c-corners.csv")
COMPARISON = pd.read_csv(DOCS / "study-c-comparison.csv")


def _row(frame, variant, powertrain, value):
    column = "grip_factor" if variant == "grip" else "scz_m2"
    rows = frame[(frame.variant == variant) & (frame.powertrain == powertrain)
                 & (frame[column].round(2) == value)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_outline_coarseness_numbers_match_trackmap():
    stats = outline_stats()
    assert f"{stats['vertices']} unique vertices over {stats['length_m']:.1f} m" in REPORT
    assert (f"from {stats['spacing_min_m']:.1f} m to {stats['spacing_max_m']:.1f} m "
            f"(median {stats['spacing_median_m']:.1f} m,\nmean {stats['spacing_mean_m']:.1f} m)") in REPORT


def test_corner_table_in_report_matches_corners_csv():
    for _, row in CORNERS.iterrows():
        landmark = row.landmark if pd.notna(row.landmark) and str(row.landmark).strip() else "—"
        line = (
            f"| {int(row.distance_m)} | {landmark} | {row.template_speed_kph:.1f} | "
            f"{row.inferred_radius_m:.1f} | {row.outline_radius_m:.1f} | "
            f"{row.implied_mu_outline:.2f} | {row.outline_speed_at_mu0_kph:.1f} |"
        )
        assert line in REPORT, line
    assert (f"μ from {CORNERS.implied_mu_outline.min():.2f} to "
            f"{CORNERS.implied_mu_outline.max():.2f}") in REPORT
    assert (f"R = v² / (μ₀ g) = {CORNERS.inferred_radius_m.min():.1f} m to "
            f"{CORNERS.inferred_radius_m.max():.1f} m") in REPORT
    assert (f"= {CORNERS.outline_radius_m.min():.1f} m to "
            f"{CORNERS.outline_radius_m.max():.1f} m.") in REPORT
    la_source = CORNERS[CORNERS.landmark == "La Source"].iloc[0]
    assert f"La Source reads {la_source.outline_radius_m:.1f} m" in REPORT
    assert f"within ±{OUTLINE_SEARCH_WINDOW_M:.0f} m" in REPORT
    assert (f"{CORNERS.template_speed_kph.min():.0f} to "
            f"{CORNERS.template_speed_kph.max():.0f} km/h") in REPORT
    nonzero_scz = [s for s in SCZS if s > 0]
    assert f"({KG_PER_SCZ * min(nonzero_scz):.0f} to {KG_PER_SCZ * max(nonzero_scz):.0f} kg)" in REPORT


@pytest.mark.parametrize("label, variant, value", [
    ("Grip ×0.9", "grip", 0.9),
    (r"Grip ×1.0 \(baseline\)", "grip", 1.0),
    ("Grip ×1.1", "grip", 1.1),
    ("Grip ×1.2", "grip", 1.2),
    ("Grip ×1.3", "grip", 1.3),
    ("Spoiler SCz 0.1 m²", "spoiler", 0.1),
    ("Spoiler SCz 0.2 m²", "spoiler", 0.2),
    ("Spoiler SCz 0.3 m²", "spoiler", 0.3),
    ("Spoiler SCz 0.4 m²", "spoiler", 0.4),
])
def test_inferred_results_table_matches_the_csv(label, variant, value):
    pattern = rf"^\| {label} \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$"
    match = re.search(pattern, REPORT, re.M)
    assert match, label
    petrol = _row(RESULTS, variant, "petrol", value)
    bev = _row(RESULTS, variant, "bev", value)
    hybrid = _row(RESULTS, variant, "hybrid", value)
    phev = _row(RESULTS, variant, "phev", value)
    assert float(match[1]) == round(petrol.lap_time_s, 1)
    assert float(match[2]) == round(petrol.co2_eu, 1)
    assert float(match[3]) == round(bev.co2_eu, 1)
    assert float(match[4]) == round(hybrid.co2_eu, 1)
    assert float(match[5]) == round(phev.co2_eu, 1)


@pytest.mark.parametrize("label, variant, value", [
    ("Grip ×0.9", "grip", 0.9),
    (r"Grip ×1.0 \(outline μ₀ = 0.7\)", "grip", 1.0),
    ("Grip ×1.3", "grip", 1.3),
    ("Spoiler SCz 0.2 m²", "spoiler", 0.2),
    ("Spoiler SCz 0.4 m²", "spoiler", 0.4),
])
def test_outline_results_table_matches_the_csv(label, variant, value):
    section = REPORT.split("### Alternative method: outline radii")[1].split("## Like-for-like")[0]
    pattern = rf"^\| {label} \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$"
    match = re.search(pattern, section, re.M)
    assert match, label
    petrol = _row(RESULTS_OUTLINE, variant, "petrol", value)
    bev = _row(RESULTS_OUTLINE, variant, "bev", value)
    hybrid = _row(RESULTS_OUTLINE, variant, "hybrid", value)
    phev = _row(RESULTS_OUTLINE, variant, "phev", value)
    assert float(match[1]) == round(petrol.lap_time_s, 1)
    assert float(match[2]) == round(petrol.co2_eu, 1)
    assert float(match[3]) == round(bev.co2_eu, 1)
    assert float(match[4]) == round(hybrid.co2_eu, 1)
    assert float(match[5]) == round(phev.co2_eu, 1)


def test_baseline_and_feasibility_sentences_match_the_csvs():
    row = _row(RESULTS, "grip", "petrol", 1.0)
    assert f"{row.lap_time_s:.1f} s and {row.co2_eu:.1f} g CO2/km for Petrol" in REPORT
    all_feasible = (
        (RESULTS.short_steps == 0).all()
        and (RESULTS_OUTLINE.short_steps == 0).all()
        and (COMPARISON.spoiler_short_steps == 0).all()
        and (COMPARISON.tyres_short_steps == 0).all()
    )
    assert all_feasible == ("`short_steps` is 0 everywhere" in REPORT)

    out_row = _row(RESULTS_OUTLINE, "grip", "petrol", 1.0)
    assert f"({out_row.lap_time_s:.1f} s vs {row.lap_time_s:.1f} s)" in REPORT
    assert f"({out_row.co2_eu:.1f} vs {row.co2_eu:.1f} g CO2/km)" in REPORT


def test_tyre_and_bev_summary_numbers_match_the_csv():
    steps = [RESULTS[(RESULTS.variant == "grip") & (RESULTS.powertrain == p)].sort_values("grip_factor")
             for p in ("petrol", "hybrid")]
    seconds = pd.concat([-s.lap_time_s.diff().dropna() for s in steps])
    grams = pd.concat([-s.co2_eu.diff().dropna() for s in steps])
    quoted = (f"saves {seconds.min():.1f} to {seconds.max():.1f} s and "
              f"{grams.min():.1f} to {grams.max():.1f} g CO2/km (Petrol,\n  Full hybrid)")
    assert quoted in REPORT

    bev = RESULTS[(RESULTS.variant == "grip") & (RESULTS.powertrain == "bev")].co2_eu
    bev_base = _row(RESULTS, "grip", "bev", 1.0)
    bev_sp04 = _row(RESULTS, "spoiler", "bev", 0.4)
    assert round(bev.mean()) == 132 and "about 132 g CO2/km EU" in REPORT
    assert f"{bev_base.co2_fr:.1f} g CO2/km France at baseline" in REPORT
    assert f"+{bev_sp04.co2_eu - bev_base.co2_eu:.1f} g CO2/km EU at SCz 0.4 m²" in REPORT


@pytest.mark.parametrize("method, heading", [
    ("inferred", "### Inferred radii (default), matched on lap time"),
    ("outline", "### Outline radii, matched on lap time"),
])
def test_comparison_tables_match_comparison_csv(method, heading):
    section = REPORT.split(heading)[1].split("### ")[0]
    part = COMPARISON[COMPARISON.radius_method == method]
    for scz, group in part.groupby("scz_m2", sort=True):
        by_car = group.set_index("powertrain")
        p = by_car.loc["petrol"]
        line = (
            f"| {scz:.1f} | {p.spoiler_lap_time_s:.1f} | {p.matched_grip_factor:.3f} | "
            f"{p.delta_co2_eu:+.1f} | {by_car.loc['bev'].delta_co2_eu:+.1f} | "
            f"{by_car.loc['hybrid'].delta_co2_eu:+.1f} | {by_car.loc['phev'].delta_co2_eu:+.1f} |"
        )
        assert line in section, line

    petrol = part[part.powertrain == "petrol"].sort_values("scz_m2")
    assert (f"{petrol.matched_grip_factor.iloc[0]:.3f} down to "
            f"{petrol.matched_grip_factor.iloc[-1]:.3f}") in REPORT


def test_required_limits_and_draft_label_are_present():
    assert "DRAFT by Claude (second pass), for the owner to review." in REPORT
    for required in ("**Radii:**", "**One line:**", "**Fixed braking:**", "**Fixed speeds elsewhere:**"):
        assert required in REPORT
