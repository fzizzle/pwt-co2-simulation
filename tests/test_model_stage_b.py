"""Stage B: each change to the model, pinned against the workbook-exact result."""

from dataclasses import replace

import pytest

from pwt.catalog import course_file
from pwt.model import Cycle, Vehicle, from_workbook, simulate
from pwt.model.constants import CO2_G_PER_G_PETROL, FUEL_G_PER_WH
from pwt.model.conventions import harmonised
from pwt.workbook import read_run

PETROL_ECO = "07 SPA Franco PETROL car ECO Driving.xlsx"


def _inputs(name, kind):
    run = read_run(course_file(name))
    return run, Vehicle.from_run(run), Cycle.from_run(run, kind)


# --- Task 7: cited constants --------------------------------------------------------------


def test_constants():
    assert FUEL_G_PER_WH == pytest.approx(0.081264, rel=1e-4)
    assert CO2_G_PER_G_PETROL == pytest.approx(3.06999, rel=1e-4)


def test_harmonised_petrol_eco_changes_only_the_constants():
    """`07` already follows the harmonised shifts and effective mass, and never stops, so
    fuel scales by exactly the heating-value ratio and CO2 by that times the CO2-per-gram."""
    run, vehicle, cycle = _inputs(PETROL_ECO, "distance")
    exact = from_workbook(run).headline
    harm = simulate(vehicle, cycle, harmonised("distance", "petrol", 250)).headline
    ratio = FUEL_G_PER_WH / 0.0909
    assert harm["fuel_l_100km"] == pytest.approx(exact["fuel_l_100km"] * ratio, rel=1e-12)
    co2_ratio = ratio * CO2_G_PER_G_PETROL / (2392 / vehicle.fuel_density)
    assert harm["co2_g_km"] == pytest.approx(exact["co2_g_km"] * co2_ratio, rel=1e-12)
    assert harm["fuel_l_100km"] == pytest.approx(9.1840, rel=1e-4)
    assert harm["co2_g_km"] == pytest.approx(203.002, rel=1e-5)


def test_harmonised_density_moves_litres_not_co2():
    run, vehicle, cycle = _inputs(PETROL_ECO, "distance")
    conv = harmonised("distance", "petrol", 250)
    a = simulate(vehicle, cycle, conv).headline
    b = simulate(replace(vehicle, fuel_density=750), cycle, conv).headline
    assert b["co2_g_km"] == pytest.approx(a["co2_g_km"], rel=1e-12)
    assert b["fuel_l_100km"] == pytest.approx(a["fuel_l_100km"] * 720 / 750, rel=1e-12)


def test_harmonised_electric_uses_the_real_lap_distance():
    """The Francorchamps EV sheets divide CO2 by 6.69 km and energy by a hard-coded 7 km."""
    run, vehicle, cycle = _inputs("06 SPA Franco ELECTRIC ECO Driving.xlsx", "distance")
    harm = simulate(vehicle, cycle, harmonised("distance", "bev", 250))
    km = harm.steps["delta_distance_m"].sum() / 1000
    assert harm.headline["co2_g_km"] == pytest.approx(
        harm.steps["energy_wh"].sum() * 0.25 / km, rel=1e-12
    )
