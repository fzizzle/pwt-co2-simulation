"""Data — the datasets behind the other pages, as plain tables.

A table viewer and nothing else: no charts, no aggregation. The other pages cover comparison;
this is where you come to see everything at once, or to check what a cell actually holds.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.layout import (
    configure,
    download,
    render_run_notices,
    run_label,
    sidebar_filters,
)
from dashboard.labels import column as column_label
from dashboard.labels import number, parameter, readable, sheet_label, unit
from dashboard.loaders import (
    load_block,
    load_runs,
    load_traces,
    params_long,
    totals_long,
)
from pwt.catalog import CATALOG, CYCLE_NAMES, POWERTRAIN_NAMES

pal = configure("Data")
runs = load_runs()

st.title("Data")
st.markdown(
    "Every dataset behind the other pages. Values are as the workbooks report them — the only "
    "changes are structural: columns renamed to stable names, and rows keyed by label and unit."
)

DATASETS = {
    "Runs": "One row per run, with every total and parameter widened into columns.",
    "Totals": "Every reported total, one row each.",
    "Parameters": "Every input, one row each.",
    "Traces": "Every step of every run, stacked.",
    "Workbook cells": (
        "One workbook's labelled block exactly as the sheet holds it — original label and "
        "unit text, the row number, and how the reader classified it."
    ),
}

choice = st.radio(
    "Dataset", options=list(DATASETS), horizontal=True, label_visibility="collapsed"
)
st.caption(DATASETS[choice])

powertrains, cycles = sidebar_filters(runs)
render_run_notices(
    *(row for _, row in runs[runs["powertrain"].isin(powertrains)
      & runs["cycle"].isin(cycles)].iterrows())
)


def apply_filters(frame: pd.DataFrame) -> pd.DataFrame:
    """Restrict to the sidebar selection, for any frame carrying powertrain and cycle."""
    if "powertrain" not in frame.columns:
        return frame
    return frame[frame["powertrain"].isin(powertrains) & frame["cycle"].isin(cycles)]


def with_display_names(frame: pd.DataFrame) -> pd.DataFrame:
    """Show the names used everywhere else, not the internal codes. Values are untouched."""
    out = frame.copy()
    if "quantity" in out.columns:
        out["quantity"] = out["quantity"].map(sheet_label)
    if "parameter" in out.columns:
        out["parameter"] = out["parameter"].map(parameter)
    if "unit" in out.columns:
        out["unit"] = out["unit"].map(unit)
    if "powertrain" in out.columns:
        out["powertrain"] = out["powertrain"].map(POWERTRAIN_NAMES).fillna(out["powertrain"])
    if "cycle" in out.columns:
        out["cycle"] = out["cycle"].map(CYCLE_NAMES).fillna(out["cycle"])
    return out


def column_picker(frame: pd.DataFrame, *, keep: list[str], key: str) -> pd.DataFrame:
    """Let the reader narrow a wide table; identity columns are always kept."""
    optional = [c for c in frame.columns if c not in keep]
    if len(optional) <= 8:
        return frame
    chosen = st.multiselect(
        f"Columns ({len(optional)} available)",
        options=optional,
        default=optional[: min(8, len(optional))],
        key=key,
        format_func=column_label,
        help="Identity columns are always shown.",
    )
    return frame[keep + chosen]


# --- build the selected table -----------------------------------------------------------------

if choice == "Workbook cells":
    entry = st.selectbox(
        "Workbook",
        options=[e.filename for e in CATALOG],
        format_func=lambda f: next(
            f"{run_label(e.powertrain, e.cycle)} — {e.filename}"
            for e in CATALOG
            if e.filename == f
        ),
    )
    table = load_block(entry)
    st.caption(f"Source: `{entry}`")
else:
    if choice == "Runs":
        table = column_picker(
            with_display_names(apply_filters(runs)),
            keep=["powertrain", "cycle", "source_file"],
            key="runs_cols",
        )
    elif choice == "Totals":
        table = with_display_names(apply_filters(totals_long(runs)))
    elif choice == "Parameters":
        table = with_display_names(apply_filters(params_long(runs)))
    else:  # Traces
        table = column_picker(
            with_display_names(apply_filters(load_traces())),
            keep=["powertrain", "cycle", "step"],
            key="trace_cols",
        )

if table.empty:
    st.info("Nothing matches the current filters. Widen the selection in the sidebar.")
    st.stop()

st.caption(f"{len(table):,} rows × {len(table.columns)} columns. Click a header to sort.")
# Size the table to its contents up to a cap, so a short dataset is fully visible rather than
# scrolling inside a widget that is mostly empty space.
ROW_PX, HEADER_PX, MAX_ROWS = 35, 38, 22
# The workbook block is the rawest view, so its numbers keep every digit.
exact = choice == "Workbook cells"
st.dataframe(
    readable(table, (lambda v: f"{v:.12g}") if exact else number),
    width="stretch",
    hide_index=True,
    height=min(len(table), MAX_ROWS) * ROW_PX + HEADER_PX,
)
download(table.rename(columns=column_label), f"pwt-{choice.lower().replace(' ', '-')}.csv",
         "Download these rows as CSV")
st.caption("The download contains exactly the rows and columns shown above.")
