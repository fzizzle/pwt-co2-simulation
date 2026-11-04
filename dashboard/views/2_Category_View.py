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
    X_LABELS,
    configure,
    download,
    mark_gap_value,
    render_run_notices,
    run_label,
    run_notice,
    varying_parameters,
)
from dashboard.labels import column as column_label
from dashboard.labels import number
from dashboard.loaders import axis_columns, load_runs, numeric_trace_columns, trace_for
from dashboard.theme import POWERTRAIN_ORDER, style_axes
from dashboard.track_charts import is_lap, lap_section, mark_corners
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
        record[f"{display} ({unit})"] = mark_gap_value(
            row.get(column), row["powertrain"], row["cycle"]
        )
    record["Workbook"] = row["source_file"]
    records.append(record)
figures = pd.DataFrame(records)

st.dataframe(
    figures, width="stretch", hide_index=True, height=len(figures) * 35 + 38
)
st.caption(
    "A dash means that workbook does not report the figure; “electricity not counted” marks "
    "a run whose figure leaves out its battery energy. Values are as reported — nothing here "
    "is converted or recomputed."
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

all_traces = [trace_for(row["powertrain"], row["cycle"]) for _, row in members.iterrows()]

# A lap and NEDC share only time and step, and against time the three cycles read as noise.
# So a category with two or more laps opens on the laps alone, against distance.
lap_members = [name for name, c in zip(member_names, members["cycle"]) if is_lap(c)]
overlaid = st.multiselect(
    "Runs to overlay", member_names,
    default=lap_members if len(lap_members) >= 2 else member_names,
    key=f"category_overlay_{choice}",
)
keep = [i for i, name in enumerate(member_names) if name in overlaid]
traces = [all_traces[i] for i in keep]
overlay_names = [member_names[i] for i in keep]
overlay_colours = [member_colours[i] for i in keep]
overlay_cycles = {members["cycle"].iloc[i] for i in keep}

if not traces:
    st.caption("Pick at least one run to overlay.")
    plottable = []
else:
    shared_axes = set.intersection(*(set(axis_columns(t)) for t in traces))
    axis_options = [c for c in ("distance_m", "time_s", "step") if c in shared_axes]
    shared_columns = sorted(set.intersection(*(set(numeric_trace_columns(t)) for t in traces)))
    plottable = [c for c in shared_columns if c not in ("step",)]

if traces and not plottable:
    st.caption("These runs share no per-step column, so there is nothing to overlay.")
elif plottable:
    picker, axis_picker = st.columns([3, 1])
    with picker:
        default = next((i for i, c in enumerate(plottable) if c == "speed_kph"), 0)
        column = st.selectbox("Column", options=plottable, index=default,
                              format_func=column_label)
    with axis_picker:
        x_column = st.selectbox("Against", options=axis_options, format_func=lambda c: X_LABELS[c])

    if x_column == "step":
        traces = [t.assign(step=range(len(t))) for t in traces]

    # In a powertrain category every member is the same technology and so the same colour;
    # dash separates them without breaking the rule that colour belongs to the powertrain.
    member_dashes = (
        [charts.DASH_CYCLE[i % len(charts.DASH_CYCLE)] for i in keep]
        if field == "powertrain"
        else None
    )

    fig = charts.overlay_traces(
        traces, overlay_names, overlay_colours, column, x_column, pal, dashes=member_dashes
    )
    style_axes(fig, pal, x_title=X_LABELS[x_column], y_title=column_label(column))
    fig.update_layout(height=420)
    # Eco and sport reach a corner at different times, so only distance suits both.
    if all(is_lap(c) for c in overlay_cycles) and (
        x_column == "distance_m" or len(overlay_cycles) == 1
    ):
        mark_corners(fig, traces[0], x_column, pal)
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
    if x_column == "distance_m" and not all(is_lap(c) for c in overlay_cycles):
        st.caption(
            "These runs are on different cycles, so the x-axes cover different ground: the "
            "Francorchamps lap is 7 km, NEDC about 11 km."
        )

laps = {name: trace for name, trace, cycle in zip(member_names, all_traces, members["cycle"])
        if is_lap(cycle)}
if laps:
    st.subheader("On the circuit")
    lap_section(laps, "category", pal)

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
    run_columns = [c for c in varying.columns if c not in ("Parameter", "Distinct values")]
    st.dataframe(
        varying.style.format({c: number for c in run_columns}, na_rep="—"),
        width="stretch",
        hide_index=True,
        height=min(len(varying), 18) * 35 + 38,
    )
    st.caption(
        f"{len(varying)} parameters differ across the category, or are absent from some of its "
        "workbooks — a dash means that workbook has no row for it at all. Most-varied first."
    )
    download(varying, f"pwt-category-{choice}-parameters.csv", "Download these parameters as CSV")
