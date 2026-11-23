"""Model results and numeric tags for the group deck."""

from functools import cache
import re

import pandas as pd

from pwt.model import fleet
from pwt.sweep import CYCLES, START_SOC, sweep

POWERTRAINS = ("petrol", "hybrid", "phev", "bev")
CYCLE_KEYS = tuple(CYCLES)
CYCLE_LABELS: dict[str, str] = {
    key: label.removesuffix(", generated") for key, label in CYCLES.items()
}
CAR_COLOURS: dict[str, str] = {
    "petrol": "#d09539", "hybrid": "#4fb267", "phev": "#b677d5", "bev": "#3984d0",
}
_ALIASES = {"franco_eco_generated": "eco", "franco_sport_generated": "sport"}
_METRICS = {
    "co2": ("co2_eu", "g CO2/km"),
    "fuel": ("fuel_l_100km", "l/100 km"),
    "elec": ("battery_kwh_100km", "kWh/100 km"),
}
_TAG = re.compile(r"\{((?:co2|fuel|elec)\.[a-z_]+\.[a-z_]+)\}")


@cache
def baseline() -> pd.DataFrame:
    return sweep({
        ("petrol",): fleet.petrol(),
        ("hybrid",): fleet.hybrid(START_SOC["hybrid"]),
        ("phev",): fleet.plugin(START_SOC["phev"]),
        ("bev",): fleet.electric(),
    })


def cell(pt: str, cycle: str) -> pd.Series:
    frame = baseline()
    return frame.loc[(frame.powertrain == pt) & (frame.cycle == cycle)].iloc[0]


@cache
def tags() -> dict[str, str]:
    values = {}
    for row in baseline().itertuples(index=False):
        for metric, (column, unit) in _METRICS.items():
            value = getattr(row, column)
            # A car without a fuel or battery channel consumes zero of that carrier.
            amount = 0.0 if pd.isna(value) else value
            formatted = f"{amount:.1f} {unit}"
            values[f"{metric}.{row.powertrain}.{row.cycle}"] = formatted
            if row.cycle in _ALIASES:
                values[f"{metric}.{row.powertrain}.{_ALIASES[row.cycle]}"] = formatted
    return values


def fill(text: str) -> str:
    return _TAG.sub(lambda match: tags()[match[1]], text)
