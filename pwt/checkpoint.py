"""The Phase 1 checkpoint: every powertrain on every cycle, from Nelis's sheets.

Supplied workbooks for NEDC and Francorchamps, `pwt.derived` for WLTC and for the plug-in
hybrid's charge-sustaining runs. Figures are what the sheets compute; the only arithmetic
added here is unit conversion, battery energy from the state-of-charge trace, and the
plug-in hybrid's NEDC weighting.

    python -m pwt.checkpoint      # print the tables as Markdown (needs LibreOffice for the
                                  # variants table)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES, find
from pwt.derived import (
    GRID_G_PER_KWH,
    PHEV_ENGINE_SOC,
    SHIFT_KPH,
    SPECS,
    DerivedSpec,
    Variant,
    build,
    read_derived,
    run_variants,
)
from pwt.catalog import course_file
from pwt.schema import Run
from pwt.workbook import read_run

CYCLE_ORDER = ("nedc", "franco_eco", "franco_sport", "wltc")
CYCLE_LABELS = {**CYCLE_NAMES, "wltc": "WLTC Class 3"}

#: UN ECE R101's averaging distance for an externally chargeable hybrid on NEDC: fuel is
#: weighted (De·C1 + Dav·C2) / (De + Dav), De the electric range, C1 charge-depleting, C2
#: charge-sustaining.
R101_DAV_KM = 25.0


@dataclass(slots=True)
class Cell:
    powertrain: str
    cycle: str
    variant: str  # "" for the headline figure; "cd" / "cs" for plug-in hybrid detail
    fuel_l_100km: float | None
    battery_kwh_100km: float | None
    co2_reported: float | None
    co2_eu_grid: float | None
    source: str


def _km(run: Run) -> float:
    # Only called for the hybrids, whose sheets all carry a per-step Δ Distance column.
    return run.trace["delta_distance_m"].sum() / 1000


def _battery_wh(run: Run) -> float | None:
    """Energy drawn from the battery over the trace, from its state of charge."""
    if "batt_soc" not in run.trace:
        return None
    capacity = run.params[("batt energy content", "wh")]
    soc = run.trace["batt_soc"].dropna()
    return capacity * (soc.iloc[0] - soc.iloc[-1])


def make_cell(powertrain: str, cycle: str, variant: str, fuel: float | None,
              battery: float | None, co2: float, source: str) -> Cell:
    """A cell from its figures, adding the EU-grid CO2 of any electricity from outside."""
    if powertrain == "bev":
        eu = battery * GRID_G_PER_KWH["EU"] / 100
    elif powertrain == "phev":
        eu = co2 + battery * GRID_G_PER_KWH["EU"] / 100
    else:
        # The full hybrid buys back its battery's charge with fuel, so no electricity comes
        # from outside.
        battery, eu = None, co2
    return Cell(powertrain, cycle, variant, fuel, battery, co2, eu, source)


def _cell(run: Run, cycle: str, variant: str = "", source: str = "workbooks") -> Cell:
    if source == "model":
        from pwt.model import from_workbook

        h = from_workbook(run).headline
        fuel, battery, co2 = h["fuel_l_100km"], h["battery_kwh_100km"], h["co2_g_km"]
    else:
        fuel, co2 = run.consumption_l_per_100km, run.co2_g_per_km
        battery = None
        if run.powertrain == "bev":
            battery = run.energy_wh_per_100km / 1000
        elif run.powertrain == "phev":
            battery = _battery_wh(run) / _km(run) / 10
    return make_cell(run.powertrain, cycle, variant, fuel, battery, co2, run.source_file)


def _r101(cd: Cell, cs: Cell, usable_wh: float) -> Cell:
    electric_range_km = usable_wh / (cd.battery_kwh_100km * 10)
    weight = lambda c1, c2: (  # noqa: E731
        (electric_range_km * c1 + R101_DAV_KM * c2) / (electric_range_km + R101_DAV_KM)
    )
    return Cell(
        "phev", cd.cycle, "",
        weight(cd.fuel_l_100km, cs.fuel_l_100km),
        weight(cd.battery_kwh_100km, cs.battery_kwh_100km),
        weight(cd.co2_reported, cs.co2_reported),
        weight(cd.co2_eu_grid, cs.co2_eu_grid),
        f"R101 weighting of {cd.source} and {cs.source}, De = {electric_range_km:.1f} km",
    )


def cells(source: str = "workbooks") -> list[Cell]:
    """Every headline cell, from the workbooks' cached values or from `pwt.model`."""
    out: list[Cell] = []
    for cycle in ("franco_eco", "franco_sport"):
        for powertrain in POWERTRAIN_NAMES:
            entry = find(powertrain=powertrain, cycle=cycle)
            out.append(_cell(read_run(course_file(entry.filename)), cycle, source=source))
    for powertrain in ("petrol", "bev", "hybrid"):
        entry = find(powertrain=powertrain, cycle="nedc")
        out.append(_cell(read_run(course_file(entry.filename)), "nedc", source=source))
    derived = {(s.powertrain, s.cycle, s.mode): s for s in SPECS}
    for powertrain in ("petrol", "bev", "hybrid"):
        out.append(_cell(read_derived(derived[(powertrain, "wltc", None)]), "wltc", source=source))
    for cycle in ("nedc", "wltc"):
        cd = _cell(read_derived(derived[("phev", cycle, "cd")]), cycle, "cd", source)
        cs = _cell(read_derived(derived[("phev", cycle, "cs")]), cycle, "cs", source)
        capacity = read_derived(derived[("phev", cycle, "cd")]).params[
            ("batt energy content", "wh")
        ]
        usable = capacity * (0.98 - PHEV_ENGINE_SOC)
        out += [_r101(cd, cs, usable), cd, cs]
    return out


def table(rows: list[Cell], field: str, digits: int = 1) -> pd.DataFrame:
    headline = [c for c in rows if not c.variant]
    frame = pd.DataFrame(
        {
            CYCLE_LABELS[cycle]: {
                POWERTRAIN_NAMES[c.powertrain]: getattr(c, field)
                for c in headline
                if c.cycle == cycle
            }
            for cycle in CYCLE_ORDER
        }
    )
    return frame.reindex(list(POWERTRAIN_NAMES.values())).map(
        lambda v: "—" if v is None or pd.isna(v) else f"{v:.{digits}f}"
    )


# --- what each inconsistency in the sheets is worth --------------------------------------

#: Petrol's efficiency curve, for putting into the hybrid sheet.
_MODERN = {"C26": 0.35, "C27": -0.3867, "C28": 0.6285, "C29": 0.7516}
#: The hybrid Francorchamps eco car's added mass: 50 kg machine + 2 × 1500 Wh / 80 Wh/kg.
_HYBRID_EXTRA_KG = 50 + 2 * 1500 / 80


def variants() -> pd.DataFrame:
    """Each supplied workbook against itself with one thing changed."""
    petrol_eco = "07 SPA Franco PETROL car ECO Driving.xlsx"
    hybrid_eco = "10 SPA Franco HYBRID engine ECO Driving.xlsx"
    petrol_nedc = "33 NEDC PETROL Car.xlsx"
    franco_eff_mass = {
        f"C{39 + i}": f"=C14+$C$13*(1.04+0.0025*(C{6 + i})^2)" for i in range(5)
    }
    cases = {
        "petrol_eco": Variant(petrol_eco),
        "petrol_eco_1280kg": Variant(petrol_eco, {"C13": 1280}),
        "petrol_eco_74kW": Variant(petrol_eco, {"C31": 74000}),
        "petrol_eco_750density": Variant(petrol_eco, {"C37": 750}),
        # The hybrid sheet adds its machine and battery outside the rotating-mass factor, as
        # it does the driver, so the same mass goes on the driver's line here.
        "petrol_eco_hybrid_mass": Variant(petrol_eco, {"C14": 80 + _HYBRID_EXTRA_KG}),
        "hybrid_eco": Variant(hybrid_eco),
        "hybrid_eco_modern_curve": Variant(hybrid_eco, _MODERN),
        "petrol_nedc": Variant(petrol_nedc),
        "petrol_nedc_franco_eff_mass": Variant(petrol_nedc, franco_eff_mass),
    }
    runs = run_variants(cases)

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        spec = DerivedSpec(
            "shift.xlsx", petrol_nedc, "petrol", "nedc", "regulatory", "shift",
            shift_kph=SHIFT_KPH,
        )
        build((spec,), Path(tmp))
        runs["petrol_nedc_franco_shifts"] = read_run(Path(tmp) / "shift.xlsx")

    def row(what, base, case, note=""):
        b, c = runs[base].consumption_l_per_100km, runs[case].consumption_l_per_100km
        bc, cc = runs[base].co2_g_per_km, runs[case].co2_g_per_km
        return {
            "change": what,
            "run": cases[base].template if base in cases else petrol_nedc,
            "l/100 km": f"{b:.3f} → {c:.3f}",
            "g CO2/km": f"{bc:.1f} → {cc:.1f}",
            "effect": f"{100 * (c / b - 1):+.1f} %",
            "note": note,
        }

    return pd.DataFrame(
        [
            row("Vehicle mass 1300 → 1280 kg (sheet value)", "petrol_eco", "petrol_eco_1280kg"),
            row("Engine max power 85 → 74 kW (sheet value)", "petrol_eco", "petrol_eco_74kW",
                "Only rescales the efficiency curve's load axis"),
            row("Fuel density 720 → 750 kg/m³ (sheet value)", "petrol_eco",
                "petrol_eco_750density", "CO2 is per litre, so it moves too"),
            row("Hybrid's efficiency curve → petrol's", "hybrid_eco", "hybrid_eco_modern_curve",
                "Atkinson curve costs the hybrid this much"),
            row(f"Petrol + {_HYBRID_EXTRA_KG:.1f} kg (hybrid's extra mass)", "petrol_eco",
                "petrol_eco_hybrid_mass", "Extra mass costs the hybrid this much"),
            row("NEDC petrol effective mass → Francorchamps formula", "petrol_nedc",
                "petrol_nedc_franco_eff_mass"),
            row("NEDC petrol shift speeds → 35/57/82/115 km/h", "petrol_nedc",
                "petrol_nedc_franco_shifts"),
        ]
    )


def markdown() -> str:
    rows = cells()
    parts = [
        "### Fuel (l/100 km)\n\n" + table(rows, "fuel_l_100km", 2).to_markdown(),
        "### Electricity from the battery (kWh/100 km)\n\n"
        + table(rows, "battery_kwh_100km", 1).to_markdown(),
        "### CO2 as the sheets report it (g/km)\n\n" + table(rows, "co2_reported").to_markdown(),
        "### CO2 with grid electricity at the EU average, 250 g/kWh (g/km)\n\n"
        + table(rows, "co2_eu_grid").to_markdown(),
        "### Plug-in hybrid detail\n\n"
        + pd.DataFrame(
            [
                {
                    "cycle": CYCLE_LABELS[c.cycle],
                    "run": c.variant or "R101 weighted",
                    "l/100 km": f"{c.fuel_l_100km:.2f}",
                    "kWh/100 km": f"{c.battery_kwh_100km:.1f}",
                    "g CO2/km (fuel)": f"{c.co2_reported:.1f}",
                    "g CO2/km (+ EU grid)": f"{c.co2_eu_grid:.1f}",
                    "source": c.source,
                }
                for c in rows
                if c.powertrain == "phev" and c.cycle in ("nedc", "wltc")
            ]
        ).to_markdown(index=False),
        "### What each inconsistency is worth\n\n" + variants().to_markdown(index=False),
    ]
    return "\n\n".join(parts)


if __name__ == "__main__":
    print(markdown())
