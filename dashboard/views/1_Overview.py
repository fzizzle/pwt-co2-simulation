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
    show_chart,
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

# --- header and controls -------------------------------------------------------------------

st.title("Workbook overview")
st.html('<span class="pwt-badge pwt-badge-wb">Reported figures, as each workbook gives them</span>')

measure_column, filter_column = st.columns([4, 1], vertical_alignment="bottom")
quantity = measure_picker(measure_column, key="wb_measure_overview", widget="radio",
                          horizontal=True)
with filter_column.popover("Filter runs", width="stretch"):
    powertrains, cycles = sidebar_filters(runs, key_prefix="overview", container=st)
display_name, unit = CANONICAL_QUANTITIES[quantity]

selected = runs[runs["powertrain"].isin(powertrains) & runs["cycle"].isin(cycles)]
if selected.empty:
    st.info("No run matches the filters. Open “Filter runs” and pick at least one powertrain "
            "and one driving cycle.")
    st.stop()

# --- the chart ------------------------------------------------------------------------------

st.subheader(f"{display_name} ({unit})")
gaps = {
    (row["powertrain"], row["cycle"])
    for _, row in selected.iterrows()
    if run_notice(row["powertrain"], row["cycle"])
}
fig = charts.grouped_totals(selected, quantity, pal, unit=unit, gaps=gaps, show_footnote=False)
style_axes(fig, pal, y_title=f"{display_name} ({unit})")
fig.update_layout(height=420, margin=dict(t=28, b=12))
show_chart(fig)
if gaps:
    st.caption(f"{charts.GAP_MARKER} {charts.GAP_LABEL}.")

render_run_notices(*(row for _, row in selected.iterrows()))

# --- the matrix -----------------------------------------------------------------------------

matrix = (
    selected.pivot(index="powertrain", columns="cycle", values=quantity)
    .reindex(index=[p for p in POWERTRAIN_ORDER if p in powertrains])
    .reindex(columns=[c for c in CYCLE_NAMES if c in cycles])
    .rename(index=POWERTRAIN_NAMES, columns=CYCLE_NAMES)
    .rename_axis(index="Powertrain", columns=None)
)
# No cell gradient here: it would pull in matplotlib as a runtime dependency, and the
# grouped bar above already carries the magnitude comparison.
display = matrix.copy().astype(object)
for powertrain in matrix.index:
    for cycle in matrix.columns:
        code_p = next(k for k, v in POWERTRAIN_NAMES.items() if v == powertrain)
        code_c = next(k for k, v in CYCLE_NAMES.items() if v == cycle)
        display.loc[powertrain, cycle] = mark_gap_value(
            matrix.loc[powertrain, cycle], code_p, code_c
        )
st.dataframe(display, width="stretch")
st.caption("A dash marks a figure the workbook does not report.")

# --- what the cells contain -----------------------------------------------------------------

notes = data_notes(selected)
if notes:
    with st.expander(f"Zero and negative figures ({len(notes)})"):
        for note in notes:
            st.markdown(f"- {note}")

# --- cycle context --------------------------------------------------------------------------

lap = trace_for("petrol", "franco_eco")
eco_label = run_label("petrol", "franco_eco")
with st.expander("Driving cycles"):
    strip = elevation_strip(lap, pal)
    if strip is not None:
        show_chart(strip)
        st.caption(f"Spa-Francorchamps altitude, from the {eco_label} workbook.")
    for code, definition in CYCLE_DEFINITIONS.items():
        st.markdown(f"### {CYCLE_NAMES[code]}\n{definition}")
with st.expander("Circuit map"):
    lap_section({eco_label: lap}, "overview", pal, paint="Altitude")

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
