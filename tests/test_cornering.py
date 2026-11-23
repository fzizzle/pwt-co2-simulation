import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pwt.cornering import (
    FIT_HALF_WINDOW_M,
    G,
    MATCH_RULES,
    MU0,
    OUTLINE_SPACING_M,
    RADIUS_METHODS,
    RESULT_FILES,
    TRACK_HALF_WIDTH_M,
    corner_table,
    downforce_speed,
    fit_circle,
    grip_speed,
    outline_corner_radii,
    resample_closed,
    results,
    spoiler_vs_tyres,
)
from pwt.model import fleet
from pwt.model.profile import generate, lap_time_s, track


def test_unchanged_grip_reproduces_the_lap():
    car = fleet.petrol()
    lap = generate("sport", car, corner_speed=grip_speed(1))
    assert np.array_equal(lap.v_kph, generate("sport", car).v_kph)


def test_no_downforce_reproduces_the_lap():
    car = fleet.petrol()
    lap = generate("sport", car, corner_speed=downforce_speed(0.8, 0.0, car.m_total))
    assert np.allclose(lap.v_kph, generate("sport", car).v_kph)


def test_more_downforce_never_slows_a_corner():
    speeds = [downforce_speed(0.8, scz, 1300)(0, 15.0) for scz in (0, 0.2, 0.5, 1.0)]
    assert speeds == sorted(speeds)


def test_plan_baseline_reproduces_from_the_code():
    """Plan baseline: sport lap 235.1 s, petrol 385.2 g CO2/km, 12 corners with a set speed."""
    from pwt.sweep import sweep

    car = fleet.petrol()
    calls = []

    def counting(s, v):
        calls.append(s)
        return grip_speed(1)(s, v)

    lap = generate("sport", car, corner_speed=counting)
    assert round(lap_time_s(lap), 1) == 235.1
    assert len(calls) == 12
    co2 = sweep({("petrol",): car}, {"franco_sport_generated": lap}).co2_eu.iloc[0]
    assert round(co2, 1) == 385.2


@pytest.mark.parametrize("line", [False, True])
def test_outline_radii_cover_every_set_speed_corner_without_gaps(line):
    corners = track("sport").corners
    radii = outline_corner_radii(line=line)
    assert set(radii) == set(corners)
    assert len(radii) == 12
    for dist, radius in radii.items():
        assert math.isfinite(radius) and radius > 0, (dist, radius)


@pytest.mark.parametrize("radius, vertices", [(20.0, 10), (35.0, 16), (100.0, 20)])
def test_fitted_radius_of_a_coarse_synthetic_circle_is_within_2_percent(radius, vertices):
    """A circle drawn with few vertices, resampled every 5 m and fitted over +/-40 m."""
    angle = np.linspace(0.0, 2.0 * np.pi, vertices + 1)
    x, y = radius * np.cos(angle), radius * np.sin(angle)
    s, xs, ys = resample_closed(x, y, OUTLINE_SPACING_M)
    assert np.allclose(np.diff(s), s[1] - s[0])
    near = np.abs((s - s[len(s) // 3] + s[-1] / 2) % s[-1] - s[-1] / 2) <= FIT_HALF_WINDOW_M
    fitted = fit_circle(xs[near], ys[near])[2]
    assert abs(fitted / radius - 1) < 0.02, fitted


def test_drivers_line_radius_is_never_below_the_fitted_radius():
    table = corner_table()
    assert (table.line_radius_m >= table.outline_radius_m).all()
    assert np.allclose(table.line_radius_m - table.outline_radius_m, TRACK_HALF_WIDTH_M)
    assert (table.implied_mu_low <= table.implied_mu_outline + 1e-12).all()
    assert (table.implied_mu_outline <= table.implied_mu_high + 1e-12).all()


def test_corner_table_reports_implied_mu_for_every_corner():
    table = corner_table()
    assert len(table) == 12
    columns = ["inferred_radius_m", "outline_radius_m", "line_radius_m", "implied_mu_outline",
               "implied_mu_line", "implied_mu_low", "implied_mu_high"]
    assert not table[columns].isna().any().any()
    v_ms = table["template_speed_kph"] / 3.6
    assert np.allclose(table["implied_mu_outline"], v_ms ** 2 / (G * table["outline_radius_m"]))
    assert np.allclose(table["inferred_radius_m"], v_ms ** 2 / (MU0 * G))


def test_outline_method_agrees_at_baseline_and_more_grip_never_slows_lap():
    car = fleet.petrol()
    radii = outline_corner_radii()
    lap_grip_1 = generate("sport", car, corner_speed=grip_speed(1.0, radii=radii, mu0=MU0))
    lap_scz_0 = generate("sport", car, corner_speed=downforce_speed(MU0, 0.0, car.m_total, radii=radii))
    assert np.allclose(lap_grip_1.v_kph, lap_scz_0.v_kph)

    for method in RADIUS_METHODS:
        r_map = None if method == "inferred" else outline_corner_radii(line=method == "line")
        times = [
            lap_time_s(generate("sport", car, corner_speed=grip_speed(g, radii=r_map, mu0=MU0)))
            for g in (0.9, 1.0, 1.1, 1.2, 1.3)
        ]
        assert times == sorted(times, reverse=True)


def test_invalid_radius_method_or_match_rule_is_rejected():
    with pytest.raises(ValueError, match="radius_method"):
        results(radius_method="unknown")
    with pytest.raises(ValueError, match="match_by"):
        spoiler_vs_tyres(match_by="unknown")
    assert "lap_time" in MATCH_RULES


@pytest.mark.parametrize("radius_method", RADIUS_METHODS)
def test_lap_time_match_really_matches_within_0_1_s(radius_method):
    comp = spoiler_vs_tyres(sczs=(0.2, 0.4), radius_method=radius_method, match_by="lap_time")
    assert len(comp) == 4 * 2
    assert (comp["lap_time_diff_s"].abs() < 0.1).all()
    assert not comp[["spoiler_co2_eu", "tyres_co2_eu", "delta_co2_eu"]].isna().any().any()


def test_grip_and_spoiler_move_lap_time_the_expected_way():
    docs = Path(__file__).resolve().parents[1] / "docs"
    for filename in RESULT_FILES.values():
        frame = pd.read_csv(docs / filename)
        grip = frame[(frame.variant == "grip") & (frame.powertrain == "petrol")].sort_values("grip_factor")
        spoiler = frame[(frame.variant == "spoiler") & (frame.powertrain == "petrol")].sort_values("scz_m2")
        assert grip.lap_time_s.is_monotonic_decreasing
        assert spoiler.lap_time_s.is_monotonic_increasing
        assert not frame.co2_eu.isna().any()
        assert not frame.co2_fr.isna().any()
        assert len(frame) == 4 * (5 + 5)
