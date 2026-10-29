"""Totals, keyed as `Run.totals` and the derived workbooks' added rows key them.

The model reports the union of what every workbook in its family reports, each computed the
way that workbook computes it, so the golden tests can compare whatever a given sheet has.
"""

from __future__ import annotations

import pandas as pd

from pwt.model.conventions import Conventions
from pwt.model.vehicle import Vehicle

Key = tuple[str, str]
GRID_REPORTING = {"eu": 250.0, "fr": 73.0}


def _km(frame: pd.DataFrame) -> float:
    return frame["delta_distance_m"].sum() / 1000


def _phases(frame: pd.DataFrame):
    if "phase" not in frame:
        return []
    return [(name, frame[frame["phase"] == name]) for name in pd.unique(frame["phase"])]


def totals(frame: pd.DataFrame, vehicle: Vehicle, conv: Conventions,
           recharge: dict | None = None) -> dict[Key, float]:
    if vehicle.family == "bev":
        return _electric(frame, conv)
    return _engine(frame, vehicle, conv, recharge)


def _engine(frame, vehicle, conv, recharge) -> dict[Key, float]:
    km = _km(frame)
    extra = recharge or {}
    litres = frame["qfuel_l"].sum() + extra.get("qfuel_l", 0.0)
    co2 = frame["emission_g_co2"].sum() + extra.get("emission_g_co2", 0.0)
    energy = frame["energy_wh"].sum() + extra.get("energy_wh", 0.0)
    out: dict[Key, float] = {
        ("total consumption", "l/100km"): litres / (km / 100),
        ("total emission", "g co2"): co2,
        ("total emission", "g co2/km"): co2 / km,
        ("energy to move the car", "wh/100km"): 100 * energy / km,
    }
    out[("total fuel energy", "wh/100km")] = out[("energy to move the car", "wh/100km")] / (
        vehicle.eta_max
    )
    for name, part in _phases(frame):
        p_km = _km(part)
        label = name.lower()
        out[(f"{label} consumption", "l/100km")] = part["qfuel_l"].sum() / (p_km / 100)
        out[(f"{label} distance", "m")] = p_km * 1000
        out[(f"{label} emission", "g co2/km")] = part["emission_g_co2"].sum() / p_km
    if "batt_soc" in frame:
        used = vehicle.battery_wh * (frame["batt_soc"].iloc[0] - frame["batt_soc"].iloc[-1])
        out[("final state of charge", "")] = frame["batt_soc"].iloc[-1]
        out[("battery energy used", "wh")] = used
        out[("battery energy used", "wh/100km")] = 100 * used / km
        for region, factor in GRID_REPORTING.items():
            out[(f"grid emission {region}", "g co2/km")] = (
                factor / 1000 * used / km / conv.charger_efficiency
            )
    return out


def _electric(frame, conv) -> dict[Key, float]:
    km = _km(frame)
    energy = frame["energy_wh"].sum()
    co2 = frame["emission_g_co2"].sum()
    out: dict[Key, float] = {
        ("total emission", "g co2/km"): co2 / km,
        ("total energy use", "wh/100km"): 100 * energy / km,
        ("energy to move the car", "wh/100km"): 100 * frame["energy_to_move_car_wh"].sum() / km,
    }
    if conv.ev_franco_totals:
        # CO2 over the distance at the second-to-last point; energy over a hard-coded 7 km.
        out[("emission", "g co2")] = co2
        out[("emission", "g co2/km")] = co2 / (frame["distance_m"].iloc[-2] / 1000)
        out[("energy", "wh")] = energy
        out[("total energy used", "wh/100km")] = energy / 7 * 100
    for name, part in _phases(frame):
        p_km = _km(part)
        label = name.lower()
        out[(f"{label} emission", "g co2")] = part["emission_g_co2"].sum()
        out[(f"{label} emission", "g co2/km")] = part["emission_g_co2"].sum() / p_km
        out[(f"{label} energy use", "wh")] = part["energy_wh"].sum()
        out[(f"{label} energy use", "wh/100km")] = 100 * part["energy_wh"].sum() / p_km
        out[(f"{label} distance", "m")] = p_km * 1000
    return out


def headline(totals_: dict[Key, float], family: str) -> dict[str, float | None]:
    """The figures every comparison wants, whatever the sheet called them."""
    if family == "bev":
        energy = totals_.get(("total energy used", "wh/100km"),
                             totals_[("total energy use", "wh/100km")])
        co2 = totals_.get(("emission", "g co2/km"), totals_[("total emission", "g co2/km")])
        return {"fuel_l_100km": None, "battery_kwh_100km": energy / 1000, "co2_g_km": co2}
    battery = totals_.get(("battery energy used", "wh/100km"))
    return {
        "fuel_l_100km": totals_[("total consumption", "l/100km")],
        "battery_kwh_100km": None if battery is None else battery / 1000,
        "co2_g_km": totals_[("total emission", "g co2/km")],
    }


__all__ = ["totals", "headline"]
