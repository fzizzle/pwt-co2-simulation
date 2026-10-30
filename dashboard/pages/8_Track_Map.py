"""The generated Francorchamps laps on the real circuit: where each car spends its energy."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.charts import speed_and_altitude
from dashboard.layout import configure, download
from dashboard.track_charts import lap_map
from pwt.catalog import POWERTRAIN_NAMES
from pwt.phase2 import result_for

pal = configure("Track map")

LAPS = {"franco_sport_generated": "Sport lap", "franco_eco_generated": "Eco lap"}
SCENARIO = "storage losses"
PAINTS = ("Speed", "Power demand", "CO₂ emitted here", "Altitude", "Battery charge")


@st.cache_data(show_spinner="Running the lap…")
def lap(powertrain: str, cycle: str) -> tuple[pd.DataFrame, dict]:
    result = result_for(powertrain, cycle, SCENARIO)
    return result.steps, {k: (None if v is None else float(v)) for k, v in result.headline.items()}


def metrics(steps: pd.DataFrame) -> dict[str, tuple[pd.Series, str, bool]]:
    """Choice → (value per step, unit, diverging around zero)."""
    per_km = (steps["emission_g_co2"] / steps["delta_distance_m"].where(lambda d: d > 0) * 1000
              ).fillna(0.0).clip(lower=0)
    out = {
        "Speed": (steps["speed_kph"], "km/h", False),
        "Power demand": (steps["engine_power_drivetrain_w"] / 1000, "kW", True),
        "CO₂ emitted here": (per_km, "g/km", False),
        "Altitude": (steps["altitude_m"], "m", False),
    }
    if "batt_soc" in steps:
        out["Battery charge"] = (steps["batt_soc"] * 100, "%", False)
    return out


st.title("Track map")
st.markdown("### Where a lap of Spa-Francorchamps spends its energy")
st.caption("The generated laps with the assignment vehicles, on the real circuit. Press **Play** "
           "to drive the lap, or drag the slider. Hover the track for the figures.")

pick_lap, pick_car = st.columns([1, 2])
cycle = pick_lap.segmented_control("Lap", list(LAPS), default="franco_sport_generated",
                                   format_func=LAPS.get) or "franco_sport_generated"
powertrain = pick_car.segmented_control("Powertrain", list(POWERTRAIN_NAMES), default="petrol",
                                        format_func=POWERTRAIN_NAMES.get) or "petrol"
steps, headline = lap(powertrain, cycle)
choices = metrics(steps)
# The options stay the same for every car, so changing car keeps the choice.
metric = st.segmented_control("Paint the track with", PAINTS, default="Speed",
                              key="paint") or "Speed"
if metric not in choices:
    st.caption("The model tracks battery charge for the two hybrids only, so this shows speed.")
    metric = "Speed"
values, unit, diverging = choices[metric]

tiles = st.columns(4)
tiles[0].metric("Lap time", f"{steps['time_s'].iloc[-1]:.0f} s")
tiles[1].metric("Top speed", f"{steps['speed_kph'].max():.0f} km/h")
tiles[2].metric("Lowest speed", f"{steps['speed_kph'].min():.0f} km/h")
fuel = headline["fuel_l_100km"]
tiles[3].metric("Fuel, l/100 km" if fuel is not None else "Battery, kWh/100 km",
                f"{fuel if fuel is not None else headline['battery_kwh_100km']:.1f}")

st.plotly_chart(lap_map(steps, values, metric, unit, diverging, pal), width="stretch", theme=None,
                config={"scrollZoom": True})
if metric == "CO₂ emitted here":
    st.caption("CO₂ at each point only. It leaves out the electricity a plug-in hybrid recharges "
               "and the fuel a full hybrid burns to buy back its battery, which the lap totals "
               "elsewhere include.")

st.subheader("The same lap along the distance")
st.plotly_chart(speed_and_altitude(steps, "distance_m", pal), width="stretch", theme=None)

st.caption("Circuit outline: [bacinger/f1-circuits](https://github.com/bacinger/f1-circuits), MIT "
           "licence. Map tiles © OpenStreetMap contributors, © CARTO. The outline is coarse and "
           "the laps use a single line, so positions are good to about 100 m. Corner names are "
           "placed by hand.")
if st.toggle("Show this lap as a table"):
    table = steps[["distance_m", "time_s", "speed_kph", "altitude_m"]].assign(**{unit: values})
    st.dataframe(table, width="stretch", hide_index=True)
    download(table, f"pwt-lap-{powertrain}-{cycle}.csv")
