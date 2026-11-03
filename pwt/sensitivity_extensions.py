"""Exploratory Study B checks; the approved fixed-trace study stays unchanged.

All assumptions, including the limits of regenerated laps, are documented in the report.
"""

from __future__ import annotations

from dataclasses import replace
from itertools import product

import openpyxl
import pandas as pd

from pwt.catalog import COURSE_FILES
from pwt.model.profile import generate, lap_time_s
from pwt.sensitivity import BASE, FACTORS, HERE, variants
from pwt.sweep import cycles, sweep

INTERMEDIATE_SCALES = (0.9, 0.95, 1.05, 1.1)
GEAR_SCALES = (0.9, 0.925, 0.95, 0.975, 1.025, 1.05, 1.075, 1.1)
# Technology-inspired scenarios, not vehicle-specific achievable or cost-optimal ranges.
# Mass: DOE lightweighting; drag/rolling: EPA 2016 TSD; engine: assignment 20–40%.
# Gear range is explicitly an unsourced exploratory assumption, not a technology claim.
IMPROVEMENT_SCALES = {
    "mass": (0.95, 0.9), "drag": (0.9, 0.8), "rolling": (0.9, 0.8),
    "engine": (1.05, 1.1), "gears": (0.95, 1.05),
}


def total_mass(vehicle, scale):
    """Reach scale * total mass by changing body mass, keeping driver/powertrain fixed."""
    return replace(vehicle, m_vehicle=vehicle.m_vehicle + (scale - 1) * vehicle.m_total)


def intermediate_variants() -> dict:
    out = {}
    for powertrain, vehicle in BASE.items():
        out[(powertrain, "baseline", 1.0)] = vehicle
        for factor, change in FACTORS.items():
            if factor == "engine" and powertrain == "bev":
                continue
            for scale in GEAR_SCALES if factor == "gears" else INTERMEDIATE_SCALES:
                out[(powertrain, factor, scale)] = change(vehicle, scale)
    return out


def workbook_curves() -> pd.DataFrame:
    """Read alternatives by parameter labels; verify all three supplied menus agree."""
    menus = []
    for prefix in ("10", "15", "35"):
        path = next(COURSE_FILES.glob(f"{prefix} *.xlsx"))
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            rows = list(book.active.iter_rows(min_row=1, max_row=35, max_col=4, values_only=True))
            params = {str(row[0]).strip().lower(): row[1:4] for row in rows}
            curves = []
            for col, label in enumerate(("downsized", "atkinson", "old")):
                curves.append({"curve": label, "eta_max": params["engine max efficiency"][col],
                               **{a: params[a][col] for a in ("a1", "a2", "a3")}})
            menus.append(pd.DataFrame(curves))
        finally:
            book.close()
    if not all(menus[0].equals(menu) for menu in menus[1:]):
        raise ValueError("The course workbooks disagree on their engine-curve menus")
    return menus[0]


def assumption_variants(curves: pd.DataFrame) -> dict:
    out = {}
    for powertrain, vehicle in BASE.items():
        out[(powertrain, "baseline", "baseline")] = vehicle
        for scale in (0.9, 1.1):
            out[(powertrain, "body_mass", str(scale))] = FACTORS["mass"](vehicle, scale)
            out[(powertrain, "total_mass", str(scale))] = total_mass(vehicle, scale)
        if powertrain == "bev":
            continue
        for row in curves.itertuples():
            shape = {a: getattr(row, a) for a in ("a1", "a2", "a3")}
            out[(powertrain, "shape_only", row.curve)] = replace(vehicle, **shape)
            out[(powertrain, "workbook_curve", row.curve)] = replace(vehicle, eta_max=row.eta_max, **shape)
    return out


def improvement_variants() -> dict:
    out = {}
    for powertrain, vehicle in BASE.items():
        out[(powertrain, "baseline", 1.0)] = vehicle
        for factor, scales in IMPROVEMENT_SCALES.items():
            if powertrain == "bev" and factor == "engine":
                continue
            for scale in scales:
                out[(powertrain, factor, scale)] = FACTORS[factor](vehicle, scale)
    return out


def interaction_variants() -> dict:
    out = {}
    for powertrain, vehicle in BASE.items():
        pairs = ("drag", "gears", "engine") if powertrain in ("hybrid", "phev") else ("drag", "gears")
        for second in pairs:
            for mass, other in product((0.9, 1.0, 1.1), repeat=2):
                out[(powertrain, second, mass, other)] = FACTORS[second](FACTORS["mass"](vehicle, mass), other)
    return out


def interactions(frame: pd.DataFrame) -> pd.DataFrame:
    """Joint change minus the sum of individual changes, in g/km (zero is additive)."""
    out = frame.copy()
    keys = ["powertrain", "cycle", "second_factor"]
    lookup = frame.set_index(keys + ["mass_scale", "other_scale"])
    residuals = []
    for row in out.itertuples():
        group = (row.powertrain, row.cycle, row.second_factor)
        base = lookup.loc[(*group, 1.0, 1.0), "co2_eu"]
        mass = lookup.loc[(*group, row.mass_scale, 1.0), "co2_eu"]
        other = lookup.loc[(*group, 1.0, row.other_scale), "co2_eu"]
        residuals.append(row.co2_eu - mass - other + base)
    out["interaction_g_km"] = residuals
    # Mark all four terms; a feasible joint point alone is insufficient.
    valid = []
    for row in out.itertuples():
        group = (row.powertrain, row.cycle, row.second_factor)
        valid.append(all(lookup.loc[(*group, a, b), "short_steps"] == 0 for a, b in
                         ((1.0, 1.0), (row.mass_scale, 1.0), (1.0, row.other_scale),
                          (row.mass_scale, row.other_scale))))
    out["engine_check_pass"] = valid
    return out


def regenerated_laps() -> pd.DataFrame:
    """Per-variant combustion-engine-limited laps, still checked by the sweep.

    The shared generator has an engine full-load curve, not a BEV motor/battery model.
    Hybrids use an engine-only acceleration envelope; no claim of optimal lap time.
    """
    parts = []
    for key, vehicle in variants().items():
        if key[0] == "bev":
            continue
        for mode in ("eco", "sport"):
            cycle = generate(mode, vehicle)
            result = sweep({key: vehicle}, {f"franco_{mode}_generated": cycle})
            result["lap_time_s"] = lap_time_s(cycle)
            parts.append(result)
    return pd.concat(parts, ignore_index=True).rename(columns={"v1": "factor", "v2": "scale"})


def extensions() -> dict[str, pd.DataFrame]:
    cycle_map = cycles()
    curves = workbook_curves()
    frames = {
        "intermediate": sweep(intermediate_variants(), cycle_map).rename(columns={"v1": "factor", "v2": "scale"}),
        "assumptions": sweep(assumption_variants(curves), cycle_map).rename(columns={"v1": "experiment", "v2": "setting"}),
        "ranges": sweep(improvement_variants(), cycle_map).rename(columns={"v1": "factor", "v2": "scale"}),
        "interactions": interactions(sweep(interaction_variants(),
                                         {c: cycle_map[c] for c in ("wltc", "franco_sport_generated")})
                                     .rename(columns={"v1": "second_factor", "v2": "mass_scale", "v3": "other_scale"})),
        "regenerated": regenerated_laps(),
        "curves": curves,
    }
    for name, frame in frames.items():
        frame.to_csv(HERE / f"study-b-{name}.csv", index=False)
    return frames
