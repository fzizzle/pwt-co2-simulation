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
from dashboard.labels import readable
from dashboard.layout import configure, download
from dashboard.track_charts import lap_section, mark_corners
from pwt.catalog import POWERTRAIN_NAMES
from pwt.phase2 import result_for

pal = configure("Track map")

LAPS = {"franco_sport_generated": "Francorchamps — sport",
        "franco_eco_generated": "Francorchamps — eco"}
SCENARIO = "storage losses"


@st.cache_data(show_spinner="Running the lap…")
def lap(powertrain: str, cycle: str) -> tuple[pd.DataFrame, dict]:
    result = result_for(powertrain, cycle, SCENARIO)
    return result.steps, {k: (None if v is None else float(v)) for k, v in result.headline.items()}


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
tiles = st.columns(4)
tiles[0].metric("Lap time", f"{steps['time_s'].iloc[-1]:.0f} s")
tiles[1].metric("Top speed", f"{steps['speed_kph'].max():.0f} km/h")
tiles[2].metric("Lowest speed", f"{steps['speed_kph'].min():.0f} km/h")
fuel = headline["fuel_l_100km"]
tiles[3].metric("Fuel, l/100 km" if fuel is not None else "Battery, kWh/100 km",
                f"{fuel if fuel is not None else headline['battery_kwh_100km']:.1f}")

painted, unit = lap_section({LAPS[cycle]: steps}, "track", pal)

st.subheader("The same lap along the distance")
fig = speed_and_altitude(steps, "distance_m", pal)
mark_corners(fig, steps, "distance_m", pal)
st.plotly_chart(fig, width="stretch", theme=None)

if st.toggle("Show this lap as a table"):
    table = steps[["distance_m", "time_s", "speed_kph", "altitude_m"]].assign(**{unit: painted})
    st.dataframe(readable(table), width="stretch", hide_index=True)
    download(table, f"pwt-lap-{powertrain}-{cycle}.csv")
