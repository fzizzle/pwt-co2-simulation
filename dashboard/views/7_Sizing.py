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

from dashboard.layout import configure, download, show_chart
from dashboard.sizing_charts import (
    HEAT_MAX_PCT,
    PROVISIONAL_LABEL,
    best_by_battery,
    best_selection,
    crossover,
    efficiency_lines,
    petrol_gap,
    phev_lines,
    size_heatmap,
)
from pwt.sweep import (
    CYCLES, MAX_C_RATE, petrol_reference, sizing, storage_sensitivity,
)

pal = configure("Hybrid sizing")

SHORT = {"NEDC": "NEDC", "WLTC Class 3": "WLTC",
         CYCLES["franco_eco_generated"]: CYCLES["franco_eco_generated"],
         CYCLES["franco_sport_generated"]: CYCLES["franco_sport_generated"]}


def _motor(kw: float) -> str:
    """'a 50 kW motor', 'an 80 kW motor': the article follows how the number is said."""
    text = f"{kw:g}"
    article = "an" if text.startswith("8") or text in ("11", "18") else "a"
    return f"{article} {text} kW motor"
LOSSY = 0.85

st.title("Hybrid sizing")
st.markdown("### Free storage was flattering the hybrid, and its best size depends on the driving")
st.caption("Assignment vehicles. EU grid unless stated. The 85 % storage efficiency and the "
           f"{MAX_C_RATE:.0f}C battery limit are assumptions.")


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

hybrid = frame[frame["powertrain"] == "hybrid"]
hyb_wltc_sel = best_selection(hybrid[hybrid["cycle"] == "wltc"])
hyb_sport_sel = best_selection(hybrid[hybrid["cycle"] == "franco_sport_generated"])
fit_wltc = hyb_wltc_sel["feasible"] if hyb_wltc_sel["feasible"] is not None else hyb_wltc_sel["provisional"]
fit_sport = hyb_sport_sel["feasible"] if hyb_sport_sel["feasible"] is not None else hyb_sport_sel["provisional"]
wltc_note = f"with {_motor(fit_wltc['motor_kw'])}" + (
    f" ({PROVISIONAL_LABEL})" if hyb_wltc_sel["feasible"] is None else ""
)
sport_note = f"with {_motor(fit_sport['motor_kw'])}, set by the limits" + (
    f" ({PROVISIONAL_LABEL})" if hyb_sport_sel["feasible"] is None else ""
)
tiles = (
    ("WLTC hybrid, with losses", f"+{rise:.0%}",
     f"{band_wltc[1.0]:.0f} → {band_wltc[LOSSY]:.0f} g CO₂/km"),
    ("Band stops paying below", f"{crossing[0]:.0%}", "energy kept each way, on WLTC"),
    ("Best full hybrid on WLTC", f"{fit_wltc['battery_kwh']:g} kWh", wltc_note),
    ("Best full hybrid, sport lap", f"{fit_sport['battery_kwh']:g} kWh", sport_note),
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
show_chart(efficiency_lines(
        sensitivity.xs("band", level="strategy")[cycle_label],
        sensitivity.xs("sheets' rule", level="strategy")[cycle_label],
        petrol[cycle_label], pal,
    ))
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
show_chart(petrol_gap(free_gap, lossy_gap, pal))

# --- 3 ----------------------------------------------------------------------------------------

st.divider()
st.subheader("3. WLTC barely cares about size; the Francorchamps sport lap wants power")
st.markdown(f"Each cell is one full hybrid. Both maps share a scale, capped at "
            f"{HEAT_MAX_PCT:.0f} % above the best, so the pale map really is flatter.")
left, right = st.columns(2)
left.markdown("**WLTC: every buildable size is within 11 % of the best**")
left.plotly_chart(size_heatmap(hybrid[hybrid["cycle"] == "wltc"], pal, show_scale=True),
                  width="stretch", theme=None)
right.markdown(f"**{CYCLES['franco_sport_generated']}: the spread reaches 27 %**")
right.plotly_chart(size_heatmap(hybrid[hybrid["cycle"] == "franco_sport_generated"], pal),
                   width="stretch", theme=None)
st.caption(
    f"The lap's best size sits where the 80 kW grid edge meets the {MAX_C_RATE:.0f}C limit, so it "
    "marks those limits rather than a free optimum. Engine check: "
    f"{hyb_wltc_sel['feasible_count']} of {hyb_wltc_sel['buildable_count']} buildable sizes pass "
    f"on WLTC Class 3; {hyb_sport_sel['feasible_count']} of {hyb_sport_sel['buildable_count']} "
    "pass on Francorchamps sport, generated."
)

# --- 4 ----------------------------------------------------------------------------------------

st.divider()
st.subheader("4. The plug-in hybrid has no single best size: it depends on how it's measured")
st.markdown(
    "Best motor at each battery size. Both charts use the same scale. "
    f"Hollow markers and dashed segments are **{PROVISIONAL_LABEL}**."
)
eu_wltc = best_by_battery(frame, "phev", "wltc", "co2_eu")
fr_wltc = best_by_battery(frame, "phev", "wltc", "co2_fr")
eu_wltc_feas = best_by_battery(frame, "phev", "wltc", "co2_eu", feasible_only=True)
fr_wltc_feas = best_by_battery(frame, "phev", "wltc", "co2_fr", feasible_only=True)

eu_sport = best_by_battery(frame, "phev", "franco_sport_generated", "co2_eu")
fr_sport = best_by_battery(frame, "phev", "franco_sport_generated", "co2_fr")
eu_sport_feas = best_by_battery(frame, "phev", "franco_sport_generated", "co2_eu", feasible_only=True)
fr_sport_feas = best_by_battery(frame, "phev", "franco_sport_generated", "co2_fr", feasible_only=True)

phev_wltc_sel = best_selection(frame[(frame["powertrain"] == "phev") & (frame["cycle"] == "wltc")])
phev_sport_sel = best_selection(
    frame[(frame["powertrain"] == "phev") & (frame["cycle"] == "franco_sport_generated")]
)


def _selection_caption(selection: dict[str, object], all_points: pd.DataFrame) -> str:
    feas = selection["feasible"]
    prov = selection["provisional"]
    parts = []
    if feas is None:
        parts.append(
            f"Feasible set: empty (0 of {selection['buildable_count']} buildable sizes pass "
            "the engine check)."
        )
    else:
        parts.append(
            f"Feasible lowest (EU grid): {feas['battery_kwh']:g} kWh, {feas['motor_kw']:g} kW — "
            f"{feas['co2_eu']:.1f} g CO₂/km ({selection['feasible_count']} of "
            f"{selection['buildable_count']} buildable sizes pass)."
        )
    if prov is not None:
        parts.append(
            f"Provisional lowest (EU grid): {prov['battery_kwh']:g} kWh, {prov['motor_kw']:g} kW — "
            f"{prov['co2_eu']:.1f} g CO₂/km ({int(prov['short_steps'])} short steps, "
            f"≤ {prov['short_kw']:.1f} kW; {PROVISIONAL_LABEL})."
        )
    elif int(all_points["provisional"].sum()) > 0:
        n_short = int(selection["buildable_count"]) - int(selection["feasible_count"])
        parts.append(
            f"Provisional points ({n_short} of {selection['buildable_count']} buildable sizes "
            f"short of the trace) are shown hollow/dashed."
        )
    return " ".join(parts)


ymax = max(
    eu_wltc["co2"].max(),
    eu_sport["co2"].max(),
    eu_sport_feas["co2"].max() if not eu_sport_feas.empty else 0.0,
) * 1.1
left, right = st.columns(2)
left.markdown("**WLTC: R101 weighting keeps rewarding range**")
left.plotly_chart(
    phev_lines(
        eu_wltc, fr_wltc, ymax, (20.0, "Still falling at<br>the grid edge"), pal,
        eu_feasible=eu_wltc_feas, fr_feasible=fr_wltc_feas,
    ),
    width="stretch", theme=None,
)
left.caption(_selection_caption(phev_wltc_sel, eu_wltc))
right.markdown("**One Francorchamps sport lap: past 6 kWh, a battery is only mass**")
right.plotly_chart(
    phev_lines(
        eu_sport, fr_sport, ymax, (6.0, "Enough for<br>the whole lap"), pal,
        eu_feasible=eu_sport_feas, fr_feasible=fr_sport_feas,
    ),
    width="stretch", theme=None,
)
right.caption(_selection_caption(phev_sport_sel, eu_sport))

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
