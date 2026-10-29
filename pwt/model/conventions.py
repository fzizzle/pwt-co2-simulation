"""Everything the supplied workbooks disagree on, as one record per workbook.

The twelve sheets are three slightly different models. Reproducing each exactly is the
precondition for changing any of them, so every disagreement is a field here rather than a
branch on a filename somewhere in the physics. Harmonising the model is then a matter of
passing a different record (`HARMONISED`, below).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

#: The assignment sheet's shift speeds ("approximately 36, 57, 82, 108 kph") as the
#: Francorchamps and hybrid files implement them.
FRANCO_SHIFTS = (35.0, 57.0, 82.0, 115.0)
#: NEDC's prescribed shift speeds, used only by `33 NEDC PETROL Car.xlsx`.
NEDC_SHIFTS = (18.0, 38.0, 50.0, 70.0)


@dataclass(frozen=True, slots=True)
class Conventions:
    #: "distance": points by distance, Δt = Δs / mean speed (Francorchamps).
    #: "time": points by time, Δs = end speed × Δt (NEDC, WLTC).
    trace_kind: str
    shift_kph: tuple[float, ...] = FRANCO_SHIFTS
    #: "outside": m_driver (+ machine + battery) + m_vehicle·k. "total": m_total·k.
    eff_mass: str = "outside"
    #: Fuel burnt at standstill (gear 0), l/h. None: the engine is off.
    idle_l_per_h: float | None = 0.8
    #: Electric only: regenerative battery power is floored here (W). None: no cap.
    regen_cap_w: float | None = None
    #: Hybrids: below this state of charge the motor stops helping.
    soc_min: float = 0.3
    #: Full hybrids: buy the battery's charge back with fuel after the last step.
    fictive_recharge: bool = False
    #: g of fuel per Wh of fuel energy on the recharge line; `35` writes /11, `10`/`15` 0.0909.
    fictive_g_per_wh: float = 0.0909
    fuel_g_per_wh: float = 0.0909
    #: CO2 per litre of fuel. None: computed per kg instead (`co2_g_per_g_fuel`).
    co2_g_per_l: float | None = 2392.0
    co2_g_per_g_fuel: float | None = None
    #: Electric CO2 factor in the sheet's own CO2 column.
    grid_g_per_kwh: float | None = None
    #: Battery energy per unit of grid energy; the sheets count no charger loss.
    charger_efficiency: float = 1.0
    #: Francorchamps EV totals: CO2/km over the distance at the second-to-last point, and
    #: Wh/100 km over a hard-coded 7 km.
    ev_franco_totals: bool = False
    #: Clip engine power at the full-load curve and report the shortfall (stage B).
    capability: bool = False


_FRANCO = Conventions(trace_kind="distance")
_TIME = Conventions(trace_kind="time")

_BY_FILE: dict[str, Conventions] = {
    # petrol
    "07": _FRANCO,
    "13": _FRANCO,
    "33": replace(_TIME, shift_kph=NEDC_SHIFTS, eff_mass="total"),
    "WLTC3 PETROL": replace(_TIME, eff_mass="total"),
    # electric
    "06": replace(_FRANCO, regen_cap_w=-120_000.0, grid_g_per_kwh=220.0, ev_franco_totals=True),
    "12": replace(_FRANCO, regen_cap_w=-120_000.0, grid_g_per_kwh=220.0, ev_franco_totals=True),
    "32": replace(_TIME, grid_g_per_kwh=440.0),
    "WLTC3 ELECTRIC": replace(_TIME, grid_g_per_kwh=440.0),
    # full hybrid
    "10": replace(_FRANCO, soc_min=0.3, fictive_recharge=True),
    "15": replace(_FRANCO, soc_min=0.3, fictive_recharge=True),
    "35": replace(_TIME, idle_l_per_h=None, soc_min=0.3, fictive_recharge=True,
                  fictive_g_per_wh=1 / 11),
    "WLTC3 HYBRID": replace(_TIME, idle_l_per_h=None, soc_min=0.3, fictive_recharge=True,
                            fictive_g_per_wh=1 / 11),
    # plug-in hybrid
    "09": replace(_FRANCO, soc_min=0.23),
    "14": replace(_FRANCO, soc_min=0.23),
    "34": replace(_TIME, idle_l_per_h=None, soc_min=0.23),
    "NEDC PHYBRID": replace(_TIME, idle_l_per_h=None, soc_min=0.23),
    "WLTC3 PHYBRID": replace(_TIME, idle_l_per_h=None, soc_min=0.23),
}


def conventions_for(source_file: str) -> Conventions:
    """The conventions a supplied or derived workbook follows, by its filename."""
    for prefix in sorted(_BY_FILE, key=len, reverse=True):
        if source_file.startswith(prefix):
            return _BY_FILE[prefix]
    raise KeyError(f"no conventions recorded for {source_file!r}")


def harmonised(trace_kind: str, family: str, grid_g_per_kwh: float) -> Conventions:
    """One convention for every powertrain and cycle (stage B).

    Shift speeds and effective mass as most files have them; a conventional petrol engine
    idles at standstill while a hybrid's is off; the hybrids' battery threshold is the
    plug-in's 23 % or the full hybrid's 30 % by `family`; electric regeneration is capped at
    the Francorchamps sheets' 120 kW (the assignment sheet's motor peaks at 125 kW); heating
    value and CO2 from `constants` (CO2 per kg of fuel, so density no longer moves it); one
    grid factor, with a charger loss; no Francorchamps EV distance quirks.
    """
    from pwt.model.constants import CHARGER_EFFICIENCY, CO2_G_PER_G_PETROL, FUEL_G_PER_WH

    return Conventions(
        trace_kind=trace_kind,
        shift_kph=FRANCO_SHIFTS,
        eff_mass="outside",
        idle_l_per_h=0.8 if family == "petrol" else None,
        regen_cap_w=-120_000.0,
        soc_min=0.23 if family == "phev" else 0.3,
        fictive_recharge=family == "hybrid",
        fuel_g_per_wh=FUEL_G_PER_WH,
        fictive_g_per_wh=FUEL_G_PER_WH,
        co2_g_per_l=None,
        co2_g_per_g_fuel=CO2_G_PER_G_PETROL,
        grid_g_per_kwh=grid_g_per_kwh,
        charger_efficiency=CHARGER_EFFICIENCY,
        ev_franco_totals=False,
    )
