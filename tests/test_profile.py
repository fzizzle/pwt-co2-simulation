"""Francorchamps laps generated from the assignment sheet's rules."""

import numpy as np
import pytest

from dataclasses import replace

from pwt.model import fleet, simulate
from pwt.model.conventions import harmonised
from pwt.model.profile import G, STRAIGHT_CORNERS, generate, lap_time_s, track


@pytest.fixture(scope="module", params=["eco", "sport"])
def lap(request):
    return request.param, generate(request.param, fleet.petrol())


def test_corners_are_boundary_conditions(lap):
    mode, cycle = lap
    for dist, speed in track(mode).corners.items():
        i = int(np.argmin(np.abs(cycle.s - dist)))
        assert cycle.v_kph[i] / 3.6 <= speed + 1e-9


def test_corners_16_and_17_are_straights():
    corners = track("sport").corners
    assert 5700.0 not in corners and 6000.0 not in corners
    assert STRAIGHT_CORNERS == {"16", "17"}


def test_braking_never_exceeds_the_rule(lap):
    mode, cycle = lap
    v = cycle.v_kph / 3.6
    decel = (v[:-1] ** 2 - v[1:] ** 2) / (2 * np.diff(cycle.s))
    assert decel.max() <= {"eco": 0.4, "sport": 0.6}[mode] * G + 1e-9


def test_eco_rules():
    _, cycle = "eco", generate("eco", fleet.petrol())
    v = cycle.v_kph / 3.6
    assert cycle.v_kph.max() <= 90 + 1e-9
    accel = (v[1:] ** 2 - v[:-1] ** 2) / (2 * np.diff(cycle.s))
    assert accel.max() <= 100 / 3.6 / 20 + 1e-9


def test_the_lap_closes(lap):
    _, cycle = lap
    assert cycle.v_kph[0] == cycle.v_kph[-1]
    assert cycle.s[-1] == 7000


def test_the_petrol_car_can_drive_it(lap):
    """The point of generating the lap: no step asks more than the full-load curve."""
    _, cycle = lap
    vehicle = fleet.petrol()
    conv = replace(harmonised("distance", "petrol", 250), capability=True)
    assert (simulate(vehicle, cycle, conv).steps["shortfall_w"] == 0).all()


def test_lap_times(lap):
    mode, cycle = lap
    assert lap_time_s(cycle) == pytest.approx({"eco": 310.3, "sport": 235.1}[mode], abs=0.1)
    assert lap_time_s(cycle) < track(mode).template_time_s
