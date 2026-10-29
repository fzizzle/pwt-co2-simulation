"""The workbooks `pwt.derived` builds: faithful to their templates, and their results locked.

The golden figures below are what the committed workbooks in `data/derived/` report. If a
change to `pwt.derived` moves one, rebuild (`python -m pwt.derived`), check why, and update
the figure deliberately.
"""

import shutil

import pytest

from pwt.catalog import course_file
from pwt.derived import (
    SHIFT_KPH,
    SPECS,
    DerivedSpec,
    _gear_formula,
    build,
    read_derived,
    wltc_class3,
    wltc_phase_distances_m,
)
from pwt.workbook import read_run

REL = 1e-4


def approx(expected):
    return pytest.approx(expected, rel=REL)


def spec(filename):
    return next(s for s in SPECS if s.filename == filename)


# --- the trace ----------------------------------------------------------------------------


def test_wltc_class3_is_1800_seconds_in_four_phases():
    trace = wltc_class3()
    assert len(trace) == 1801
    assert trace["time_s"].iloc[-1] == 1800
    assert list(trace["phase"].unique()) == ["Low", "Medium", "High", "Extra-high"]
    assert trace["speed_kph"].max() == pytest.approx(131.3)


@pytest.mark.parametrize("filename", [s.filename for s in SPECS if s.cycle == "wltc"])
def test_wltc_phase_distances_match_the_supplied_file(filename):
    """The sheets' per-step distance is end speed × Δt; over 1 s steps that start and end at
    rest it sums to the file's own phase distances."""
    run = read_derived(spec(filename))
    for phase, metres in wltc_phase_distances_m().items():
        assert run.params[(f"{phase.lower()} distance", "m")] == approx(metres)


def test_gear_formula_matches_the_supplied_nested_if():
    assert _gear_formula("J4", SHIFT_KPH) == (
        "=IF(J4=0,0,IF(J4<=35,1,IF(J4<=57,2,IF(J4<=82,3,IF(J4<=115,4,5)))))"
    )


# --- results ------------------------------------------------------------------------------


def test_wltc_petrol():
    run = read_derived(spec("WLTC3 PETROL.xlsx"))
    assert run.consumption_l_per_100km == approx(7.4336)
    assert run.co2_g_per_km == approx(177.8112)


def test_wltc_electric():
    run = read_derived(spec("WLTC3 ELECTRIC.xlsx"))
    assert run.energy_wh_per_100km == approx(17791.4337)
    assert run.consumption_l_per_100km is None


def test_wltc_hybrid():
    run = read_derived(spec("WLTC3 HYBRID.xlsx"))
    assert run.consumption_l_per_100km == approx(6.5833)
    assert run.co2_g_per_km == approx(157.4722)


def test_nedc_phev_charge_depleting_is_all_electric():
    """The supplied 34's zero fuel is a result: the battery never reaches the 23 % threshold."""
    run = read_derived(spec("NEDC PHYBRID CD.xlsx"))
    assert run.consumption_l_per_100km == 0
    assert run.params[("final state of charge", "")] == approx(0.7797)
    assert run.params[("battery energy used", "wh")] == approx(1602.409)
    assert run.params[("grid emission eu", "g co2/km")] == approx(35.6972)


@pytest.mark.parametrize("filename", ["NEDC PHYBRID CS.xlsx", "WLTC3 PHYBRID CS.xlsx"])
def test_phev_charge_sustaining_holds_the_battery(filename):
    run = read_derived(spec(filename))
    assert run.params[("final state of charge", "")] == pytest.approx(0.23, abs=0.015)
    assert run.consumption_l_per_100km > 5


def test_nedc_phev_charge_sustaining():
    run = read_derived(spec("NEDC PHYBRID CS.xlsx"))
    assert run.consumption_l_per_100km == approx(5.9640)
    assert run.co2_g_per_km == approx(142.6586)


# --- faithfulness -------------------------------------------------------------------------

TEMPLATES = (
    "33 NEDC PETROL Car.xlsx",
    "32 NEDC ELECTRIC.xlsx",
    "35 NEDC HYBRID engine.xlsx",
    "34 NEDC PHYBRID engine.xlsx",
)


@pytest.mark.skipif(
    not (shutil.which("soffice") or shutil.which("libreoffice")),
    reason="rebuilding needs LibreOffice",
)
def test_rebuilding_a_template_on_its_own_trace_reproduces_it(tmp_path):
    """The derived workbooks are only as good as the fill-down; prove it on known answers."""
    specs = tuple(
        DerivedSpec(f"rebuilt {name}", name, "?", "nedc", "regulatory", "rebuild")
        for name in TEMPLATES
    )
    build(specs, tmp_path)
    for name in TEMPLATES:
        supplied = read_run(course_file(name))
        rebuilt = read_run(tmp_path / f"rebuilt {name}")
        assert supplied.totals, name
        for key, value in supplied.totals.items():
            assert rebuilt.totals[key] == pytest.approx(value, rel=1e-9, abs=1e-9), (name, key)
        assert rebuilt.trace.shape == supplied.trace.shape, name
