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
        harm.steps["energy_wh"].sum() * 0.25 / km / 0.9, rel=1e-12  # 90 % charger
    )


# --- Task 8: engine capability ------------------------------------------------------------

PETROL_SPORT = "13 SPA Franco PETROL car SPORT Driving.xlsx"


def _capable(name, kind, rated=74_000.0):
    run, vehicle, cycle = _inputs(name, kind)
    from pwt.model.conventions import conventions_for

    conv = replace(conventions_for(name), capability=True)
    return simulate(replace(vehicle, p_rated_w=rated), cycle, conv), run


@pytest.mark.parametrize("name, flat_over", [(PETROL_ECO, 1), (PETROL_SPORT, 7)])
def test_shortfall_covers_every_step_over_the_rating(name, flat_over):
    result, run = _capable(name, "distance")
    demand = from_workbook(run).steps["engine_power_drivetrain_w"]
    assert (demand[1:] > 74_000).sum() == flat_over
    short = result.steps["shortfall_w"]
    # Every step over the flat rating is short; the rpm-dependent curve can only add steps.
    assert (short[demand > 74_000] > 0).all()
    assert (short > 0).sum() >= flat_over


def test_delivered_power_never_exceeds_the_curve():
    from pwt.model.powertrains import full_load_w

    result, _ = _capable(PETROL_SPORT, "distance")
    steps = result.steps
    limit = full_load_w(result.vehicle, steps["engine_speed_rads"].to_numpy())
    assert (steps["engine_power_drivetrain_w"].to_numpy() <= limit + 1e-9).all()


def test_capability_lowers_the_hybrid_engine_share_only():
    result, run = _capable("15 SPA Franco HYBRID engine SPORT Driving.xlsx", "distance")
    exact = from_workbook(run)
    assert (result.steps["shortfall_w"] > 0).any()
    assert (result.steps["energy_wh"] <= exact.steps["energy_wh"] + 1e-9).all()
    assert result.steps["batt_soc"].equals(exact.steps["batt_soc"])


def test_capability_is_off_for_the_workbook_exact_path():
    result = from_workbook(read_run(course_file(PETROL_SPORT)))
    assert "shortfall_w" not in result.steps


# --- Task 9: charge-sustaining full hybrid ------------------------------------------------


def _wltc_hybrid(strategy=None, soc0=0.6):
    from pwt.derived import SPECS, read_derived
    from pwt.model.conventions import conventions_for

    run = read_derived(next(s for s in SPECS if s.filename == "WLTC3 HYBRID.xlsx"))
    vehicle = replace(Vehicle.from_run(run), soc0=soc0)
    return simulate(vehicle, Cycle.from_run(run, "time"), conventions_for(run.source_file),
                    strategy)


def test_soc_band_holds_the_battery_in_the_band():
    from pwt.model.strategy import SocBandStrategy

    soc = _wltc_hybrid(SocBandStrategy(0.5, 0.7)).steps["batt_soc"]
    assert soc.min() >= 0.45 and soc.max() <= 0.75
    assert abs(soc.iloc[-1] - soc.iloc[0]) <= 0.1


def test_soc_band_beats_the_sheet_rule_from_the_same_start():
    from pwt.model.strategy import SocBandStrategy

    band = _wltc_hybrid(SocBandStrategy()).headline["fuel_l_100km"]
    nelis = _wltc_hybrid().headline["fuel_l_100km"]
    assert band == pytest.approx(5.6115, rel=1e-4)
    assert nelis == pytest.approx(7.2211, rel=1e-4)


def test_best_efficiency_load_is_the_curve_maximum():
    from pwt.model.strategy import SocBandStrategy

    _, vehicle, _ = _inputs("10 SPA Franco HYBRID engine ECO Driving.xlsx", "distance")
    best = SocBandStrategy().best_load_w(vehicle)
    assert vehicle.efficiency(best) >= vehicle.efficiency(best * 0.95)
    assert vehicle.efficiency(best) >= vehicle.efficiency(best * 1.05)


def test_the_sheets_read_hybrid_efficiency_at_the_whole_demand():
    """The engine supplies (1 − share) of the demand, but its efficiency is read at all of it,
    which flatters it whenever the motor helps. Reading it at the share costs 16.5 % fuel on
    the eco lap."""
    from pwt.model.conventions import conventions_for
    from pwt.model.strategy import NelisStrategy

    name = "10 SPA Franco HYBRID engine ECO Driving.xlsx"
    _, vehicle, cycle = _inputs(name, "distance")
    conv = conventions_for(name)
    sheet = simulate(vehicle, cycle, conv, NelisStrategy("demand")).headline["fuel_l_100km"]
    honest = simulate(vehicle, cycle, conv, NelisStrategy("engine")).headline["fuel_l_100km"]
    assert sheet == pytest.approx(7.5752, rel=1e-4)
    assert honest == pytest.approx(8.8270, rel=1e-4)


def test_soc_band_charging_stays_under_the_full_load_curve():
    """Charging targets the best-efficiency load only as far as the engine can deliver it."""
    from pwt.model.conventions import conventions_for
    from pwt.model.strategy import NelisStrategy, SocBandStrategy

    def short_steps(strategy):
        from pwt.derived import SPECS, read_derived

        run = read_derived(next(s for s in SPECS if s.filename == "WLTC3 HYBRID.xlsx"))
        vehicle = replace(Vehicle.from_run(run), soc0=0.6)
        conv = replace(conventions_for(run.source_file), capability=True)
        steps = simulate(vehicle, Cycle.from_run(run, "time"), conv, strategy).steps
        return int((steps["shortfall_w"] > 0).sum())

    assert short_steps(SocBandStrategy()) <= short_steps(NelisStrategy("engine"))


# --- Task 10: assignment-sheet vehicles and the TD1 checkpoint -----------------------------


def test_assignment_vehicles_match_the_sheet():
    from pwt.model import fleet

    assert fleet.petrol().m_total == 1280 + 80
    assert fleet.electric().m_vehicle + fleet.electric().m_battery == 1460
    assert fleet.electric().battery_wh == 22_000
    assert fleet.hybrid().m_machine == 100 and fleet.hybrid().p_motor_w == 25_000
    assert fleet.plugin().battery_wh == 15_000 and fleet.plugin().m_battery == 100
    assert fleet.petrol().p_rated_w == 74_000 and fleet.petrol().fuel_density == 750


def test_phase2_scenarios():
    from pwt.phase2 import scenario_cells

    def co2(rows, powertrain, cycle):
        return next(c for c in rows if (c.powertrain, c.cycle, c.variant)
                    == (powertrain, cycle, "")).co2_eu_grid

    exact, _ = scenario_cells("exact")
    harm, _ = scenario_cells("harmonised")
    stage_b, shortfall = scenario_cells("stage B")
    assert co2(exact, "petrol", "franco_eco") == pytest.approx(245.7298, rel=1e-6)
    assert co2(harm, "petrol", "franco_eco") == pytest.approx(203.0023, rel=1e-6)
    # The electric car moves only by the charger loss: its regen cap and grid factor stay.
    assert co2(harm, "bev", "franco_sport") == pytest.approx(
        co2(exact, "bev", "franco_sport") / 0.9
    )
    assert co2(stage_b, "hybrid", "wltc") < co2(harm, "hybrid", "wltc")
    assert shortfall[("petrol", "franco_sport")][0] == 15  # steps short by over 0.1 kW
