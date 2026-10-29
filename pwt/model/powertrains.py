"""Wheel power to fuel, electricity and CO2, one function per powertrain family.

Each mirrors its workbooks column by column (see `docs/model-equations.md`) and returns the
road-load frame with the powertrain's columns added, named as `pwt.workbook.TRACE_ALIASES`
names them, so a result compares directly with `Run.trace`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pwt.model.conventions import Conventions
from pwt.model.vehicle import Vehicle


def full_load_w(vehicle: Vehicle, engine_rads: np.ndarray) -> np.ndarray:
    """Maximum engine power at a speed: linear to the knee, then flat (assignment sheet)."""
    rpm = engine_rads * 60 / (2 * np.pi)
    return vehicle.p_max_w * np.clip(rpm / vehicle.full_load_knee_rpm, 0.0, 1.0)


def _co2(conv: Conventions, fuel_l, fuel_g):
    if conv.co2_g_per_l is not None:
        return fuel_l * conv.co2_g_per_l
    return fuel_g * conv.co2_g_per_g_fuel


def _idle_l(conv: Conventions, dt):
    return 0.0 if conv.idle_l_per_h is None else conv.idle_l_per_h * dt / 3600


def petrol(frame: pd.DataFrame, vehicle: Vehicle, conv: Conventions) -> pd.DataFrame:
    f = frame.copy()
    force, dt, gear = f["total_force_n"], f["delta_time_s"], f["gear"]
    wheel = np.where(force > 0, force * f["mean_speed_ms"], 0.0)
    engine = wheel / vehicle.eta_drivetrain
    if conv.capability:
        limit = full_load_w(vehicle, f["engine_speed_rads"].to_numpy())
        f["shortfall_w"] = np.maximum(engine - limit, 0.0)
        engine = np.minimum(engine, limit)
    energy = np.where(force < 0, 0.0, engine * dt / 3600)
    eff = vehicle.efficiency(engine)
    fuel_g = energy * conv.fuel_g_per_wh / eff
    fuel_l = np.where(gear == 0, _idle_l(conv, dt), fuel_g / vehicle.fuel_density)
    if conv.co2_g_per_l is None:
        # Per kg: idle fuel needs a mass too.
        fuel_g = np.where(gear == 0, fuel_l * vehicle.fuel_density, fuel_g)
    f["engine_power_w"] = wheel
    f["engine_power_drivetrain_w"] = engine
    f["engine_torque_nm"] = engine / f["engine_speed_rads"]
    f["energy_wh"] = energy
    f["engine_efficiency"] = eff
    f["qfuel_g"] = fuel_g
    f["qfuel_l"] = fuel_l
    f["emission_g_co2"] = _co2(conv, fuel_l, fuel_g)
    return _zero_initial(f)


def electric(frame: pd.DataFrame, vehicle: Vehicle, conv: Conventions) -> pd.DataFrame:
    f = frame.copy()
    force, dt = f["total_force_n"].to_numpy(), f["delta_time_s"].to_numpy()
    omega = f["engine_speed_rads"].to_numpy()
    rpm = f["engine_speed_rpm"].to_numpy()
    wheel = force * f["mean_speed_ms"].to_numpy()
    drive = np.where(force > 0, wheel / vehicle.eta_drivetrain, wheel * vehicle.eta_drivetrain)

    a, b, c = vehicle.motor_eff
    poly = a * rpm * rpm + b * rpm + c
    prev_poly = np.concatenate(([poly[0]], poly[:-1]))
    eff_pct = np.where(drive >= 0, poly, prev_poly)  # regeneration reads the previous speed
    eff = eff_pct / 100

    battery_uncapped = np.where(drive > 0, drive / eff, drive * eff)
    battery = battery_uncapped
    if conv.regen_cap_w is not None:
        battery = np.where(
            drive > 0, drive / eff,
            np.where(drive < conv.regen_cap_w, conv.regen_cap_w * eff, drive * eff),
        )
    energy = battery * dt / 3600
    co2 = (conv.grid_g_per_kwh or 0.0) / 1000 * energy

    prev_omega = np.concatenate(([omega[0]], omega[:-1]))
    with np.errstate(divide="ignore", invalid="ignore"):
        torque = np.where(drive > 0, drive / omega, drive / ((prev_omega + omega) / 2))
        torque_dl = np.where(omega != 0, drive / omega, 0.0)
        battery_torque = np.where(omega != 0, battery_uncapped / omega, 0.0)
    prev_drive = np.concatenate(([0.0], drive[:-1]))

    f["wheel_power_w"] = wheel
    f["engine_power_w"] = wheel
    f["engine_power_drivetrain_w"] = drive
    f["engine_torque_nm"] = torque
    f["engine_torque_drivetrain_nm"] = torque_dl
    f["efficiency_pct"] = eff_pct
    f["total_engine_power_w"] = battery
    f["total_engine_torque_nm"] = np.where(drive > 0, torque / eff, torque * eff)
    f["battery_engine_power_w"] = battery_uncapped
    f["battery_engine_torque_nm"] = battery_torque
    f["energy_wh"] = energy
    f["co2_g"] = co2
    f["emission_g_co2"] = co2
    f["energy_to_move_car_wh"] = (drive + prev_drive) / 2 * dt / 3600
    return _zero_initial(f)


def hybrid(frame: pd.DataFrame, vehicle: Vehicle, conv: Conventions, strategy=None):
    """Full and plug-in hybrid. Returns (steps, recharge), `recharge` the fictive end line."""
    from pwt.model.strategy import NelisStrategy

    strategy = strategy or NelisStrategy()
    f = frame.copy()
    force = f["total_force_n"].to_numpy()
    dt = f["delta_time_s"].to_numpy()
    gear = f["gear"].to_numpy()
    wheel = force * f["mean_speed_ms"].to_numpy()
    demand = np.where(force >= 0, wheel / vehicle.eta_drivetrain, wheel * vehicle.eta_drivetrain)
    demand[0] = 0.0
    battv = demand * dt / 3600

    n = len(f)
    fact = np.zeros(n)
    engine_wh = np.zeros(n)
    soc = np.zeros(n)
    engine_power = np.zeros(n)  # the power the efficiency curve is read at
    soc[0] = vehicle.soc0
    for i in range(1, n):
        share, engine_wh[i], engine_power[i], charge_wh = strategy.step(
            vehicle, conv, soc[i - 1], demand[i], dt[i], braking=force[i] < 0,
        )
        fact[i] = share
        soc[i] = soc[i - 1] - (share * battv[i] - charge_wh) / vehicle.battery_wh

    if conv.capability:
        limit = full_load_w(vehicle, f["engine_speed_rads"].to_numpy())
        engine_share_w = np.where(dt > 0, engine_wh * 3600 / np.where(dt > 0, dt, 1), 0.0)
        f["shortfall_w"] = np.maximum(engine_share_w - limit, 0.0)

    eff = np.where(engine_wh > 0, vehicle.efficiency(engine_power), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        fuel_g = np.where(engine_wh > 0, engine_wh * conv.fuel_g_per_wh / eff, 0.0)
    fuel_l = np.where(gear == 0, _idle_l(conv, dt), fuel_g / vehicle.fuel_density)
    if conv.co2_g_per_l is None:
        fuel_g = np.where(gear == 0, fuel_l * vehicle.fuel_density, fuel_g)

    f["engine_power_w"] = wheel
    f["engine_power_drivetrain_w"] = demand
    f["engine_torque_nm"] = demand / f["engine_speed_rads"]
    f["battv"] = battv
    f["fact"] = fact
    f["energy_wh"] = engine_wh
    f["batt_soc"] = soc
    f["engine_efficiency"] = eff
    f["qfuel_g"] = fuel_g
    f["qfuel_l"] = fuel_l
    f["emission_g_co2"] = _co2(conv, fuel_l, fuel_g)
    f = _zero_initial(f, keep=("batt_soc",))

    recharge = None
    if conv.fictive_recharge:
        wh = vehicle.battery_wh * (soc[0] - soc[-1])
        g = wh * conv.fictive_g_per_wh / vehicle.eta_max if wh > 0 else 0.0
        litres = g / vehicle.fuel_density
        recharge = {
            "energy_wh": wh,
            "batt_soc": soc[-1] + wh / vehicle.battery_wh,
            "qfuel_g": g,
            "qfuel_l": litres,
            "emission_g_co2": float(_co2(conv, litres, g)),
        }
    return f, recharge


#: Step quantities that sheet row 3 holds as 0 or copies of the last row; zeroing them keeps
#: every sum honest.
_STEP_COLUMNS = (
    "energy_wh", "qfuel_g", "qfuel_l", "emission_g_co2", "co2_g", "energy_to_move_car_wh",
    "battv", "fact",
)


def _zero_initial(frame: pd.DataFrame, keep: tuple[str, ...] = ()) -> pd.DataFrame:
    for column in _STEP_COLUMNS:
        if column in frame and column not in keep:
            frame.loc[0, column] = 0.0
    return frame
