"""Model — what the Python model computes, beside what the workbooks report.

Unlike every other page, nothing here is read from a spreadsheet: it is `pwt.model`, which
reproduces the workbooks exactly in its "exact" scenario and then changes them one tested step
at a time. The findings behind each scenario are in `docs/phase-2-results.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import charts
from dashboard.labels import readable
from dashboard.layout import X_LABELS, configure, download, show_chart
from dashboard.theme import POWERTRAIN_ORDER, Palette, style_axes
from dashboard.track_charts import is_lap, lap_section, mark_corners
from pwt.catalog import POWERTRAIN_NAMES
from pwt.checkpoint import CYCLE_LABELS, CYCLE_ORDER
from pwt.model import fleet
from pwt.model.profile import generate
from pwt.phase2 import (
    ASSIGNMENT_VEHICLES,
    GENERATED,
    SCENARIOS,
    generated_laps,
    powertrain_cells,
    result_for,
    scenario_cells,
    side_by_side,
)

pal = configure("Model")

#: Numbered because each scenario builds on the one before it.
SCENARIO_LABELS = {
    "exact": "1 · Workbook vehicles, 250 g/kWh grid",
    "harmonised": "2 · One convention",
    "stage B": "3 · Better hybrid control",
    "assignment": "4 · Assignment vehicles",
    "storage losses": "5 · With storage losses",
}
SCENARIO_NOTES = {
    "exact": "Each workbook's vehicle and formulas reproduced exactly, with electricity counted "
             "at 250 g/kWh. Petrol and full hybrid match Overview; the electric cars do not "
             "(see above).",
    "harmonised": "The same vehicles on one convention, with cited constants and a 90 % "
                  "charger.",
    "stage B": "Harmonised; hybrid engine efficiency read at the engine's share; the full "
               "hybrid holds its battery in a 50–70 % band.",
    "assignment": "Stage B with the assignment sheet's vehicles instead of the workbooks'.",
    "storage losses": "Assignment, with 85 % one way through the hybrids' motor, inverter "
                      "and battery.",
}
SMALL_CHARTS = {"gear": "Gear", "batt_soc": "Battery charge",
                "engine_power_drivetrain_w": "Power demand"}
CYCLE_CHOICES = {**CYCLE_LABELS, "franco_eco_generated": "Francorchamps — eco, generated",
                 "franco_sport_generated": "Francorchamps — sport, generated"}


def _format_shortfall(short_steps: int | None, short_kw: float | None) -> str:
    if short_steps is None:
        return "unchecked"
    if short_steps == 0:
        return "pass"
    unit = "step" if short_steps == 1 else "steps"
    return f"{short_steps} {unit}, ≤ {short_kw:.1f} kW"


def _scenario_bars(long_frame: pd.DataFrame, scenario: str, pal: Palette) -> go.Figure:
    """Grouped CO2 bars for one scenario using the deck convention for infeasible runs."""
    fig = go.Figure()
    own = long_frame[long_frame["scenario"] == scenario]
    cycle_labels = [CYCLE_LABELS[c] for c in CYCLE_ORDER]
    ymax = max(float(own["co2_g_km"].max()) * 1.18, 10.0)

    for powertrain in POWERTRAIN_ORDER:
        colour = pal.for_powertrain(powertrain)
        sub = own[own["powertrain_key"] == powertrain].set_index("cycle_key")
        ys, texts, fill_colours, line_widths, custom = [], [], [], [], []
        for cycle in CYCLE_ORDER:
            row = sub.loc[cycle]
            co2 = float(row["co2_g_km"])
            checked = bool(row["checked"])
            steps = None if pd.isna(row["short_steps"]) else int(row["short_steps"])
            kw = None if pd.isna(row["short_kw"]) else float(row["short_kw"])
            hollow = checked and (steps or 0) > 0
            ys.append(co2)
            texts.append(f"{co2:.1f}*" if hollow else f"{co2:.1f}")
            fill_colours.append("rgba(0,0,0,0)" if hollow else colour)
            line_widths.append(2.5 if hollow else 0)
            if not checked:
                detail = "Engine check: unchecked"
            elif hollow:
                unit = "step" if steps == 1 else "steps"
                detail = f"Provisional: engine short on {steps} {unit}, worst {kw:.1f} kW"
            else:
                detail = "Engine check: pass (0 short steps)"
            custom.append([detail])

        fig.add_trace(go.Bar(
            x=cycle_labels,
            y=ys,
            name=POWERTRAIN_NAMES[powertrain],
            text=texts,
            textposition="outside",
            textfont=dict(color=pal.text_primary, size=11),
            cliponaxis=False,
            marker=dict(
                color=fill_colours,
                line=dict(color=[colour] * len(CYCLE_ORDER), width=line_widths),
            ),
            customdata=custom,
            hovertemplate=(
                f"{POWERTRAIN_NAMES[powertrain]} · %{{x}}<br>"
                "%{y:.1f} g CO₂/km<br>%{customdata[0]}<extra></extra>"
            ),
        ))

    style_axes(fig, pal, y_title="g CO₂/km")
    fig.update_yaxes(range=[0, ymax])
    fig.update_xaxes(showgrid=False)
    fig.update_layout(height=380, barmode="group", bargap=0.22, bargroupgap=0.08)
    return fig


@st.cache_data(show_spinner="Running the model…")
def comparison() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    results = {scenario: scenario_cells(scenario) for scenario in SCENARIOS}
    summary = {scenario: cells_ for scenario, (cells_, _) in results.items()}
    co2_table = side_by_side(summary).reset_index()

    feas_rows = []
    long_rows = []
    for powertrain, p_name in POWERTRAIN_NAMES.items():
        for cycle in CYCLE_ORDER:
            c_name = CYCLE_LABELS[cycle]
            feas_row = {"powertrain": p_name, "cycle": c_name}
            for scenario in SCENARIOS:
                cells_, shortfall = results[scenario]
                cell = next(
                    c for c in cells_
                    if (c.powertrain, c.cycle, c.variant) == (powertrain, cycle, "")
                )
                if not shortfall:
                    checked = False
                    short_steps, short_kw = None, None
                else:
                    checked = True
                    short_steps, short_kw = shortfall[(powertrain, cycle)]
                status = _format_shortfall(short_steps, short_kw)
                feas_row[scenario] = status
                long_rows.append({
                    "powertrain_key": powertrain,
                    "powertrain": p_name,
                    "cycle_key": cycle,
                    "cycle": c_name,
                    "scenario": scenario,
                    "co2_g_km": float(cell.co2_eu_grid),
                    "checked": checked,
                    "short_steps": short_steps,
                    "short_kw": short_kw,
                    "status": status,
                })
            feas_rows.append(feas_row)
    return co2_table, pd.DataFrame(feas_rows), pd.DataFrame(long_rows)


@st.cache_data(show_spinner="Generating the laps…")
def laps() -> pd.DataFrame:
    return generated_laps().reset_index(names="lap")


@st.cache_data(show_spinner="Running the model…")
def steps(
    powertrain: str, cycle: str, scenario: str
) -> tuple[pd.DataFrame, dict, tuple[int, float] | None]:
    result = result_for(powertrain, cycle, scenario)
    headline = {k: (None if v is None else float(v)) for k, v in result.headline.items()}
    if cycle in GENERATED:
        effective = scenario if scenario in ASSIGNMENT_VEHICLES else "assignment"
        vehicle = {
            "petrol": fleet.petrol,
            "bev": fleet.electric,
            "hybrid": lambda: fleet.hybrid(1.0),
            "phev": lambda: fleet.plugin(0.98),
        }[powertrain]()
        cyc = generate(GENERATED[cycle], fleet.petrol())
        _, shortfall = powertrain_cells(powertrain, cycle, vehicle, cyc, effective)
        return result.steps, headline, shortfall
    return result.steps, headline, None


st.title("Model")
st.markdown(
    "What the Python model computes. Its **exact** scenario reproduces every workbook to "
    "about 1e-15; the others change one thing at a time. CO₂ counts electricity at 250 g/kWh "
    "for every powertrain, so the four compare on one footing."
)

# --- the scenarios --------------------------------------------------------------------------

st.subheader("How much CO₂ does each car emit?")
st.caption("g CO₂/km. Each column builds on the one before it.")
st.caption(
    "Why column 1 differs from Overview for the electric cars: the workbooks count grid "
    "electricity at 220 g/kWh (electric car, laps) or 440 g/kWh (electric car, NEDC), and not "
    "at all for the plug-in hybrid. Here every kWh counts at 250 g/kWh, and the plug-in "
    "hybrid's NEDC and WLTC rows weight its charge-depleting and charge-sustaining runs."
)
co2_table, feas_table, long_frame = comparison()
table = co2_table.rename(columns=SCENARIO_LABELS)
st.dataframe(table, width="stretch", hide_index=True, height=len(table) * 35 + 38)
download(table, "pwt-model-scenarios.csv")

bar_scenario = st.selectbox(
    "Scenario chart",
    list(SCENARIOS),
    index=len(SCENARIOS) - 1,
    format_func=SCENARIO_LABELS.get,
    key="model_bar_scenario",
)
show_chart(_scenario_bars(long_frame, bar_scenario, pal))
if bar_scenario == "exact":
    st.caption("g CO₂/km, EU grid 250 g/kWh · Engine check: unchecked for this scenario.")
else:
    st.caption("g CO₂/km, EU grid 250 g/kWh · * outlined: engine short of the trace on some steps")

st.markdown("**Engine capability check (short steps and worst shortfall)**")
feas_display = feas_table.rename(columns=SCENARIO_LABELS)
st.dataframe(feas_display, width="stretch", hide_index=True, height=len(feas_display) * 35 + 38)
download(feas_display, "pwt-model-feasibility.csv")
st.caption(
    "Steps where demand exceeds the 74 kW full-load curve and worst shortfall in kW. "
    "Scenarios without an engine check are labelled unchecked."
)

with st.expander("What each column changes"):
    for scenario, note in SCENARIO_NOTES.items():
        st.markdown(f"- **{SCENARIO_LABELS[scenario]}** — {note}")

# --- one drive ------------------------------------------------------------------------------

st.subheader("What happens along the drive?")
left, middle, right = st.columns(3)
powertrain = left.selectbox("Powertrain", list(POWERTRAIN_NAMES),
                            format_func=POWERTRAIN_NAMES.get, key="model_powertrain")
drives = list(CYCLE_ORDER) + list(GENERATED)
cycle = middle.selectbox("Drive", drives, index=drives.index("franco_sport_generated"),
                         format_func=CYCLE_CHOICES.get, key="model_cycle")
scenario = right.selectbox("Scenario", list(SCENARIOS), index=2, key="model_scenario",
                           format_func=SCENARIO_LABELS.get, disabled=cycle in GENERATED)
if cycle in GENERATED:
    st.caption("A generated lap has no workbook, so it only exists with the assignment vehicles.")
if powertrain == "phev" and cycle in ("nedc", "wltc"):
    st.caption("The plug-in hybrid's charge-depleting run (from 98 %); the scenario table "
               "weights it with the charge-sustaining run.")

trace, headline, gen_shortfall = steps(powertrain, cycle, scenario)
fuel, battery, co2 = (headline[k] for k in ("fuel_l_100km", "battery_kwh_100km", "co2_g_km"))
# Only the figures this car has: a petrol car draws nothing from a battery, an electric car
# burns no fuel.
tiles = [(label, text) for label, text in (
    ("Fuel", None if fuel is None or fuel == 0 else f"{fuel:.2f} l/100 km"),
    ("From the battery", None if battery is None or battery == 0
     else f"{battery:.1f} kWh/100 km"),
    ("CO₂ (fuel, or grid for the electric car)", f"{co2:.1f} g/km"),
) if text is not None]
for slot, (label, text) in zip(st.columns(len(tiles)), tiles):
    slot.metric(label, text)

if cycle in GENERATED:
    drive_shortfall = gen_shortfall
elif scenario == "exact":
    drive_shortfall = None
else:
    match = long_frame[
        (long_frame["powertrain_key"] == powertrain)
        & (long_frame["cycle_key"] == cycle)
        & (long_frame["scenario"] == scenario)
    ].iloc[0]
    drive_shortfall = (
        None
        if not match["checked"]
        else (int(match["short_steps"]), float(match["short_kw"]))
    )

if drive_shortfall is None:
    st.caption("Engine check: unchecked for the exact workbook scenario.")
elif drive_shortfall[0] > 0:
    short_steps, short_kw = drive_shortfall
    unit = "step" if short_steps == 1 else "steps"
    suffix = " (charge-sustaining run)" if powertrain == "phev" and cycle in ("nedc", "wltc") else ""
    st.warning(
        f"Provisional — engine short of the trace on {short_steps} {unit}, "
        f"worst shortfall {short_kw:.1f} kW{suffix}.",
        icon="⚠️",
    )
else:
    st.caption("Engine check: pass (0 short steps).")

on_lap = is_lap(cycle)
if on_lap:
    lap_section({CYCLE_CHOICES[cycle]: trace}, "model", pal, source="model",
                colour=pal.for_powertrain(powertrain))
else:
    st.caption("This is a test cycle, not a circuit, so it has no track map. Pick a "
               "Francorchamps drive to see one.")

x_column = "distance_m" if on_lap else "time_s"
st.markdown("**Speed and elevation**")
fig = charts.speed_and_altitude(trace, x_column, pal, colour=pal.for_powertrain(powertrain))
style_axes(fig, pal, x_title=X_LABELS[x_column])
fig.update_layout(height=420)
if on_lap:
    mark_corners(fig, trace, x_column, pal)
show_chart(fig)

plots = [c for c in SMALL_CHARTS if c in trace.columns]
cols = st.columns(len(plots))
for column, slot in zip(plots, cols):
    with slot:
        st.markdown(f"**{SMALL_CHARTS[column]}**")
        fig = (charts.gear_steps(trace, x_column, pal, colour=pal.for_powertrain(powertrain)) if column == "gear"
               else charts.trace_lines(trace, [column], x_column, pal))
        style_axes(fig, pal, x_title=X_LABELS[x_column],
                   y_title="" if column == "gear" else
                   {"batt_soc": "fraction", "engine_power_drivetrain_w": "W"}[column])
        fig.update_layout(height=300)
        if on_lap:
            mark_corners(fig, trace, x_column, pal, labels=False)
        show_chart(fig)

with st.expander("How the generated laps are built"):
    st.markdown(
        "Corner speeds from the templates as boundary conditions; eco accelerates at 0–100 km/h "
        "in 20 s (capped at 90 km/h and at what the engine gives) and brakes at 0.4 g; sport "
        "accelerates as hard as the 74 kW engine can and brakes at 0.6 g. The petrol car can "
        "drive both on every step, unlike the supplied laps."
    )
    if st.toggle("Show generated lap comparison table", key="model_show_laps"):
        lap_table = laps()
        st.dataframe(readable(lap_table), width="stretch", hide_index=True)
        download(lap_table, "pwt-model-generated-laps.csv")

with st.expander(f"All {len(trace)} steps, as a table"):
    st.dataframe(readable(trace), width="stretch", hide_index=True)
    download(trace, f"model-{powertrain}-{cycle}-{scenario}.csv".replace(" ", "-"))
