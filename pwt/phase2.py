"""The Phase 2 checkpoint: the 4 × 4 table four ways, from `pwt.model`.

1. **exact** — each workbook reproduced (equals `docs/phase-1-results.md`).
2. **harmonised** — the same vehicles, one convention and cited constants.
3. **stage B** — harmonised; hybrid engine efficiency read at the engine's share of the
   demand rather than all of it; the full hybrid charge-sustaining.
4. **assignment** — stage B with the assignment sheet's vehicles instead of the workbooks'.

Engine capability does not change these figures: clipping power the car cannot deliver
would only make an infeasible trace look frugal. It is reported beside them instead, as the
steps on which each engine falls short of its 74 kW full-load curve.

    python -m pwt.phase2      # print the tables as Markdown
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from pwt.catalog import POWERTRAIN_NAMES, course_file, find
from pwt.checkpoint import CYCLE_LABELS, CYCLE_ORDER, Cell, _r101, cells, make_cell, table
from pwt.derived import PHEV_ENGINE_SOC, SPECS, read_derived
from pwt.model import Cycle, Vehicle, simulate
from pwt.model import fleet
from pwt.model.conventions import harmonised
from pwt.model.strategy import NelisStrategy, SocBandStrategy
from pwt.workbook import read_run

SCENARIOS = ("exact", "harmonised", "stage B", "assignment")
GRID = 250.0
RATED_W = 74_000.0
BAND_SOC0 = 0.6
#: Shortfalls below this are discretisation, not a car that cannot follow the trace.
SHORTFALL_NOISE_W = 100.0


def _source(powertrain: str, cycle: str):
    """The workbook whose trace (and, for the workbook vehicles, parameters) a cell uses."""
    if cycle == "wltc":
        mode = "cd" if powertrain == "phev" else None
        spec = next(s for s in SPECS if (s.powertrain, s.cycle, s.mode) == (powertrain, cycle, mode))
        return read_derived(spec)
    if cycle == "nedc" and powertrain == "phev":
        spec = next(s for s in SPECS if (s.powertrain, s.cycle, s.mode) == ("phev", "nedc", "cd"))
        return read_derived(spec)
    return read_run(course_file(find(powertrain=powertrain, cycle=cycle).filename))


def _vehicle(powertrain: str, run, scenario: str) -> Vehicle:
    if scenario == "assignment":
        soc0 = None
        if powertrain in ("hybrid", "phev"):
            soc0 = Vehicle.from_run(run).soc0 if run is not None else (
                1.0 if powertrain == "hybrid" else 0.98
            )
        return {
            "petrol": fleet.petrol,
            "bev": fleet.electric,
            "hybrid": lambda: fleet.hybrid(soc0),
            "phev": lambda: fleet.plugin(soc0),
        }[powertrain]()
    return Vehicle.from_run(run)


def _simulate(powertrain, cycle, vehicle, cyc, scenario, soc0=None, capability=False):
    conv = replace(harmonised(cyc.kind, powertrain, GRID), capability=capability)
    strategy = None
    if scenario in ("stage B", "assignment"):
        if powertrain == "hybrid":
            strategy = SocBandStrategy()
            vehicle = replace(vehicle, soc0=BAND_SOC0)
        elif powertrain == "phev":
            strategy = NelisStrategy(efficiency_at="engine")
    if soc0 is not None:
        vehicle = replace(vehicle, soc0=soc0)
    return simulate(vehicle, cyc, conv, strategy)


def _shortfall(powertrain, cycle, vehicle, cyc, scenario, soc0=None) -> tuple[int, float]:
    """Steps on which the engine falls short of its full-load curve, and the worst (kW)."""
    if vehicle.family == "bev":
        return 0, 0.0
    vehicle = replace(vehicle, p_rated_w=vehicle.p_rated_w or RATED_W)
    short = _simulate(powertrain, cycle, vehicle, cyc, scenario, soc0, capability=True).steps[
        "shortfall_w"
    ]
    short = short[short > SHORTFALL_NOISE_W]
    return int(len(short)), float(short.max()) / 1000 if len(short) else 0.0


def _cell(powertrain, cycle, variant, result) -> Cell:
    h = result.headline
    return make_cell(powertrain, cycle, variant, h["fuel_l_100km"], h["battery_kwh_100km"],
                     h["co2_g_km"], result.cycle.name, result.conventions.charger_efficiency)


def scenario_cells(scenario: str) -> tuple[list[Cell], dict]:
    """Cells for one scenario, and each engine cell's shortfall against its full-load curve."""
    if scenario == "exact":
        return cells("model"), {}
    out: list[Cell] = []
    shortfall: dict[tuple[str, str], tuple[int, float]] = {}
    for cycle in CYCLE_ORDER:
        for powertrain in POWERTRAIN_NAMES:
            run = _source(powertrain, cycle)
            kind = "distance" if cycle.startswith("franco") else "time"
            cyc = Cycle.from_run(run, kind, name=run.source_file)
            vehicle = _vehicle(powertrain, run, scenario)
            if powertrain == "phev" and cycle in ("nedc", "wltc"):
                cd = _cell(powertrain, cycle, "cd",
                           _simulate(powertrain, cycle, vehicle, cyc, scenario, soc0=0.98))
                cs = _cell(powertrain, cycle, "cs",
                           _simulate(powertrain, cycle, vehicle, cyc, scenario,
                                     soc0=PHEV_ENGINE_SOC))
                usable = vehicle.battery_wh * (0.98 - PHEV_ENGINE_SOC)
                out += [_r101(cd, cs, usable), cd, cs]
                shortfall[(powertrain, cycle)] = _shortfall(
                    powertrain, cycle, vehicle, cyc, scenario, soc0=PHEV_ENGINE_SOC
                )
                continue
            result = _simulate(powertrain, cycle, vehicle, cyc, scenario)
            out.append(_cell(powertrain, cycle, "", result))
            shortfall[(powertrain, cycle)] = _shortfall(powertrain, cycle, vehicle, cyc, scenario)
    return out, shortfall


def shortfall_table(shortfall: dict) -> pd.DataFrame:
    """Steps short of the full-load curve / steps in the cycle, and the worst shortfall."""
    steps = {"nedc": 104, "franco_eco": 31, "franco_sport": 31, "wltc": 1800}
    frame = pd.DataFrame(
        {
            CYCLE_LABELS[cycle]: {
                POWERTRAIN_NAMES[p]: (
                    "—" if (p, cycle) not in shortfall or shortfall[(p, cycle)][0] == 0
                    else f"{shortfall[(p, cycle)][0]} of {steps[cycle]}, "
                         f"up to {shortfall[(p, cycle)][1]:.0f} kW"
                )
                for p in POWERTRAIN_NAMES
                if p != "bev"
            }
            for cycle in CYCLE_ORDER
        }
    )
    return frame


#: Cycles `result_for` accepts beyond CYCLE_ORDER: the laps `pwt.model.profile` generates.
GENERATED = {"franco_eco_generated": "eco", "franco_sport_generated": "sport"}


def result_for(powertrain: str, cycle: str, scenario: str):
    """One powertrain on one cycle under one scenario, as a full `Result` (steps included).

    The plug-in hybrid on NEDC and WLTC is its charge-depleting run. On a generated lap the
    exact scenario does not exist (no workbook), so it runs as "assignment".
    """
    from pwt.model import from_workbook
    from pwt.model.profile import generate

    if cycle in GENERATED:
        vehicle = _vehicle(powertrain, None, "assignment")
        cyc = generate(GENERATED[cycle], fleet.petrol())
        return _simulate(powertrain, cycle, vehicle, cyc, "assignment")
    run = _source(powertrain, cycle)
    if scenario == "exact":
        return from_workbook(run)
    kind = "distance" if cycle.startswith("franco") else "time"
    cyc = Cycle.from_run(run, kind, name=run.source_file)
    return _simulate(powertrain, cycle, _vehicle(powertrain, run, scenario), cyc, scenario)


def hybrid_breakdown() -> pd.DataFrame:
    """The full hybrid's stage B change, one step at a time (harmonised constants)."""
    rows = {
        "sheets' rule, efficiency at the whole demand": (NelisStrategy("demand"), None),
        "sheets' rule, efficiency at the engine's share": (NelisStrategy("engine"), None),
        "same, starting at 60 %": (NelisStrategy("engine"), BAND_SOC0),
        "charge-sustaining band 50-70 %, from 60 %": (SocBandStrategy(), BAND_SOC0),
    }
    out = {}
    for label, (strategy, soc0) in rows.items():
        out[label] = {}
        for cycle in CYCLE_ORDER:
            run = _source("hybrid", cycle)
            kind = "distance" if cycle.startswith("franco") else "time"
            vehicle = Vehicle.from_run(run)
            if soc0 is not None:
                vehicle = replace(vehicle, soc0=soc0)
            result = simulate(vehicle, Cycle.from_run(run, kind),
                              harmonised(kind, "hybrid", GRID), strategy)
            out[label][CYCLE_LABELS[cycle]] = f"{result.headline['fuel_l_100km']:.2f}"
    return pd.DataFrame(out).T


def generated_laps() -> pd.DataFrame:
    """Every powertrain on the Francorchamps laps the assignment's rules generate.

    The profile is generated for the assignment sheet's petrol car (the sheet: "same for all
    cars") and driven by the four assignment vehicles, stage B conventions.
    """
    from pwt.model.profile import generate, lap_time_s, track

    rows = {}
    for mode in ("eco", "sport"):
        cyc = generate(mode, fleet.petrol())
        label = f"{mode} — generated, {lap_time_s(cyc):.0f} s"
        rows[label] = {}
        for powertrain, name in POWERTRAIN_NAMES.items():
            vehicle = {"petrol": fleet.petrol, "bev": fleet.electric,
                       "hybrid": fleet.hybrid, "phev": fleet.plugin}[powertrain]()
            result = _simulate(powertrain, mode, vehicle, cyc, "assignment")
            cell = _cell(powertrain, mode, "", result)
            short, worst = _shortfall(powertrain, mode, vehicle, cyc, "assignment")
            text = f"{cell.co2_eu_grid:.1f}"
            if short:
                text += f" (short on {short} step{'s' if short > 1 else ''}, ≤ {worst:.0f} kW)"
            rows[label][name] = text
        supplied = scenario_cells("assignment")[0]
        template = track(mode).template_time_s
        rows[f"{mode} — supplied lap, {template:.0f} s"] = {
            POWERTRAIN_NAMES[c.powertrain]: f"{c.co2_eu_grid:.1f}"
            for c in supplied if c.cycle == f"franco_{mode}" and not c.variant
        }
    return pd.DataFrame(rows).T


def markdown() -> str:
    parts = []
    summary = {}
    for scenario in SCENARIOS:
        rows, shortfall = scenario_cells(scenario)
        summary[scenario] = rows
        parts.append(f"## {scenario}")
        parts.append("### Fuel (l/100 km)\n\n" + table(rows, "fuel_l_100km", 2).to_markdown())
        parts.append(
            "### CO2 with electricity at 250 g/kWh (g/km)\n\n"
            + table(rows, "co2_eu_grid").to_markdown()
        )
        if shortfall:
            parts.append(
                "### Steps the engine cannot deliver (74 kW full-load curve)\n\n"
                + shortfall_table(shortfall).to_markdown()
            )
    parts.insert(0, "## All four, CO2 with electricity at 250 g/kWh (g/km)\n\n"
                 + side_by_side(summary).to_markdown()
                 + "\n\n## The full hybrid's change, step by step (l/100 km)\n\n"
                 + hybrid_breakdown().to_markdown()
                 + "\n\n## Francorchamps, generated by the assignment's rules "
                   "(g CO2/km, electricity at 250 g/kWh, assignment vehicles)\n\n"
                 + generated_laps().to_markdown())
    return "\n\n".join(parts)


def side_by_side(summary: dict[str, list[Cell]]) -> pd.DataFrame:
    rows = []
    for powertrain, name in POWERTRAIN_NAMES.items():
        for cycle in CYCLE_ORDER:
            row = {"powertrain": name, "cycle": CYCLE_LABELS[cycle]}
            for scenario, cells_ in summary.items():
                cell = next(c for c in cells_ if (c.powertrain, c.cycle, c.variant)
                            == (powertrain, cycle, ""))
                row[scenario] = f"{cell.co2_eu_grid:.1f}"
            rows.append(row)
    return pd.DataFrame(rows).set_index(["powertrain", "cycle"])


if __name__ == "__main__":
    print(markdown())
