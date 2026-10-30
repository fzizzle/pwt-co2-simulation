"""Phase 3: storage losses, the sizing rule, the sweep and the corner-speed hook."""

from dataclasses import replace

import numpy as np
import pytest

from pwt.model import fleet, simulate
from pwt.model.constants import STORAGE_EFFICIENCY
from pwt.model.conventions import harmonised
from pwt.model.profile import generate
from pwt.model.strategy import NelisStrategy, SocBandStrategy
from pwt.phase2 import scenario_cells
from pwt.sweep import MAX_C_RATE, best, cycles, sizing, sweep


@pytest.fixture(scope="module")
def cycle_map():
    return cycles()


@pytest.fixture(scope="module")
def frame():
    return sizing()


@pytest.mark.parametrize("strategy", [SocBandStrategy(), NelisStrategy("engine")])
def test_storage_loss_costs_fuel_on_every_cycle(cycle_map, strategy):
    for cyc in cycle_map.values():
        conv = harmonised(cyc.kind, "hybrid", 250.0)
        free = simulate(fleet.hybrid(0.6), cyc, conv, strategy)
        lossy = simulate(fleet.hybrid(0.6), cyc,
                         replace(conv, storage_efficiency=STORAGE_EFFICIENCY), strategy)
        assert lossy.headline["fuel_l_100km"] > free.headline["fuel_l_100km"]


def test_storage_loss_is_charged_both_ways():
    """Out at η drains 1/η; back in at η stores η, so a round trip keeps η²."""
    from pwt.model import Cycle

    speed = np.array([0.0, 20.0, 40.0, 40.0, 20.0, 0.0])
    cyc = Cycle("trip", "time", speed, t=np.arange(0.0, 60.0, 10.0))
    vehicle = fleet.plugin(0.5)
    conv = harmonised("time", "phev", 250.0)
    strategy = NelisStrategy("engine")
    free = simulate(vehicle, cyc, conv, strategy).steps
    lossy = simulate(vehicle, cyc, replace(conv, storage_efficiency=0.8), strategy).steps
    down_free = np.diff(free["batt_soc"])
    down_lossy = np.diff(lossy["batt_soc"])
    drive, regen = down_free < 0, down_free > 0
    assert drive.any() and regen.any()
    assert down_lossy[drive] == pytest.approx(down_free[drive] / 0.8)
    assert down_lossy[regen] == pytest.approx(down_free[regen] * 0.8)


def test_sized_hybrid_matches_the_fleet_within_the_mass_rule():
    for sized, sheet in ((fleet.sized_hybrid(1.5, 25, 1.0), fleet.hybrid()),
                         (fleet.sized_hybrid(15, 45), fleet.plugin())):
        assert sized.battery_wh == sheet.battery_wh
        assert sized.p_motor_w == sheet.p_motor_w
        assert sized.m_battery == sheet.m_battery
        assert sized.m_total == pytest.approx(sheet.m_total, abs=8.0)
    assert fleet.machine_mass_kg(35) == pytest.approx(100.0)
    assert fleet.machine_mass_kg(80) > fleet.machine_mass_kg(20)


def test_sweep_base_case_equals_the_scenario_figure(cycle_map):
    """With the fleet's own vehicles the sweep gives the scenario table's cells."""
    table = sweep({("hybrid", "base"): fleet.hybrid(), ("phev", "base"): fleet.plugin()},
                  {k: cycle_map[k] for k in ("nedc", "wltc")})
    cells = scenario_cells("storage losses")[0]
    for row in table.itertuples():
        cell = next(c for c in cells
                    if (c.powertrain, c.cycle, c.variant) == (row.powertrain, row.cycle, ""))
        assert row.co2_eu == pytest.approx(cell.co2_eu_grid)


def test_identity_corner_transform_reproduces_the_lap():
    petrol = fleet.petrol()
    plain = generate("eco", petrol)
    same = generate("eco", petrol, corner_speed=lambda _s, v: v)
    assert np.array_equal(plain.v_kph, same.v_kph)


def test_a_grippier_tyre_laps_faster():
    from pwt.model.profile import lap_time_s

    petrol = fleet.petrol()
    grip = generate("sport", petrol, corner_speed=lambda _s, v: v * 1.1**0.5)
    assert lap_time_s(grip) < lap_time_s(generate("sport", petrol))


def test_sizing_grid_is_complete_and_flags_impossible_packs(frame):
    assert not frame.isna()[["co2_eu", "co2_fr"]].any().any()
    assert (frame["motor_kw"] / frame["battery_kwh"] > MAX_C_RATE).eq(~frame["buildable"]).all()
    top = best(frame)
    assert (top["best motor (kW)"] / top["best battery (kWh)"] <= MAX_C_RATE).all()


def test_full_hybrid_optimum_is_inside_the_grid_on_wltc(frame):
    top = best(frame)
    row = top[(top["powertrain"] == "Full hybrid") & (top["cycle"] == "WLTC Class 3")].iloc[0]
    assert 1 < row["best battery (kWh)"] < 20


def test_mass_costs_fuel_when_the_battery_sits_idle(cycle_map):
    """Same strategy and motor, an empty pack that never helps: only its mass changes."""
    cyc = cycle_map["wltc"]
    conv = harmonised(cyc.kind, "hybrid", 250.0)
    fuel = [simulate(fleet.sized_hybrid(kwh, 40, 0.2), cyc, conv).headline["fuel_l_100km"]
            for kwh in (5, 10, 20)]
    assert fuel == sorted(fuel) and fuel[0] < fuel[-1]


def test_france_is_never_dirtier_than_the_eu_grid(frame):
    assert (frame["co2_fr"] <= frame["co2_eu"] + 1e-9).all()
