"""Study B: one-factor-at-a-time sensitivity on fixed baseline cycles.

Run ``python -m pwt.sensitivity`` to export the raw and ranked tables.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from pwt.model import Vehicle, fleet
from pwt.sweep import CYCLES, START_SOC, cycles, sweep

BASE = {
    "petrol": fleet.petrol(),
    "bev": fleet.electric(),
    "hybrid": fleet.hybrid(START_SOC["hybrid"]),
    "phev": fleet.plugin(START_SOC["phev"]),
}
FACTORS = {
    "mass": lambda v, k: replace(v, m_vehicle=v.m_vehicle * k),
    "drag": lambda v, k: replace(v, cx=v.cx * k),
    "rolling": lambda v, k: replace(v, f_roll=v.f_roll * k),
    "gears": lambda v, k: replace(v, ratios=tuple(r * k for r in v.ratios)),
    "engine": lambda v, k: replace(v, eta_max=v.eta_max * k),
}
SCALES = (0.9, 1.1)
# The approved plan's checkpoint, rounded to one decimal, in CYCLES order.
EXPECTED_BASELINE = {
    "petrol": (134.1, 145.1, 217.5, 385.2),
    "bev": (38.0, 45.8, 56.5, 132.2),
    "hybrid": (123.7, 128.8, 218.8, 395.2),
    "phev": (67.9, 73.6, 113.0, 293.0),
}
HERE = Path(__file__).resolve().parent.parent / "docs"


def variants() -> dict[tuple[str, str, float], Vehicle]:
    """42 immutable vehicle variants; only one parameter changes in each."""
    out = {}
    for powertrain, vehicle in BASE.items():
        out[(powertrain, "baseline", 1.0)] = vehicle
        for name, change in FACTORS.items():
            if name == "engine" and powertrain == "bev":
                continue
            for scale in SCALES:
                out[(powertrain, name, scale)] = change(vehicle, scale)
    return out


def check_baseline(frame: pd.DataFrame) -> None:
    """Stop rather than publish results if the approved baseline has moved."""
    actual = frame[frame["factor"] == "baseline"].set_index(["powertrain", "cycle"])
    expected_keys = {(p, c) for p in BASE for c in CYCLES}
    if not actual.index.is_unique or set(actual.index) != expected_keys:
        raise ValueError("Expected exactly one baseline for each powertrain and cycle")
    for powertrain, values in EXPECTED_BASELINE.items():
        for cycle, expected in zip(CYCLES, values):
            value = actual.loc[(powertrain, cycle), "co2_eu"]
            if pd.isna(value) or round(float(value), 1) != expected:
                raise ValueError(f"Baseline changed: {powertrain}/{cycle}: {value}, expected {expected}")


def sensitivity() -> pd.DataFrame:
    """168 sweep rows using the unchanged storage-loss scenario."""
    frame = sweep(variants(), cycles()).rename(columns={"v1": "factor", "v2": "scale"})
    check_baseline(frame)
    return frame


def swings(frame: pd.DataFrame, co2: str = "co2_eu") -> pd.DataFrame:
    """Endpoint CO2 and unsigned span, ranked separately for each car and cycle.

    Preserve endpoint direction: improving efficiency can lower CO2 at scale 1.1.
    Signed deltas from baseline make the tornado's two sides explicit.
    """
    check_baseline(frame)
    keys = ["powertrain", "cycle"]
    endpoints = frame[frame["factor"] != "baseline"]
    expected = {(p, c, f, s) for p, f, s in variants() if f != "baseline" for c in CYCLES}
    actual = pd.MultiIndex.from_frame(endpoints[keys + ["factor", "scale"]])
    if not actual.is_unique or set(actual) != expected or endpoints["co2_eu"].isna().any():
        raise ValueError("Sensitivity endpoints are missing, duplicated or contain CO2 gaps")
    if co2 not in ("co2_eu", "co2_fr"):
        raise ValueError("Choose co2_eu or co2_fr")
    table = endpoints.pivot(index=keys + ["factor"], columns="scale", values=co2)
    table = table.rename(columns={0.9: "co2_low", 1.1: "co2_high"}).rename_axis(columns=None)
    baseline = frame[frame["factor"] == "baseline"].set_index(keys)[co2]
    table = table.join(baseline.rename("baseline")).reset_index()
    table["delta_low"] = table["co2_low"] - table["baseline"]
    table["delta_high"] = table["co2_high"] - table["baseline"]
    table["swing"] = (table["co2_high"] - table["co2_low"]).abs()
    table["swing_percent"] = 100 * table["swing"] / table["baseline"]
    # Signed, finite-difference elasticity: relative CO2 change / relative parameter change.
    # Still depends on the sampled interval when the response is nonlinear.
    table["elasticity"] = (table["co2_high"] - table["co2_low"]) / (0.2 * table["baseline"])
    table["elasticity_low"] = table["delta_low"] / (-0.1 * table["baseline"])
    table["elasticity_high"] = table["delta_high"] / (0.1 * table["baseline"])
    for scale, suffix in ((0.9, "low"), (1.1, "high")):
        flags = endpoints[endpoints.scale == scale].set_index(keys + ["factor"])
        table = table.join(flags[["short_steps", "short_kw"]].add_suffix(f"_{suffix}"),
                           on=keys + ["factor"])
    baseline_flags = frame[frame.factor == "baseline"].set_index(keys).short_steps
    table = table.join(baseline_flags.rename("baseline_short_steps"), on=keys)
    table["engine_check_pass"] = ((table.short_steps_low == 0)
                                  & (table.short_steps_high == 0)
                                  & (table.baseline_short_steps == 0))
    table = table.sort_values(keys + ["swing", "factor"], ascending=[True, True, False, True])
    table["rank"] = table.groupby(keys).cumcount() + 1
    return table.reset_index(drop=True)


def export(frame: pd.DataFrame, directory: Path = HERE) -> pd.DataFrame:
    ranked = swings(frame)
    frame.to_csv(directory / "study-b-results.csv", index=False)
    ranked.to_csv(directory / "study-b-swings.csv", index=False)
    return ranked


if __name__ == "__main__":
    results = sensitivity()
    print(export(results).to_markdown(index=False, floatfmt=".3f"))
