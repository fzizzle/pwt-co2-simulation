"""Numbers quoted in docs/study-c-cornering.md match the saved results."""

import re
from pathlib import Path

import pandas as pd
import pytest

from pwt.cornering import (
    FIT_HALF_WINDOW_M,
    FIT_HALF_WINDOWS_M,
    KG_PER_SCZ,
    OUTLINE_SEARCH_WINDOW_M,
    OUTLINE_SPACING_M,
    SCZS,
    TRACK_HALF_WIDTH_M,
    one_grip_fits_every_corner,
    outline_stats,
)

DOCS = Path(__file__).resolve().parents[1] / "docs"
REPORT = (DOCS / "study-c-cornering.md").read_text(encoding="utf-8")
RESULTS = pd.read_csv(DOCS / "study-c-results.csv")
RESULTS_OUTLINE = pd.read_csv(DOCS / "study-c-results-outline.csv")
RESULTS_LINE = pd.read_csv(DOCS / "study-c-results-line.csv")
CORNERS = pd.read_csv(DOCS / "study-c-corners.csv")
COMPARISON = pd.read_csv(DOCS / "study-c-comparison.csv")


def _row(frame, variant, powertrain, value):
    column = "grip_factor" if variant == "grip" else "scz_m2"
    rows = frame[(frame.variant == variant) & (frame.powertrain == powertrain)
                 & (frame[column].round(2) == value)]
    assert len(rows) == 1
    return rows.iloc[0]


def _section(start: str) -> str:
    """The report from heading `start` up to the next heading of level 2 or 3."""
    after = REPORT.split(start, 1)[1]
    return re.split(r"^#{2,3} ", after, maxsplit=1, flags=re.M)[0]


def _corner(name):
    return CORNERS[CORNERS.landmark == name].iloc[0]


def test_outline_coarseness_numbers_match_trackmap():
    stats = outline_stats()
    assert f"{stats['vertices']} unique vertices over {stats['length_m']:.1f} m" in REPORT
    assert (f"from {stats['spacing_min_m']:.1f} m to {stats['spacing_max_m']:.1f} m "
            f"(median {stats['spacing_median_m']:.1f} m,\nmean {stats['spacing_mean_m']:.1f} m)") in REPORT
    assert f"coarse {stats['vertices']}-vertex centreline outline" in REPORT


def test_corner_table_in_report_matches_corners_csv():
    for _, row in CORNERS.iterrows():
        landmark = row.landmark if pd.notna(row.landmark) and str(row.landmark).strip() else "-"
        line = (
            f"| {int(row.distance_m)} | {landmark} | {row.template_speed_kph:.1f} | "
            f"{row.inferred_radius_m:.1f} | {row.outline_radius_m:.1f} | {row.line_radius_m:.1f} | "
            f"{row.radius_low_m:.1f} to {row.radius_high_m:.1f} | {row.min_3pt_radius_m:.1f} | "
            f"{row.implied_mu_outline:.2f} | {row.implied_mu_low:.2f} to {row.implied_mu_high:.2f} |"
        )
        assert line in REPORT, line


def test_method_constants_quoted_in_report():
    assert f"resamples the outline every {OUTLINE_SPACING_M:.0f} m" in REPORT
    assert f"within ±{OUTLINE_SEARCH_WINDOW_M:.0f} m that turns most within ±{FIT_HALF_WINDOW_M:.0f} m" in REPORT
    assert f"points within ±{FIT_HALF_WINDOW_M:.0f} m of that apex" in REPORT
    low, mid, high = FIT_HALF_WINDOWS_M
    assert f"half-windows of {low:.0f}, {mid:.0f} and {high:.0f} m" in REPORT
    assert f"half a track width, {TRACK_HALF_WIDTH_M:.1f} m, an ASSUMPTION" in REPORT
    assert f"| {TRACK_HALF_WIDTH_M:.1f} m (`TRACK_HALF_WIDTH_M`) |" in REPORT
    assert f"assumed\n  {TRACK_HALF_WIDTH_M:.1f} m half track width" in REPORT


def test_radius_ranges_and_grip_claim_match_corners_csv():
    assert (f"R = v² / (μ₀ g) = {CORNERS.inferred_radius_m.min():.1f} m to "
            f"{CORNERS.inferred_radius_m.max():.1f} m") in REPORT
    assert (f"within ±{FIT_HALF_WINDOW_M:.0f} m of each apex = {CORNERS.outline_radius_m.min():.1f} m to "
            f"{CORNERS.outline_radius_m.max():.1f} m.") in REPORT
    assert (f"fitted radius plus {TRACK_HALF_WIDTH_M:.1f} m = {CORNERS.line_radius_m.min():.1f} m to "
            f"{CORNERS.line_radius_m.max():.1f} m.") in REPORT

    claim = (f"On this coarse outline, the implied grip ranges from "
             f"{CORNERS.implied_mu_outline.min():.2f} to {CORNERS.implied_mu_outline.max():.2f}.")
    assert REPORT.count(claim) == 2  # the Choices table and the corner section
    within = "This spread is within the method's uncertainty"
    outside = "No single grip value lies inside every corner's band"
    if one_grip_fits_every_corner(CORNERS):
        assert within in REPORT and outside not in REPORT
    else:
        assert outside in REPORT and within not in REPORT
        pouhon, bruxelles = _corner("Pouhon"), _corner("Bruxelles")
        assert pouhon.implied_mu_high < bruxelles.implied_mu_low
        assert (f"Pouhon's is {pouhon.implied_mu_low:.2f} to {pouhon.implied_mu_high:.2f} and "
                f"Bruxelles' is {bruxelles.implied_mu_low:.2f} to {bruxelles.implied_mu_high:.2f}.") in REPORT


def test_la_source_check_and_unreliable_apex_match_corners_csv():
    la_source = _corner("La Source")
    assert (f"centreline radius is {la_source.outline_radius_m:.1f} m and the driver's line "
            f"{la_source.line_radius_m:.1f} m, against the plan's rough 35 m") in REPORT
    assert (f"the fit spans {la_source.radius_low_m:.1f} m to {la_source.radius_high_m:.1f} m. "
            f"The old 3-vertex method gave {la_source.min_3pt_radius_m:.1f} m.") in REPORT

    edge = CORNERS[CORNERS.apex_at_search_edge.astype(bool)].distance_m.astype(int).tolist()
    assert edge == [5100]
    assert f"Corner 5100 has its apex at the edge of the ±{OUTLINE_SEARCH_WINDOW_M:.0f} m search" in REPORT
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
    _check_results_row(_section("### Default method: inferred radii"), RESULTS, label, variant, value)


ALTERNATIVES = [
    ("### Alternative method: fitted outline radii", RESULTS_OUTLINE, "outline"),
    ("### Alternative method: driver's line radii", RESULTS_LINE, "line"),
]


@pytest.mark.parametrize("heading, frame, tag", ALTERNATIVES)
@pytest.mark.parametrize("label, variant, value", [
    ("Grip ×0.9", "grip", 0.9),
    (r"Grip ×1.0 \({tag} μ₀ = 0.7\)", "grip", 1.0),
    ("Grip ×1.3", "grip", 1.3),
    ("Spoiler SCz 0.2 m²", "spoiler", 0.2),
    ("Spoiler SCz 0.4 m²", "spoiler", 0.4),
])
def test_alternative_results_tables_match_the_csvs(heading, frame, tag, label, variant, value):
    _check_results_row(_section(heading), frame, label.format(tag=tag), variant, value)


def _check_results_row(section, frame, label, variant, value):
    pattern = rf"^\| {label} \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$"
    match = re.search(pattern, section, re.M)
    assert match, label
    assert float(match[1]) == round(_row(frame, variant, "petrol", value).lap_time_s, 1)
    for column, powertrain in zip((2, 3, 4, 5), ("petrol", "bev", "hybrid", "phev")):
        assert float(match[column]) == round(_row(frame, variant, powertrain, value).co2_eu, 1)


def test_baseline_feasibility_and_alternative_sentences_match_the_csvs():
    row = _row(RESULTS, "grip", "petrol", 1.0)
    assert f"{row.lap_time_s:.1f} s and {row.co2_eu:.1f} g CO2/km for Petrol" in REPORT
    frames = (RESULTS, RESULTS_OUTLINE, RESULTS_LINE)
    all_feasible = (
        all((f.short_steps == 0).all() for f in frames)
        and (COMPARISON.spoiler_short_steps == 0).all()
        and (COMPARISON.tyres_short_steps == 0).all()
    )
    assert all_feasible == ("`short_steps` is 0 everywhere" in REPORT)

    assert (CORNERS.outline_radius_m > CORNERS.inferred_radius_m).all()
    assert "Every fitted radius is larger than its inferred radius" in REPORT
    out_row = _row(RESULTS_OUTLINE, "grip", "petrol", 1.0)
    line_row = _row(RESULTS_LINE, "grip", "petrol", 1.0)
    assert (f"The Petrol lap takes {out_row.lap_time_s:.1f} s on the fitted radii and "
            f"{line_row.lap_time_s:.1f} s on the\ndriver's line, against {row.lap_time_s:.1f} s, "
            f"with EU CO2 of {out_row.co2_eu:.1f} and {line_row.co2_eu:.1f} against "
            f"{row.co2_eu:.1f} g CO2/km.") in REPORT
    for frame in (RESULTS_OUTLINE, RESULTS_LINE):
        petrol = frame[frame.powertrain == "petrol"]
        grip = petrol[petrol.variant == "grip"].sort_values("grip_factor")
        spoiler = petrol[petrol.variant == "spoiler"].sort_values("scz_m2")
        assert grip.lap_time_s.is_monotonic_decreasing and grip.co2_eu.is_monotonic_decreasing
        assert spoiler.lap_time_s.is_monotonic_increasing and spoiler.co2_eu.is_monotonic_increasing


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


COMPARISONS = [
    ("inferred", "### Inferred radii (default), matched on lap time", "under inferred radii"),
    ("outline", "### Outline radii, matched on lap time", "under fitted outline\nradii"),
    ("line", "### Driver's line radii, matched on lap time", "on the driver's line"),
]


@pytest.mark.parametrize("method, heading, phrase", COMPARISONS)
def test_comparison_tables_match_comparison_csv(method, heading, phrase):
    section = _section(heading)
    part = COMPARISON[COMPARISON.radius_method == method]
    assert len(part) == 4 * len([s for s in SCZS if s > 0])
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
            f"{petrol.matched_grip_factor.iloc[-1]:.3f} {phrase}") in REPORT
    assert (petrol.matched_grip_factor < 1.0).all()


def test_spoiler_costs_more_co2_than_matched_tyres_everywhere():
    assert (COMPARISON.delta_co2_eu > 0).all()
    assert "the spoiler still\nproduces higher EU CO2 than tyres for every powertrain" in REPORT


def test_required_limits_labels_and_matching_note_are_present():
    assert ("**Status: DRAFT (third pass by Claude Opus 5.5, second pass by Gemini 4 Neon, "
            "first pass by Claude), for the owner to review.**") in REPORT
    for required in ("**Radii:**", "**One line:**", "**Fixed braking:**", "**Fixed speeds elsewhere:**"):
        assert required in REPORT
    assert ("Matched on lap time, a provisional rule. Matching on the average corner speed or on one\n"
            "reference corner could change the result; the owner to choose.") in REPORT
    assert "—" not in REPORT
