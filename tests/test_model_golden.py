"""The Python model must reproduce every workbook: totals and every per-step column.

Nineteen runs: the twelve supplied workbooks and the seven `pwt.derived` builds. Nothing in
stage B may change these results — workbook-exact is always reachable via `from_workbook`.
"""

import numpy as np
import pytest

from pwt.catalog import CATALOG, course_file
from pwt.derived import SPECS, read_derived
from pwt.model import Cycle, Vehicle, from_workbook
from pwt.model.conventions import NEDC_SHIFTS, conventions_for
from pwt.workbook import read_run

REL, ABS = 1e-6, 1e-9

#: Rows added below the parameter block by `pwt.derived`, which the model also reports.
_DERIVED_LABELS = (
    " distance", " consumption", " emission", " energy use",
    "final state of charge", "battery energy used", "grid emission",
)

#: Cells the sheets hard-code over their own formula, which nothing downstream reads. Sheet
#: row 24's engine torque is 0 in all six Francorchamps engine files although the formula
#: gives ~140 Nm.
_SHEET_OVERRIDES = {("engine_torque_nm", 21)}


RUNS = [pytest.param(e.filename, id=e.filename[:2]) for e in CATALOG] + [
    pytest.param(s.filename, id=s.filename.removesuffix(".xlsx")) for s in SPECS
]


def _load(name):
    if name[:2].isdigit():
        return read_run(course_file(name))
    return read_derived(next(s for s in SPECS if s.filename == name))


@pytest.mark.parametrize("name", RUNS)
def test_totals_match_the_workbook(name):
    run = _load(name)
    result = from_workbook(run)
    expected = dict(run.totals)
    if not name[:2].isdigit():
        expected |= {
            k: v for k, v in run.params.items() if any(lbl in k[0] for lbl in _DERIVED_LABELS)
        }
    assert expected, name
    for key, value in expected.items():
        assert key in result.totals, f"{name}: model does not report {key}"
        assert result.totals[key] == pytest.approx(value, rel=REL, abs=ABS), (name, key)


@pytest.mark.parametrize("name", RUNS)
def test_every_step_matches_the_workbook(name):
    run = _load(name)
    steps = from_workbook(run).steps
    trace = run.trace
    if conventions_for(name).eff_mass == "total":
        # `33` and its WLTC build call their per-step distance "Distance (m)".
        trace = trace.rename(columns={"distance_m": "delta_distance_m"})
    shared = [c for c in trace.columns if c in steps.columns]
    assert len(shared) >= 15, (name, shared)
    assert len(steps) == len(trace), name
    for column in shared:
        # Row 0 is the initial state; the Francorchamps sheets fill it with copies of the
        # last row, which no formula reads.
        expected = trace[column].to_numpy(float)[1:]
        actual = steps[column].to_numpy(float)[1:]
        for row in range(len(expected)):
            if (column, row + 1) in _SHEET_OVERRIDES and name[:2] in {
                "07", "13", "10", "15", "09", "14"
            }:
                continue
            if np.isnan(expected[row]):
                continue
            assert actual[row] == pytest.approx(expected[row], rel=REL, abs=ABS), (
                name, column, row + 1,
            )


# --- inputs -------------------------------------------------------------------------------


@pytest.mark.parametrize("name", [e.filename for e in CATALOG])
def test_effective_masses_match_the_sheet(name):
    """The model computes effective mass from components; the sheet's cached cells check it."""
    run = read_run(course_file(name))
    vehicle = Vehicle.from_run(run)
    conv = conventions_for(name)
    cached = {k[0]: v for k, v in run.params.items() if k[0].startswith("effective mass gear")}
    for label, value in cached.items():
        gear = label.removeprefix("effective mass gear").strip()
        ratio = vehicle.ratios[int(gear) - 1] if gear else vehicle.ratios[0]
        assert vehicle.effective_mass(ratio, conv.eff_mass) == pytest.approx(value, rel=1e-12)


def test_vehicle_reads_the_active_efficiency_curve():
    """Hybrid sheets lay out three curves across B/C/D; column C is the one in use."""
    vehicle = Vehicle.from_run(read_run(course_file("10 SPA Franco HYBRID engine ECO Driving.xlsx")))
    assert (vehicle.a1, vehicle.a2, vehicle.a3) == (-1.0778, 1.7543, 0.3097)  # atkinson
    assert vehicle.family == "hybrid" and vehicle.battery_wh == 1500


def test_cycles():
    nedc = Cycle.from_run(read_run(course_file("33 NEDC PETROL Car.xlsx")), "time")
    assert len(nedc) == 105 and nedc.t[-1] == 1240
    assert set(nedc.phase) == {"Urban", "Extra urban"}
    assert len(Cycle.wltc_class3()) == 1801


def test_conventions_record_the_disagreements():
    assert conventions_for("33 NEDC PETROL Car.xlsx").shift_kph == NEDC_SHIFTS
    assert conventions_for("35 NEDC HYBRID engine.xlsx").fictive_recharge
    assert not conventions_for("34 NEDC PHYBRID engine.xlsx").fictive_recharge
    assert conventions_for("WLTC3 PHYBRID CS.xlsx").soc_min == 0.23
