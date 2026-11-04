import numpy as np

from pwt.cornering import downforce_speed, grip_speed
from pwt.model import fleet
from pwt.model.profile import generate


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
    from pwt.model.profile import lap_time_s
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


def test_grip_and_spoiler_move_lap_time_the_expected_way():
    import pandas as pd
    from pathlib import Path

    frame = pd.read_csv(Path(__file__).resolve().parents[1] / "docs/study-c-results.csv")
    grip = frame[(frame.variant == "grip") & (frame.powertrain == "petrol")].sort_values("grip_factor")
    spoiler = frame[(frame.variant == "spoiler") & (frame.powertrain == "petrol")].sort_values("scz_m2")
    assert grip.lap_time_s.is_monotonic_decreasing
    assert spoiler.lap_time_s.is_monotonic_increasing
    assert not frame.co2_eu.isna().any()
    assert len(frame) == 4 * (5 + 5)
