"""The generated Francorchamps laps on the circuit: model output for the assignment vehicles."""

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
from dashboard.theme import style_axes
from dashboard.track_charts import lap_section, mark_corners
from pwt import phase2
from pwt.catalog import POWERTRAIN_NAMES
from pwt.model import fleet
from pwt.model.constants import GRID_G_PER_KWH
from pwt.model.profile import generate
from pwt.sweep import CYCLES

pal = configure("Track map")

LAPS = {
    "franco_sport_generated": CYCLES["franco_sport_generated"],
    "franco_eco_generated": CYCLES["franco_eco_generated"],
}
SCENARIO = "storage losses"


@st.cache_data(show_spinner="Running the lap…")
def lap(powertrain: str, cycle: str) -> tuple[pd.DataFrame, dict, tuple[int, float]]:
    result = phase2.result_for(powertrain, cycle, SCENARIO)
    headline = {k: (None if v is None else float(v)) for k, v in result.headline.items()}
    vehicle = {
        "petrol": fleet.petrol,
        "bev": fleet.electric,
        "hybrid": lambda: fleet.hybrid(1.0),
        "phev": lambda: fleet.plugin(0.98),
    }[powertrain]()
    cyc = generate(phase2.GENERATED[cycle], fleet.petrol())
    _, shortfall = phase2.powertrain_cells(powertrain, cycle, vehicle, cyc, SCENARIO)
    return result.steps, headline, shortfall


st.title("Track map")
st.caption(
    f"Model output for the assignment vehicles. Storage losses included. "
    f"EU grid ({GRID_G_PER_KWH['EU']:.0f} g CO₂/kWh)."
)

cycle = (
    st.segmented_control(
        "Driving cycle", list(LAPS), default="franco_sport_generated", format_func=LAPS.get
    )
    or "franco_sport_generated"
)
powertrain = (
    st.segmented_control(
        "Powertrain", list(POWERTRAIN_NAMES), default="petrol", format_func=POWERTRAIN_NAMES.get
    )
    or "petrol"
)

steps, headline, (short_steps, short_kw) = lap(powertrain, cycle)
tiles = st.columns(4)
tiles[0].metric("Lap time", f"{steps['time_s'].iloc[-1]:.0f} s")
tiles[1].metric("Maximum speed", f"{steps['speed_kph'].max():.0f} km/h")
tiles[2].metric("Minimum speed", f"{steps['speed_kph'].min():.0f} km/h")
fuel = headline["fuel_l_100km"]
if fuel is not None:
    tiles[3].metric("Fuel consumption", f"{fuel:.1f} l/100 km")
else:
    tiles[3].metric("Battery energy", f"{headline['battery_kwh_100km']:.1f} kWh/100 km")

if powertrain == "bev":
    st.caption("Engine power check: does not apply to Battery electric.")
elif short_steps > 0:
    step_unit = "step" if short_steps == 1 else "steps"
    st.warning(
        f"Provisional — engine power falls short on {short_steps} {step_unit} "
        f"(maximum shortfall {short_kw:.1f} kW).",
        icon="⚠️",
    )
else:
    st.caption("Engine power check: pass (0 short steps).")

painted, unit = lap_section({LAPS[cycle]: steps}, "track", pal, source="model")

st.subheader("Speed and altitude by distance")
fig = speed_and_altitude(steps, "distance_m", pal)
style_axes(fig, pal, x_title="Distance (m)")
mark_corners(fig, steps, "distance_m", pal)
st.plotly_chart(fig, width="stretch", theme=None)

if st.toggle("Show lap table"):
    table = steps[["distance_m", "time_s", "speed_kph", "altitude_m"]].copy()
    selected_metric = st.session_state.get("track_paint", "Speed")
    if selected_metric not in ("Speed", "Altitude"):
        table[f"{selected_metric} ({unit})"] = painted.to_numpy()
    st.dataframe(readable(table), width="stretch", hide_index=True)
    download(table, f"pwt-lap-{powertrain}-{cycle}.csv", "Download lap table (CSV)")
