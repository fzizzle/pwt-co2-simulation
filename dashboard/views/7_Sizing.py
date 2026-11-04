"""What sizing the hybrids shows, one finding at a time.

Every heading states a finding and the chart under it is the evidence. Tables stay behind a
toggle; the method and caveats are in `docs/phase-3-sizing.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.layout import configure, download
from dashboard.sizing_charts import (
    HEAT_MAX_PCT, crossover, efficiency_lines, petrol_gap, phev_lines, size_heatmap,
)
from pwt.sweep import (
    CYCLES, MAX_C_RATE, best, by_battery, petrol_reference, sizing, storage_sensitivity,
)

pal = configure("Sizing")

SHORT = {"NEDC": "NEDC", "WLTC Class 3": "WLTC",
         "Francorchamps eco, generated": "Francorchamps — eco",
         "Francorchamps sport, generated": "Francorchamps — sport"}
LOSSY = 0.85


@st.cache_data(show_spinner="Running 616 hybrid sizes…")
def sizes() -> pd.DataFrame:
    return sizing()


@st.cache_data(show_spinner="Running the storage cases…")
def storage() -> tuple[pd.DataFrame, dict[str, float]]:
    return storage_sensitivity(), petrol_reference()


frame = sizes()
sensitivity, petrol = storage()
wltc = "WLTC Class 3"
band_wltc = sensitivity.xs("band", level="strategy")[wltc]
rule_wltc = sensitivity.xs("sheets' rule", level="strategy")[wltc]
rise = band_wltc[LOSSY] / band_wltc[1.0] - 1
crossing = crossover(band_wltc, rule_wltc)

st.title("Hybrid sizing")
st.markdown("### Free storage was flattering the hybrid, and its best size depends on the driving")
st.caption("Assignment vehicles. EU grid unless stated. The 85 % storage efficiency and the "
           f"{MAX_C_RATE:.0f}C battery limit are assumptions.")

top = best(frame).set_index(["powertrain", "cycle"])
fit_wltc = top.loc[("Full hybrid", wltc)]
fit_sport = top.loc[("Full hybrid", CYCLES["franco_sport_generated"])]
tiles = (
    ("Full hybrid on WLTC, with losses", f"+{rise:.0%}",
     f"{band_wltc[1.0]:.0f} → {band_wltc[LOSSY]:.0f} g CO₂/km"),
    ("Band stops paying below", f"{crossing[0]:.0%}", "energy kept each way, on WLTC"),
    ("Best full hybrid on WLTC", f"{fit_wltc['best battery (kWh)']:g} kWh",
     f"with a {fit_wltc['best motor (kW)']:g} kW motor"),
    ("Best full hybrid, Francorchamps — sport", f"{fit_sport['best battery (kWh)']:g} kWh",
     f"with a {fit_sport['best motor (kW)']:g} kW motor, set by the limits"),
)
for column, (label, value, note) in zip(st.columns(4), tiles):
    column.metric(label, value)
    column.caption(note)

# --- 1 ----------------------------------------------------------------------------------------

st.divider()
st.subheader("1. Once storing energy costs something, the band loses its lead on WLTC and NEDC")
st.markdown("The band charges the battery from the engine, and that energy now pays a loss going "
            "in and another coming out.")
cycle_label = st.segmented_control(
    "Cycle", list(CYCLES.values()), default=wltc, format_func=SHORT.get, key="storage_cycle",
) or wltc
st.plotly_chart(
    efficiency_lines(
        sensitivity.xs("band", level="strategy")[cycle_label],
        sensitivity.xs("sheets' rule", level="strategy")[cycle_label],
        petrol[cycle_label], pal,
    ),
    width="stretch", theme=None,
)
if cycle_label.startswith("Francorchamps"):
    st.caption("On the laps the band keeps its lead at every efficiency tested.")

# --- 2 ----------------------------------------------------------------------------------------

st.divider()
st.subheader("2. The full hybrid's lead over petrol shrinks, and disappears on the laps")
st.markdown("The assignment's 1.5 kWh, 25 kW hybrid with its band. Left of the line is better "
            "than petrol.")
band = sensitivity.xs("band", level="strategy")
free_gap = {SHORT[c]: (band[c][1.0] / petrol[c] - 1) * 100 for c in CYCLES.values()}
lossy_gap = {SHORT[c]: (band[c][LOSSY] / petrol[c] - 1) * 100 for c in CYCLES.values()}
st.plotly_chart(petrol_gap(free_gap, lossy_gap, pal), width="stretch", theme=None)

# --- 3 ----------------------------------------------------------------------------------------

st.divider()
st.subheader("3. WLTC barely cares about size; the Francorchamps sport lap wants power")
st.markdown(f"Each cell is one full hybrid. Both maps share a scale, capped at "
            f"{HEAT_MAX_PCT:.0f} % above the best, so the pale map really is flatter.")
hybrid = frame[frame["powertrain"] == "hybrid"]
left, right = st.columns(2)
left.markdown("**WLTC: every buildable size is within 11 % of the best**")
left.plotly_chart(size_heatmap(hybrid[hybrid["cycle"] == "wltc"], pal, show_scale=False),
                  width="stretch", theme=None)
right.markdown("**Francorchamps — sport: the spread reaches 27 %**")
right.plotly_chart(size_heatmap(hybrid[hybrid["cycle"] == "franco_sport_generated"], pal),
                   width="stretch", theme=None)
st.caption("The lap's best size sits where the 80 kW grid edge meets the 20C limit, so it marks "
           "those limits rather than a free optimum.")

# --- 4 ----------------------------------------------------------------------------------------

st.divider()
st.subheader("4. The plug-in hybrid has no single best size: it depends on how it's measured")
st.markdown("Best motor at each battery size. Both charts use the same scale.")
eu = by_battery(frame, "phev")
fr = by_battery(frame, "phev", "co2_fr")
sport = CYCLES["franco_sport_generated"]
ymax = max(eu[wltc].max(), eu[sport].max()) * 1.1
left, right = st.columns(2)
left.markdown("**WLTC: R101 weighting keeps rewarding range**")
left.plotly_chart(phev_lines(eu[wltc], fr[wltc], ymax, (20.0, "Still falling at<br>the grid edge"),
                             pal), width="stretch", theme=None)
right.markdown("**One Francorchamps sport lap: past 6 kWh, a battery is only mass**")
right.plotly_chart(phev_lines(eu[sport], fr[sport], ymax, (6.0, "Enough for<br>the whole lap"),
                              pal), width="stretch", theme=None)

# --- tables -----------------------------------------------------------------------------------

st.divider()
if st.toggle("Show the figures as tables"):
    st.markdown("**Storage efficiency, g CO₂/km**")
    table = sensitivity.reset_index()
    st.dataframe(table, width="stretch", hide_index=True)
    download(table, "pwt-storage-efficiency.csv")
    st.markdown("**Every size**")
    st.dataframe(frame, width="stretch", hide_index=True)
    download(frame, "pwt-hybrid-sizing.csv")
