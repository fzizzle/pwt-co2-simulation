"""Golden tests: the extractor must reproduce the cached values in the supplied workbooks.

These are the numbers Nelis's spreadsheets already report. Nothing here recomputes physics —
the assertions exist so that a change to the reader cannot silently start reading the wrong
row, which is the real risk given that every workbook puts its results at a different address.
"""

import math

import pytest

from pwt.catalog import CATALOG, course_file, find
from pwt.workbook import read_run

REL = 1e-4  # the workbooks' cached values are exact; 0.01% is ample slack for float round-trip


def approx(expected):
    return pytest.approx(expected, rel=REL)


# --- headline figures, one per powertrain -------------------------------------------------


def test_petrol_franco_eco():
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    assert run.consumption_l_per_100km == approx(10.2730)
    assert run.co2_g_per_km == approx(245.7298)
    assert run.co2_g_total == approx(1720.1086)


def test_bev_franco_eco():
    run = read_run(course_file("06 SPA Franco ELECTRIC ECO Driving.xlsx"))
    assert run.energy_wh_per_100km == approx(20477.0234)
    assert run.co2_g_per_km == approx(47.1369)
    # A battery-electric run reports no fuel consumption at all.
    assert run.consumption_l_per_100km is None


def test_hybrid_franco_eco():
    run = read_run(course_file("10 SPA Franco HYBRID engine ECO Driving.xlsx"))
    assert run.consumption_l_per_100km == approx(7.5752)
    assert run.co2_g_per_km == approx(181.1989)


def test_phev_franco_eco():
    run = read_run(course_file("09 SPA Franco PHYBRID engine ECO Driving.xlsx"))
    assert run.consumption_l_per_100km == approx(1.4297)
    assert run.co2_g_per_km == approx(34.1987)


# --- the label/unit collision that forced the (label, unit) key ---------------------------


def test_emission_rows_are_distinguished_by_unit_not_label():
    """Petrol r48 and r49 are both labelled "Total emission:" and differ only in unit.

    Keying totals by label alone would collapse them and lose one of the two figures.
    """
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    assert run.totals[("total emission", "g co2")] == approx(1720.1086)
    assert run.totals[("total emission", "g co2/km")] == approx(245.7298)


# --- values are passed through, not repaired ---------------------------------------------


def test_zero_totals_are_preserved_not_coerced():
    """NEDC PHEV reports 0 for consumption and both emission rows.

    The tool shows supplied data as-is, so a zero must survive extraction as a zero rather
    than becoming None, NaN or a substituted value.
    """
    run = read_run(course_file("34 NEDC PHYBRID engine.xlsx"))
    assert run.consumption_l_per_100km == 0.0
    assert run.co2_g_per_km == 0.0


def test_negative_energy_rows_are_preserved():
    """PHEV Franco eco nets regenerated against engine energy and goes negative."""
    run = read_run(course_file("09 SPA Franco PHYBRID engine ECO Driving.xlsx"))
    assert run.totals[("energy to move the car", "wh/100km")] == approx(-5284.6129)
    assert run.totals[("total fuel energy", "wh/100km")] == approx(-15098.8939)


# --- label normalisation across workbooks ------------------------------------------------


def test_case_variant_labels_resolve_to_one_key():
    """Franco writes "Total fuel energy", NEDC writes "Total Fuel energy"."""
    franco = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    nedc = read_run(course_file("33 NEDC PETROL Car.xlsx"))
    key = ("total fuel energy", "wh/100km")
    assert franco.totals[key] == approx(76086.6199)
    assert nedc.totals[key] == approx(39733.1088)


def test_nedc_petrol_has_phase_split_totals_others_lack():
    run = read_run(course_file("33 NEDC PETROL Car.xlsx"))
    assert run.totals[("urban consumption", "l/100km")] == approx(6.7885)
    assert run.totals[("extra urban consumption", "l/100km")] == approx(6.5267)


# --- parameters ---------------------------------------------------------------------------


def test_petrol_params_include_gear_ratios_and_masses():
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    assert run.params[("vehicle mass", "kg")] == approx(1300.0)
    assert run.params[("total mass", "kg")] == approx(1380.0)
    assert run.params[("gear ratio 1", "")] == approx(12.526)
    assert run.params[("gear ratio 5", "")] == approx(2.525)
    assert run.params[("scx", "m^2")] == approx(0.8339)


def test_bev_has_single_gear_ratio():
    run = read_run(course_file("06 SPA Franco ELECTRIC ECO Driving.xlsx"))
    assert run.params[("gear ratio", "")] == approx(6.218)
    assert run.params[("battery energy content", "kwh")] == approx(50.0)


# --- per-step trace -----------------------------------------------------------------------


def test_trace_columns_are_snake_case_and_typed():
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    for col in ("time_s", "distance_m", "altitude_m", "speed_kph", "gear", "engine_power_w"):
        assert col in run.trace.columns, f"missing {col}; got {list(run.trace.columns)}"
    assert run.trace["speed_kph"].iloc[0] == approx(90.0)
    assert run.trace["altitude_m"].iloc[0] == approx(418.0)
    assert run.trace["gear"].iloc[0] == 4


def test_francorchamps_lap_is_segments_not_uniform_steps():
    """The Spa lap is ~33 variable-length segments, not a per-second trace.

    Δ distances run 149, 71, 200, 440 m and so on, summing to the 7 km lap. The sheets'
    reported dimension of 113 rows counts the parameter block and formatting, not steps.
    """
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    assert 30 <= len(run.trace) <= 40
    assert run.trace["delta_distance_m"].iloc[1] == approx(149.0)
    assert run.trace["distance_m"].max() == approx(7000.0)


def test_nedc_trace_is_longer_than_the_lap_trace():
    nedc = read_run(course_file("33 NEDC PETROL Car.xlsx"))
    lap = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    assert len(nedc.trace) > 100
    assert len(nedc.trace) > 2 * len(lap.trace)


def test_blank_tail_rows_are_dropped():
    """Rows below the trace hold cached empty strings, not None; they must not be kept."""
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    # No row may be entirely empty.
    assert not run.trace.isna().all(axis=1).any()


def test_trace_has_no_all_nan_columns():
    """A column that is entirely NaN means the header was matched to the wrong block."""
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    empty = [c for c in run.trace.columns if run.trace[c].isna().all()]
    assert not empty, f"all-NaN trace columns: {empty}"


# --- catalog ------------------------------------------------------------------------------


def test_catalog_covers_twelve_runs():
    assert len(CATALOG) == 12
    assert {e.powertrain for e in CATALOG} == {"petrol", "bev", "hybrid", "phev"}
    assert {e.cycle for e in CATALOG} == {"franco_eco", "franco_sport", "nedc"}
    # every (powertrain, cycle) pair present exactly once
    pairs = [(e.powertrain, e.cycle) for e in CATALOG]
    assert len(set(pairs)) == 12


def test_catalog_files_all_exist():
    for entry in CATALOG:
        assert course_file(entry.filename).exists(), entry.filename


def test_catalog_overrides_wrong_workbook_titles():
    """Three supplied titles contradict their filename; identity comes from the catalog.

    `13 SPA Franco PETROL car SPORT Driving.xlsx` has a title cell reading "ECO", and
    `34 NEDC PHYBRID engine.xlsx` has one reading "FRANCORCHAMPS". Trusting the title would
    file these runs under the wrong cycle and driving style.
    """
    petrol_sport = find(powertrain="petrol", cycle="franco_sport")
    assert petrol_sport.style == "sport"
    assert "SPORT" in petrol_sport.filename

    nedc_phev = find(powertrain="phev", cycle="nedc")
    assert nedc_phev.cycle == "nedc"
    run = read_run(course_file(nedc_phev.filename))
    assert "FRANCORCHAMPS" in run.title_cell.upper()  # the workbook is mislabelled
    assert run.cycle == "nedc"  # the catalog wins


def test_every_catalogued_run_extracts():
    for entry in CATALOG:
        run = read_run(course_file(entry.filename))
        assert run.trace is not None and len(run.trace) > 0, entry.filename
        assert run.totals, entry.filename
        # Every run reports a CO2-per-km figure, even the unfinished NEDC PHEV (as 0).
        assert run.co2_g_per_km is not None and not math.isnan(run.co2_g_per_km), entry.filename


def test_summary_rows_are_skipped_and_counted():
    """Each lap workbook ends with a cumulative summary row and a unit-annotation row.

    They are not steps — the summary repeats the run's totals under the Δ headers, which
    would put a spurious final point on every plot. Skipping is recorded rather than silent.
    """
    run = read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    assert run.summary_rows_skipped == 1
    assert len(run.trace) == 32  # the Spa lap is 32 segments


def test_step_counts_are_exact_across_all_runs():
    """Francorchamps runs are 32 segments; NEDC runs are 105 steps (0-1240 s)."""
    for entry in CATALOG:
        run = read_run(course_file(entry.filename))
        expected = 32 if entry.cycle.startswith("franco") else 105
        assert len(run.trace) == expected, f"{entry.filename}: {len(run.trace)} rows"


def test_electric_nedc_sums_row_is_not_a_step():
    """`32`'s sums row fills exactly half its columns; it once passed as a 106th step at
    1240 s with the whole cycle's distance."""
    run = read_run(course_file("32 NEDC ELECTRIC.xlsx"))
    assert run.summary_rows_skipped == 1
    assert run.trace["delta_distance_m"].max() < 1000  # the sums row held 11 222 m
