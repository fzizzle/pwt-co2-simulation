"""Overview — every supplied run in one table and one chart.

Run with: `streamlit run dashboard/Overview.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit puts the script's own directory on sys.path, not the repo root, so neither `pwt`
# nor `dashboard` is importable without this.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard import charts
from dashboard.layout import (
    CANONICAL_QUANTITIES,
    CYCLE_DEFINITIONS,
    configure,
    cycle_facts,
    data_notes,
    download,
    elevation_strip,
    render_run_notices,
    run_notice,
    sidebar_filters,
)
from dashboard.theme import POWERTRAIN_ORDER, style_axes
from dashboard.loaders import load_runs, trace_for
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

pal = configure("Overview")
runs = load_runs()

# --- header ---------------------------------------------------------------------------------

st.title("PWT workbook explorer")
st.markdown(
    "The twelve supplied workbooks — four powertrains over three cycles — read straight from "
    "the spreadsheets. Figures are shown exactly as the workbooks report them: nothing here "
    "converts units, recomputes a result, or fills in a missing value."
)

with st.expander("What the cycles are"):
    for code, definition in CYCLE_DEFINITIONS.items():
        st.markdown(f"### {CYCLE_NAMES[code]}\n{definition}")
        facts = cycle_facts(trace_for("petrol", code))
        if facts:
            st.caption(f"In these files: {facts}.")

lap = trace_for("petrol", "franco_eco")
strip = elevation_strip(lap, pal)
if strip is not None:
    st.plotly_chart(strip, width="stretch", config={"displayModeBar": False}, theme=None)
    st.caption(
        "Spa-Francorchamps elevation over the 7 km lap — the grade term behind every "
        "Francorchamps figure below."
    )

# --- controls -------------------------------------------------------------------------------

powertrains, cycles = sidebar_filters(runs)
st.sidebar.subheader("Measure")
quantity = st.sidebar.radio(
    "Figure to compare",
    options=list(CANONICAL_QUANTITIES),
    format_func=lambda q: CANONICAL_QUANTITIES[q][0],
    label_visibility="collapsed",
)
display_name, unit = CANONICAL_QUANTITIES[quantity]

selected = runs[runs["powertrain"].isin(powertrains) & runs["cycle"].isin(cycles)]
if selected.empty:
    st.info("Pick at least one powertrain and one cycle in the sidebar.")
    st.stop()

# --- the matrix -----------------------------------------------------------------------------

st.subheader(f"{display_name} — every run")
st.caption(
    f"Unit: {unit}. A blank cell means that workbook does not report this figure; a cell "
    "marked “to be filled” is a known gap in the supplied file."
)

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
def mark_gaps(value, powertrain, cycle):
    """Label a known-missing figure instead of letting a bare 0 read as a result."""
    if pd.isna(value):
        return "—"
    if run_notice(powertrain, cycle):
        return f"{value:,.3f} — to be filled"
    return f"{value:,.3f}"


display = matrix.copy().astype(object)
for powertrain in matrix.index:
    for cycle in matrix.columns:
        code_p = next(k for k, v in POWERTRAIN_NAMES.items() if v == powertrain)
        code_c = next(k for k, v in CYCLE_NAMES.items() if v == cycle)
        display.loc[powertrain, cycle] = mark_gaps(
            matrix.loc[powertrain, cycle], code_p, code_c
        )
st.dataframe(display, width="stretch")

# --- the chart ------------------------------------------------------------------------------

gaps = {
    (row["powertrain"], row["cycle"])
    for _, row in selected.iterrows()
    if run_notice(row["powertrain"], row["cycle"])
}
fig = charts.grouped_totals(selected, quantity, pal, unit=unit, gaps=gaps)
style_axes(fig, pal, y_title=unit)
fig.update_layout(height=420)
st.plotly_chart(fig, width="stretch", theme=None)

# --- what the cells contain -----------------------------------------------------------------

notes = data_notes(selected)
if notes:
    with st.expander(f"Values to be aware of ({len(notes)})", expanded=True):
        for note in notes:
            st.markdown(f"- {note}")

# --- the table ------------------------------------------------------------------------------

with st.expander("All reported figures, as a table"):
    columns = ["powertrain", "cycle", "source_file", "steps", *CANONICAL_QUANTITIES]
    table = selected[columns].copy()
    table["powertrain"] = table["powertrain"].map(POWERTRAIN_NAMES)
    table["cycle"] = table["cycle"].map(CYCLE_NAMES)
    table = table.rename(
        columns={
            "powertrain": "Powertrain",
            "cycle": "Cycle",
            "source_file": "Workbook",
            "steps": "Steps",
            **{k: f"{v[0]} ({v[1]})" for k, v in CANONICAL_QUANTITIES.items()},
        }
    )
    st.dataframe(table, width="stretch", hide_index=True)
    download(table, "pwt-runs.csv")
