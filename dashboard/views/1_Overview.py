"""Overview — every supplied run in one table and one chart.

Opened from `dashboard/Overview.py` under "The workbooks".
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit puts the script's own directory on sys.path, not the repo root, so neither `pwt`
# nor `dashboard` is importable without this.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard import charts
from dashboard.layout import (
    CANONICAL_QUANTITIES,
    CYCLE_DEFINITIONS,
    configure,
    data_notes,
    download,
    elevation_strip,
    mark_gap_value,
    measure_picker,
    render_run_notices,
    run_label,
    run_notice,
    sidebar_filters,
)
from dashboard.labels import figure, readable
from dashboard.theme import POWERTRAIN_ORDER, style_axes
from dashboard.loaders import load_runs, trace_for
from dashboard.track_charts import lap_section
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

pal = configure("Overview")
runs = load_runs()

# --- header ---------------------------------------------------------------------------------

st.title("Workbook overview")
st.markdown("Reported results for four powertrains on three cycles.")

# --- controls -------------------------------------------------------------------------------

powertrains, cycles = sidebar_filters(runs, key_prefix="overview")
quantity = measure_picker(st.sidebar, key="wb_measure_overview", widget="radio")
display_name, unit = CANONICAL_QUANTITIES[quantity]

selected = runs[runs["powertrain"].isin(powertrains) & runs["cycle"].isin(cycles)]
if selected.empty:
    st.info("Select at least one powertrain and one driving cycle.")
    st.stop()

# --- the matrix -----------------------------------------------------------------------------

st.subheader(f"{display_name} ({unit})")
st.caption("A dash marks a figure the workbook does not report.")

render_run_notices(*(row for _, row in selected.iterrows()))

matrix = (
    selected.pivot(index="powertrain", columns="cycle", values=quantity)
    .reindex(index=[p for p in POWERTRAIN_ORDER if p in powertrains])
    .reindex(columns=[c for c in CYCLE_NAMES if c in cycles])
    .rename(index=POWERTRAIN_NAMES, columns=CYCLE_NAMES)
    .rename_axis(index="Powertrain", columns=None)
)
# No cell gradient here: it would pull in matplotlib as a runtime dependency, and the
# grouped bar below already carries the magnitude comparison.
display = matrix.copy().astype(object)
for powertrain in matrix.index:
    for cycle in matrix.columns:
        code_p = next(k for k, v in POWERTRAIN_NAMES.items() if v == powertrain)
        code_c = next(k for k, v in CYCLE_NAMES.items() if v == cycle)
        display.loc[powertrain, cycle] = mark_gap_value(
            matrix.loc[powertrain, cycle], code_p, code_c
        )
st.dataframe(display, width="stretch")

# --- the chart ------------------------------------------------------------------------------

gaps = {
    (row["powertrain"], row["cycle"])
    for _, row in selected.iterrows()
    if run_notice(row["powertrain"], row["cycle"])
}
fig = charts.grouped_totals(selected, quantity, pal, unit=unit, gaps=gaps, show_footnote=False)
style_axes(fig, pal, y_title=f"{display_name} ({unit})")
fig.update_layout(height=420, margin=dict(t=28, b=12))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme=None)
if gaps:
    st.caption(f"{charts.GAP_MARKER} {charts.GAP_LABEL}.")

# --- what the cells contain -----------------------------------------------------------------

notes = data_notes(selected)
if notes:
    with st.expander(f"Zero and negative figures ({len(notes)})", expanded=True):
        for note in notes:
            st.markdown(f"- {note}")

# --- elevation and cycle context ------------------------------------------------------------

lap = trace_for("petrol", "franco_eco")
eco_label = run_label("petrol", "franco_eco")
strip = elevation_strip(lap, pal)
if strip is not None:
    st.plotly_chart(strip, width="stretch", config={"displayModeBar": False}, theme=None)
    st.caption(f"Altitude from the {eco_label} workbook.")
    with st.expander("Circuit map"):
        lap_section({eco_label: lap}, "overview", pal, paint="Altitude")

with st.expander("Driving cycles"):
    for code, definition in CYCLE_DEFINITIONS.items():
        st.markdown(f"### {CYCLE_NAMES[code]}\n{definition}")

# --- the table ------------------------------------------------------------------------------

with st.expander("Reported figures"):
    columns = ["powertrain", "cycle", "source_file", "steps", *CANONICAL_QUANTITIES]
    table = selected[columns].copy()
    table["powertrain"] = table["powertrain"].map(POWERTRAIN_NAMES)
    table["cycle"] = table["cycle"].map(CYCLE_NAMES)
    table = table.rename(
        columns={
            "powertrain": "Powertrain",
            "cycle": "Driving cycle",
            "source_file": "Workbook",
            "steps": "Steps",
            **{k: f"{v[0]} ({v[1]})" for k, v in CANONICAL_QUANTITIES.items()},
        }
    )
    st.dataframe(readable(table, figure), width="stretch", hide_index=True)
    download(table, "pwt-runs.csv", "Download reported figures (CSV)")
