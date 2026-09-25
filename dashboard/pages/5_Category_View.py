"""Category view — every run in one category together.

A category is a slice of the 4x3 grid along one field: all four powertrains on one cycle, or
one powertrain across all three cycles. Driving style is not a third axis — it maps 1:1 onto
cycle today (eco/sport/regulatory to the two Francorchamps laps and NEDC), so "all the sport"
is the Francorchamps sport category.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard import charts
from dashboard.layout import (
    CANONICAL_QUANTITIES,
    configure,
    download,
    render_run_notices,
    run_label,
    run_notice,
    varying_parameters,
)
from dashboard.loaders import axis_columns, load_runs, numeric_trace_columns, trace_for
from dashboard.theme import POWERTRAIN_ORDER, style_axes
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

pal = configure("Category view")
runs = load_runs()

st.title("Category view")
st.markdown(
    "Every run in one category, side by side. Choose powertrain to see one technology across "
    "the cycles, or by cycle to see the four technologies on the same drive."
)

# --- pick the category -----------------------------------------------------------------------

CATEGORY_AXES = {
    "Powertrain": ("powertrain", POWERTRAIN_NAMES, list(POWERTRAIN_ORDER)),
    "Cycle": ("cycle", CYCLE_NAMES, list(CYCLE_NAMES)),
}

axis = st.radio(
    "Category", options=list(CATEGORY_AXES), horizontal=True, label_visibility="collapsed"
)
field, names, order = CATEGORY_AXES[axis]
available = [code for code in order if code in set(runs[field])]
choice = st.selectbox(axis, options=available, format_func=lambda c: names[c])

members = runs[runs[field] == choice].copy()
# Order members the way the rest of the app orders runs, so colour and sequence stay stable.
sort_field = "cycle" if field == "powertrain" else "powertrain"
sort_order = list(CYCLE_NAMES) if sort_field == "cycle" else list(POWERTRAIN_ORDER)
members["_sort"] = members[sort_field].map({c: i for i, c in enumerate(sort_order)})
members = members.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

#: Each member's short name: the field that varies within the category.
member_names = [
    (CYCLE_NAMES if sort_field == "cycle" else POWERTRAIN_NAMES)[row[sort_field]]
    for _, row in members.iterrows()
]
#: Colour always follows the powertrain, even when the powertrain is what the category has in
#: common — that keeps a technology the same colour on every page.
member_colours = [pal.for_powertrain(row["powertrain"]) for _, row in members.iterrows()]

st.caption(
    f"{names[choice]} — {len(members)} runs: "
    + " · ".join(f"`{row['source_file']}`" for _, row in members.iterrows())
)

render_run_notices(*(row for _, row in members.iterrows()))

# --- the figures, as a table -------------------------------------------------------------------

st.subheader("Reported figures")

records = []
for name, (_, row) in zip(member_names, members.iterrows()):
    record = {"Run": name}
    for column, (display, unit) in CANONICAL_QUANTITIES.items():
        record[f"{display} ({unit})"] = row.get(column)
    record["Workbook"] = row["source_file"]
    records.append(record)
figures = pd.DataFrame(records)

st.dataframe(
    figures, width="stretch", hide_index=True, height=len(figures) * 35 + 38
)
st.caption(
    "A blank cell means that workbook does not report the figure. Values are as reported — "
    "nothing here is converted or recomputed."
)
download(figures, f"pwt-category-{choice}.csv", "Download these figures as CSV")

# --- one measure, charted ----------------------------------------------------------------------

st.subheader("Compare one measure")
quantity = st.selectbox(
    "Measure",
    options=list(CANONICAL_QUANTITIES),
    format_func=lambda q: CANONICAL_QUANTITIES[q][0],
)
display_name, unit = CANONICAL_QUANTITIES[quantity]

gaps = {
    (row["powertrain"], row["cycle"])
    for _, row in members.iterrows()
    if run_notice(row["powertrain"], row["cycle"])
}
fig = charts.grouped_totals(members, quantity, pal, unit=unit, gaps=gaps)
style_axes(fig, pal, y_title=unit)
fig.update_layout(height=400)
st.plotly_chart(fig, width="stretch", theme=None)

if members[quantity].isna().all():
    st.caption(f"No run in this category reports {display_name.lower()}.")

# --- traces overlaid ---------------------------------------------------------------------------

st.subheader("Traces overlaid")

traces = [trace_for(row["powertrain"], row["cycle"]) for _, row in members.iterrows()]

shared_axes = set.intersection(*(set(axis_columns(t)) for t in traces))
X_LABELS = {"distance_m": "Distance (m)", "time_s": "Time (s)", "step": "Step"}
axis_options = [c for c in ("distance_m", "time_s", "step") if c in shared_axes]

shared_columns = sorted(set.intersection(*(set(numeric_trace_columns(t)) for t in traces)))
plottable = [c for c in shared_columns if c not in ("step",)]

if not plottable:
    st.caption("These runs share no per-step column, so there is nothing to overlay.")
else:
    picker, axis_picker = st.columns([3, 1])
    with picker:
        default = next((i for i, c in enumerate(plottable) if c == "speed_kph"), 0)
        column = st.selectbox("Column", options=plottable, index=default)
    with axis_picker:
        x_column = st.selectbox("Against", options=axis_options, format_func=X_LABELS.get)

    if x_column == "step":
        traces = [t.assign(step=range(len(t))) for t in traces]

    # In a powertrain category every member is the same technology and so the same colour;
    # dash separates them without breaking the rule that colour belongs to the powertrain.
    member_dashes = (
        [charts.DASH_CYCLE[i % len(charts.DASH_CYCLE)] for i in range(len(traces))]
        if field == "powertrain"
        else None
    )

    fig = charts.overlay_traces(
        traces, member_names, member_colours, column, x_column, pal, dashes=member_dashes
    )
    style_axes(fig, pal, x_title=X_LABELS[x_column], y_title=column)
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch", theme=None)

    if member_dashes:
        st.caption(
            "All runs here are the same powertrain and so share its colour; the line pattern "
            "tells the cycles apart."
        )

    if axis_options == ["step"]:
        st.caption(
            "Plotted against step number: these workbooks share no distance or time column "
            "that runs forward across all of them."
        )
    if field == "powertrain":
        st.caption(
            "These runs are on different cycles, so the x-axes cover different ground: the "
            "Francorchamps lap is 7 km, NEDC about 11 km."
        )

# --- what differs ------------------------------------------------------------------------------

st.subheader("Inputs that differ across the category")

varying = varying_parameters(members)
if varying.empty:
    st.caption("Every parameter these workbooks share holds the same value.")
else:
    # Rename the run columns to the short names used above.
    rename = {
        run_label(row["powertrain"], row["cycle"]): name
        for name, (_, row) in zip(member_names, members.iterrows())
    }
    varying = varying.rename(columns=rename)
    st.dataframe(
        varying, width="stretch", hide_index=True,
        height=min(len(varying), 18) * 35 + 38,
    )
    st.caption(
        f"{len(varying)} parameters differ across the category, or appear in only some of its "
        "workbooks. Most-varied first."
    )
    download(varying, f"pwt-category-{choice}-parameters.csv", "Download these parameters as CSV")
