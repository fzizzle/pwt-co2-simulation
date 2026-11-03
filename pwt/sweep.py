"""Run a grid of vehicle variants over the cycles, and the hybrid sizing study built on it.

`sweep` takes any `Vehicle` variants, so a one-at-a-time sensitivity study is the same call
with a different grid. Everything runs under the "storage losses" scenario: without a loss,
storing energy is free and a bigger battery only ever looks better.

    python -m pwt.sweep       # print the tables as Markdown, write the figure
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from pwt.checkpoint import Cell
from pwt.model import Cycle, Vehicle, fleet, simulate
from pwt.model.constants import CHARGER_EFFICIENCY, GRID_G_PER_KWH
from pwt.model.conventions import harmonised
from pwt.model.profile import generate
from pwt.model.strategy import NelisStrategy, SocBandStrategy
from pwt.phase2 import GRID, _source, powertrain_cells

SCENARIO = "storage losses"
#: The cycles a car can actually drive: the regulatory two and the generated laps.
CYCLES = {
    "nedc": "NEDC",
    "wltc": "WLTC Class 3",
    "franco_eco_generated": "Francorchamps eco, generated",
    "franco_sport_generated": "Francorchamps sport, generated",
}
BATTERY_KWH = (1, 1.5, 2, 3, 4, 6, 8, 10, 12, 15, 20)
MOTOR_KW = (20, 30, 40, 50, 60, 70, 80)
#: Strategy and accounting: the full hybrid holds its band and buys back any drain with fuel;
#: the plug-in hybrid starts full and is recharged from the grid.
POWERTRAINS = {"hybrid": "Full hybrid", "phev": "Plug-in hybrid"}
START_SOC = {"hybrid": 0.6, "phev": 0.98}
#: Peak battery power over energy. The model has no battery power limit, so a 1 kWh pack would
#: happily run an 80 kW motor. An assumption, just above the assignment hybrid's 16.7 C.
MAX_C_RATE = 20.0
HERE = Path(__file__).resolve().parent.parent / "docs"


def cycles() -> dict[str, Cycle]:
    """Every sweep cycle. The generated laps are the petrol car's, "same for all cars"."""
    out = {}
    for cycle in ("nedc", "wltc"):
        run = _source("hybrid", cycle)
        out[cycle] = Cycle.from_run(run, "time", name=run.source_file)
    petrol = fleet.petrol()
    out["franco_eco_generated"] = generate("eco", petrol)
    out["franco_sport_generated"] = generate("sport", petrol)
    return out


def france_co2(cell: Cell) -> float:
    """g CO2/km with the French grid: the fuel's CO2 as reported, plus the electricity's."""
    if cell.powertrain == "hybrid" or cell.battery_kwh_100km is None:
        return cell.co2_eu_grid
    grid = GRID_G_PER_KWH["FR"] / CHARGER_EFFICIENCY
    if cell.powertrain == "bev":
        # Its reported CO2 already represents grid electricity, not fuel.
        return cell.battery_kwh_100km * grid / 100
    return cell.co2_reported + cell.battery_kwh_100km * grid / 100


def sweep(variants: dict, cycle_map: dict[str, Cycle] | None = None,
          scenario: str = SCENARIO) -> pd.DataFrame:
    """One row per variant and cycle.

    `variants` maps a tuple of labels, (powertrain, *anything), to a `Vehicle`; the labels
    come back as columns `powertrain`, `v1`, `v2`… so the caller names its own axes.
    """
    cycle_map = cycle_map or cycles()
    rows = []
    for key, vehicle in variants.items():
        powertrain, *labels = key
        for cycle, cyc in cycle_map.items():
            cells, (short_steps, short_kw) = powertrain_cells(
                powertrain, cycle, vehicle, cyc, scenario
            )
            cell = cells[0]
            rows.append({
                "powertrain": powertrain,
                **{f"v{i + 1}": label for i, label in enumerate(labels)},
                "cycle": cycle,
                "mass_kg": vehicle.m_total,
                "fuel_l_100km": cell.fuel_l_100km,
                "battery_kwh_100km": cell.battery_kwh_100km,
                "co2_eu": cell.co2_eu_grid,
                "co2_fr": france_co2(cell),
                "short_steps": short_steps,
                "short_kw": short_kw,
            })
    return pd.DataFrame(rows)


def sizing_grid() -> dict[tuple, Vehicle]:
    return {
        (powertrain, battery, motor): fleet.sized_hybrid(battery, motor, START_SOC[powertrain])
        for powertrain in POWERTRAINS
        for battery in BATTERY_KWH
        for motor in MOTOR_KW
    }


def sizing() -> pd.DataFrame:
    frame = sweep(sizing_grid()).rename(columns={"v1": "battery_kwh", "v2": "motor_kw"})
    frame["buildable"] = frame["motor_kw"] / frame["battery_kwh"] <= MAX_C_RATE
    return frame


def storage_sensitivity(cycle_map: dict[str, Cycle] | None = None) -> pd.DataFrame:
    """The assignment's full hybrid, band against the sheets' rule, by storage efficiency."""
    cycle_map = cycle_map or cycles()
    rows = {}
    for eta in (1.0, 0.95, 0.9, 0.85, 0.8):
        for name, strategy in (("band", SocBandStrategy()), ("sheets' rule",
                                                             NelisStrategy("engine"))):
            rows[(eta, name)] = {
                CYCLES[cycle]: simulate(
                    fleet.hybrid(START_SOC["hybrid"]), cyc,
                    replace(harmonised(cyc.kind, "hybrid", GRID), storage_efficiency=eta),
                    strategy,
                ).headline["co2_g_km"]
                for cycle, cyc in cycle_map.items()
            }
    table = pd.DataFrame(rows).T.round(1)
    table.index.names = ["one-way efficiency", "strategy"]
    return table


def petrol_reference(cycle_map: dict[str, Cycle] | None = None) -> dict[str, float]:
    cycle_map = cycle_map or cycles()
    return {
        CYCLES[cycle]: round(simulate(fleet.petrol(), cyc, harmonised(cyc.kind, "petrol", GRID)
                                      ).headline["co2_g_km"], 1)
        for cycle, cyc in cycle_map.items()
    }


def best(frame: pd.DataFrame, co2: str = "co2_eu") -> pd.DataFrame:
    """The lowest-CO2 buildable size per powertrain and cycle."""
    rows = []
    frame = frame[frame["buildable"]]
    for (powertrain, cycle), part in frame.groupby(["powertrain", "cycle"], sort=False):
        top = part.loc[part[co2].idxmin()]
        rows.append({
            "powertrain": POWERTRAINS[powertrain],
            "cycle": CYCLES[cycle],
            "best battery (kWh)": top["battery_kwh"],
            "best motor (kW)": top["motor_kw"],
            "mass (kg)": round(top["mass_kg"]),
            "g CO2/km": round(top[co2], 1),
            "worst in grid": round(part[co2].max(), 1),
            "steps short": top["short_steps"],
        })
    return pd.DataFrame(rows)


def by_battery(frame: pd.DataFrame, powertrain: str, co2: str = "co2_eu") -> pd.DataFrame:
    """Best buildable motor's CO2 for each battery size, one column per cycle."""
    part = frame[(frame["powertrain"] == powertrain) & frame["buildable"]]
    table = part.groupby(["battery_kwh", "cycle"], sort=False)[co2].min().unstack("cycle")
    return table[list(CYCLES)].rename(columns=CYCLES).round(1)


def plot(frame: pd.DataFrame, path: Path) -> None:
    """g CO2/km against battery size, one panel per cycle, one line per powertrain and grid."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colours = {"hybrid": "#1baf7a", "phev": "#eda100"}  # as `dashboard.theme`
    frame = frame[frame["buildable"]]
    petrol = petrol_reference()
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6), sharex=True)
    for ax, (cycle, label) in zip(axes, CYCLES.items()):
        part = frame[frame["cycle"] == cycle]
        for powertrain, name in POWERTRAINS.items():
            own = part[part["powertrain"] == powertrain]
            eu = own.groupby("battery_kwh")["co2_eu"].min()
            ax.plot(eu.index, eu.values, color=colours[powertrain], lw=2, label=f"{name}, EU grid")
            if powertrain == "phev":
                fr = own.groupby("battery_kwh")["co2_fr"].min()
                ax.plot(fr.index, fr.values, color=colours[powertrain], lw=2, ls="--",
                        label=f"{name}, French grid")
        ax.axhline(petrol[label], color="#6b6b66", lw=1.5, ls=":", label="Petrol")
        ax.set_title(label, fontsize=10, loc="left")
        ax.set_xlabel("Battery (kWh)")
        ax.set_ylim(bottom=0)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#dddddd", lw=0.6)
    axes[0].set_ylabel("g CO2/km, best motor at each size")
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def markdown(frame: pd.DataFrame) -> str:
    return "\n\n".join([
        "## The assignment's full hybrid by storage efficiency (g CO2/km)\n\n"
        + storage_sensitivity().to_markdown(),
        "Petrol on the same cycles: "
        + ", ".join(f"{k} {v}" for k, v in petrol_reference().items()) + ".",
        "## Best size per cycle, EU grid (250 g/kWh)\n\n"
        + best(frame).to_markdown(index=False),
        "## Best size per cycle, French grid (73 g/kWh)\n\n"
        + best(frame, "co2_fr").to_markdown(index=False),
        "## Full hybrid: g CO2/km by battery, best motor at each size\n\n"
        + by_battery(frame, "hybrid").to_markdown(),
        "## Plug-in hybrid: g CO2/km by battery, EU grid, best motor at each size\n\n"
        + by_battery(frame, "phev").to_markdown(),
        "## Plug-in hybrid: the same, French grid\n\n"
        + by_battery(frame, "phev", "co2_fr").to_markdown(),
    ])


if __name__ == "__main__":
    frame = sizing()
    plot(frame, HERE / "phase-3-sizing.png")
    print(markdown(frame))
