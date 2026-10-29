"""The four vehicles as the assignment sheet defines them, rather than as the workbooks do.

Where the sheet gives a range, the midpoint is taken; where it gives nothing, the
workbooks' value is kept and named in `notes`.
"""

from __future__ import annotations

from pwt.model.constants import PETROL_DENSITY
from pwt.model.vehicle import Vehicle

#: Wh per kg: the sheet's 150 Wh/kg, cell-level (the workbooks double it for the pack).
BATTERY_WH_PER_KG = 150.0

_BODY = dict(
    wheel_diameter_m=0.6345,  # 195-65-R15, 634.5 mm
    m_driver=80.0,
    g=9.81,
    frontal_area=2.69,
    cx=0.31,
    rho_air=1.2,
    f_roll=0.015,  # not in the sheet; the workbooks' value
    eta_drivetrain=0.95,
)
_ENGINE = dict(
    ratios=(12.526, 7.588, 5.052, 3.428, 2.525),
    # The sheet gives 20-40 % "NA to downsized" and no curve; the workbooks' "modern" curve,
    # rescaled to the sheet's 74 kW engine.
    eta_max=0.35, a1=-0.3867, a2=0.6285, a3=0.7516,
    p_max_w=74_000.0,
    p_rated_w=74_000.0,
    fuel_density=PETROL_DENSITY,
    idle_rpm=800.0,
)
#: The workbooks' motor map (peak 94.5 % at 4917 rpm); the sheet gives a 94 % maximum.
_MOTOR_MAP = (-6e-07, 0.0059, 80.0)

_NOTES = (
    "rolling resistance 0.015 and the efficiency curve's shape are the workbooks'",
    "battery mass at the sheet's 150 Wh/kg, not doubled for the pack",
)


def petrol() -> Vehicle:
    return Vehicle(family="ice", m_vehicle=1280.0, notes=_NOTES, **_BODY, **_ENGINE)


def electric() -> Vehicle:
    # 1460 kg with its 22 kWh battery, 1230 kg car only.
    return Vehicle(
        family="bev", ratios=(6.218,), m_vehicle=1230.0, m_battery=230.0,
        battery_wh=22_000.0, motor_eff=_MOTOR_MAP, notes=_NOTES, **_BODY,
    )


def hybrid(soc0: float = 1.0) -> Vehicle:
    """Petrol car + 100 kg machine and inverter + 1.5 kWh; 25 kW (sheet: 20-30 kW)."""
    return Vehicle(
        family="hybrid", m_vehicle=1280.0, m_machine=100.0,
        m_battery=1500.0 / BATTERY_WH_PER_KG, battery_wh=1500.0, p_motor_w=25_000.0,
        soc0=soc0, notes=_NOTES, **_BODY, **_ENGINE,
    )


def plugin(soc0: float = 0.98) -> Vehicle:
    """Petrol car + 100 kg + 15 kWh (sheet: 10-20); 45 kW (sheet: 40-50 kW)."""
    return Vehicle(
        family="hybrid", m_vehicle=1280.0, m_machine=100.0,
        m_battery=15_000.0 / BATTERY_WH_PER_KG, battery_wh=15_000.0, p_motor_w=45_000.0,
        soc0=soc0, notes=_NOTES, **_BODY, **_ENGINE,
    )
