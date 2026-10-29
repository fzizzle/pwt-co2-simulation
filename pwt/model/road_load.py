"""Kinematics and forces, shared by every powertrain.

Each array has one entry per cycle point. Index 0 is the initial state: its step quantities
(Δt, Δs, a, forces) are zero and nothing is summed from it, as sheet row 3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pwt.model.conventions import Conventions
from pwt.model.cycle import Cycle
from pwt.model.vehicle import Vehicle


def gears(v_kph: np.ndarray, shifts: tuple[float, ...]) -> np.ndarray:
    """The sheets' nested IF: 0 at rest, then 1 up to the first shift speed, and so on."""
    gear = 1 + (v_kph[:, None] > np.asarray(shifts)[None, :]).sum(axis=1)
    return np.where(v_kph == 0, 0, gear)


def road_load(cycle: Cycle, vehicle: Vehicle, conv: Conventions) -> pd.DataFrame:
    v = cycle.v_kph / 3.6
    n = len(cycle)
    dt = np.zeros(n)
    ds = np.zeros(n)
    if conv.trace_kind == "distance":
        ds[1:] = np.diff(cycle.s)
        dt[1:] = ds[1:] / ((v[1:] + v[:-1]) / 2)
        t = np.cumsum(dt)
        s = cycle.s
        dz = np.zeros(n)
        dz[1:] = np.diff(cycle.z)
        slope = np.zeros(n)
        slope[1:] = np.arctan(dz[1:] / ds[1:])
    else:
        t = cycle.t
        dt[1:] = np.diff(t)
        ds[1:] = v[1:] * dt[1:]
        s = np.cumsum(ds)
        slope = np.zeros(n)

    a = np.zeros(n)
    with np.errstate(divide="ignore", invalid="ignore"):
        a[1:] = np.where(dt[1:] != 0, (v[1:] - v[:-1]) / dt[1:], 0.0)

    wheel = v / (vehicle.wheel_diameter_m / 2)
    m = vehicle.m_total
    resistive = (
        m * vehicle.g * vehicle.f_roll
        + m * vehicle.g * np.sin(slope)
        + 0.5 * vehicle.rho_air * vehicle.scx * v * v
    )

    if vehicle.family == "bev":
        ratio = vehicle.ratios[0]
        engine = wheel * ratio
        gear = None
        accel_force = vehicle.effective_mass(ratio, conv.eff_mass) * a
    else:
        gear = cycle.gear if cycle.gear is not None else gears(cycle.v_kph, conv.shift_kph)
        ratios = np.array((np.nan,) + vehicle.ratios)
        engine = np.where(gear == 0, vehicle.idle_rads, ratios[gear] * wheel)
        m_eff = np.array(
            (0.0,) + tuple(vehicle.effective_mass(r, conv.eff_mass) for r in vehicle.ratios)
        )
        accel_force = m_eff[gear] * a
    accel_force[0] = 0.0
    total = resistive + accel_force

    frame = pd.DataFrame(
        {
            "delta_time_s": dt,
            "delta_distance_m": ds,
            "time_s": t,
            "distance_m": s,
            "altitude_m": cycle.z,
            "speed_kph": cycle.v_kph,
            "speed_ms": v,
            "acceleration_ms2": a,
            "wheel_speed_rads": wheel,
            "engine_speed_rads": engine,
            "engine_speed_rpm": engine * 60 / (2 * np.pi),
            "slope_rad": slope,
            "resistive_force_n": resistive,
            "acceleration_force_n": accel_force,
            "total_force_n": total,
        }
    )
    if gear is not None:
        frame.insert(frame.columns.get_loc("acceleration_ms2"), "gear", gear)
    mean_v = np.zeros(n)
    mean_v[1:] = (v[1:] + v[:-1]) / 2
    frame["mean_speed_ms"] = mean_v
    if cycle.phase is not None:
        frame["phase"] = cycle.phase
    return frame
