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
st.markdown("Tables from the supplied workbooks.")

DATASETS = {
    "Runs": "One row per run.",
    "Totals": "One row per reported total.",
    "Parameters": "One row per reported parameter.",
    "Traces": "One row per trace step.",
    "Workbook cells": "Workbook row numbers, labels and units, with reader matches.",
}

choice = st.radio(
    "Dataset", options=list(DATASETS), horizontal=True, label_visibility="collapsed"
)
st.caption(DATASETS[choice])

powertrains: list[str] = []
cycles: list[str] = []
if choice != "Workbook cells":
    powertrains, cycles = sidebar_filters(runs, key_prefix="data")
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
    """Let the reader narrow a wide table; fixed identity columns are always kept."""
    optional = [c for c in frame.columns if c not in keep]
    if len(optional) <= 8:
        return frame
    fixed_names = ", ".join(column_label(c, with_unit=False) for c in keep)
    chosen = st.multiselect(
        "Columns",
        options=optional,
        default=optional[: min(8, len(optional))],
        key=key,
        format_func=column_label,
        help=f"Always shown: {fixed_names}.",
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
    selected_run = runs[runs["source_file"] == entry]
    render_run_notices(*(row for _, row in selected_run.iterrows()))
    table = load_block(entry)
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
    st.info("No rows match the selected filters.")
    st.stop()

st.caption(f"{len(table):,} rows × {len(table.columns)} columns.")
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
         "Download table (CSV)")
