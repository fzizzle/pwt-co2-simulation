"""Trace Explorer — the per-step data for one run, instead of scrolling a spreadsheet."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard import charts
from dashboard.layout import configure, download, run_picker, source_caption
from dashboard.loaders import load_runs, numeric_trace_columns, trace_for
from dashboard.theme import style_axes

pal = configure("Trace Explorer")
runs = load_runs()

st.title("Trace Explorer")
st.markdown(
    "Every step of one run. The Francorchamps laps are 32 variable-length segments; the NEDC "
    "runs are around 105 steps. Hover any chart for exact values."
)

# --- controls -------------------------------------------------------------------------------

st.sidebar.subheader("Run")
row = run_picker(runs, "Run to explore", key="trace_run", index=0)
trace = trace_for(row["powertrain"], row["cycle"])

if trace.empty:
    st.warning("This workbook has no per-step data.")
    st.stop()

available = numeric_trace_columns(trace)
x_options = [c for c in ("distance_m", "time_s", "step") if c in trace.columns or c == "step"]
st.sidebar.subheader("Axis")
X_LABELS = {"distance_m": "Distance (m)", "time_s": "Time (s)", "step": "Step"}
x_column = st.sidebar.selectbox(
    "Plot against", options=x_options, format_func=lambda c: X_LABELS[c]
)
x_label = X_LABELS[x_column]
if x_column == "step":
    trace = trace.assign(step=range(len(trace)))

source_caption(row)

# --- the three standing views ---------------------------------------------------------------

st.subheader("Speed and elevation")
fig = charts.speed_and_altitude(trace, x_column, pal)
style_axes(fig, pal, x_title=x_label)
fig.update_layout(height=420)
st.plotly_chart(fig, width="stretch", theme=None)

left, right = st.columns(2)

with left:
    if "gear" in trace.columns and trace["gear"].notna().any():
        st.subheader("Gear")
        fig = charts.gear_steps(trace, x_column, pal)
        style_axes(fig, pal, x_title=x_label, y_title="Gear")
        fig.update_layout(height=300)
        st.plotly_chart(fig, width="stretch", theme=None)
    else:
        st.subheader("Gear")
        st.caption(
            "This workbook has no gear column — the electric runs use a single reduction ratio."
        )

with right:
    st.subheader("Forces")
    fig = charts.force_breakdown(trace, x_column, pal)
    style_axes(fig, pal, x_title=x_label, y_title="Force (N)")
    fig.update_layout(height=300)
    st.plotly_chart(fig, width="stretch", theme=None)
    st.caption(
        "Overlaid rather than stacked: both components are signed in the supplied data — "
        "acceleration force goes negative under braking, resistive force downhill."
    )

# --- free-form column picker ----------------------------------------------------------------

st.subheader("Any column")
default = [c for c in ("engine_power_w",) if c in available] or available[:1]
columns = st.multiselect(
    "Columns to plot", options=available, default=default, label_visibility="collapsed"
)
if columns:
    fig = charts.trace_lines(trace, columns, x_column, pal)
    style_axes(fig, pal, x_title=x_label)
    fig.update_layout(height=380)
    st.plotly_chart(fig, width="stretch", theme=None)
    if len(columns) > 1:
        st.caption(
            "One shared y-axis. Columns of very different magnitude are easier to read one at "
            "a time than on two scales."
        )
else:
    st.caption("Pick one or more columns to plot.")

# --- the table ------------------------------------------------------------------------------

with st.expander(f"All {len(trace)} steps, as a table"):
    st.dataframe(trace, width="stretch", hide_index=True)
    download(trace, f"trace-{row['powertrain']}-{row['cycle']}.csv")
