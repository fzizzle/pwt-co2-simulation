"""Cached access to run data.

Prefers the parquet written by `python -m pwt.build`, and falls back to reading the workbooks
directly when it is absent — so a fresh clone and the deployed app both work with no build
step. Everything is cached per session, so moving a control never re-parses a workbook.
"""

from __future__ import annotations

import importlib
import re

import pandas as pd
import streamlit as st

from pwt import workbook as _workbook

# Streamlit Community Cloud pulls new files on push and re-imports modules inside the app
# folder, but packages outside it — `pwt/` — stay in memory from the moment the process
# booted. A page that calls a function added after boot then raises "ImportError: cannot
# import name …" while that function sits on disk, and only a manual reboot clears it.
# Reloading when an expected name is missing makes the app recover on its own; locally, where
# the module is never stale, this is a no-op.
_REQUIRED = ("read_run", "read_block", "read_all")
if any(not hasattr(_workbook, name) for name in _REQUIRED):
    _workbook = importlib.reload(_workbook)

read_block = _workbook.read_block
read_run = _workbook.read_run

from pwt.build import RUNS_PARQUET, TRACES_PARQUET, runs_frame, traces_frame
from pwt.catalog import CATALOG, CYCLE_NAMES, POWERTRAIN_NAMES, course_file


@st.cache_data(show_spinner="Reading workbooks…")
def load_runs() -> pd.DataFrame:
    """One row per run: identity, canonical figures, every total and parameter."""
    if RUNS_PARQUET.exists():
        return pd.read_parquet(RUNS_PARQUET)
    return runs_frame([read_run(course_file(e.filename)) for e in CATALOG])


@st.cache_data(show_spinner="Reading workbooks…")
def load_traces() -> pd.DataFrame:
    """Every run's steps stacked, tagged with powertrain and cycle."""
    if TRACES_PARQUET.exists():
        return pd.read_parquet(TRACES_PARQUET)
    return traces_frame([read_run(course_file(e.filename)) for e in CATALOG])


@st.cache_data
def trace_for(powertrain: str, cycle: str) -> pd.DataFrame:
    traces = load_traces()
    mask = (traces["powertrain"] == powertrain) & (traces["cycle"] == cycle)
    return traces[mask].drop(columns=["powertrain", "cycle"]).reset_index(drop=True)


def numeric_trace_columns(trace: pd.DataFrame) -> list[str]:
    """Plottable columns, excluding identity and bookkeeping."""
    skip = {"step", "source_file"}
    return [
        c
        for c in trace.columns
        if c not in skip and pd.api.types.is_numeric_dtype(trace[c]) and trace[c].notna().any()
    ]


def axis_columns(trace: pd.DataFrame) -> list[str]:
    """Columns usable as an x-axis, meaning they increase step by step.

    `Distance (m)` is cumulative in the Francorchamps workbooks but per-step in the NEDC ones,
    where it is not monotonic and sums to the 11.2 km lap rather than ending at it. Plotting
    against it there would scramble the chart, so a column only qualifies as an axis when it
    actually runs forward. Nothing is recomputed — an unsuitable column is simply not offered.
    """
    candidates = []
    for column in ("distance_m", "time_s"):
        if column in trace.columns:
            values = trace[column].dropna()
            if len(values) > 1 and values.is_monotonic_increasing and values.iloc[-1] > 0:
                candidates.append(column)
    return candidates + ["step"]


def axis_exclusion_reason(trace: pd.DataFrame, column: str) -> str | None:
    """Why `column` is not offered as an x-axis, or None if it is offered or absent.

    Distance semantics are per-workbook, not per-cycle: the eight Francorchamps files and the
    NEDC hybrid and plug-in hybrid store it cumulatively, `33 NEDC PETROL Car.xlsx` stores it
    per step, and `32 NEDC ELECTRIC.xlsx` has the column but never fills it.
    """
    if column not in trace.columns or column in axis_columns(trace):
        return None
    values = trace[column].dropna()
    if values.empty:
        return f"`{column}` is empty in this workbook, so there is nothing to plot against."
    if not values.is_monotonic_increasing:
        return (
            f"`{column}` is recorded per step in this workbook rather than cumulatively, so it "
            "does not run forward and would scramble the chart."
        )
    return f"`{column}` does not increase across the run, so it cannot be an axis."


def pretty(kind: str, value: str) -> str:
    """Display name for a powertrain or cycle code."""
    table = POWERTRAIN_NAMES if kind == "powertrain" else CYCLE_NAMES
    return table.get(value, value)


#: Flattened column names look like "label [unit]", or just "label" when the workbook gave no
#: unit. Splitting them back out keeps the long views readable as two sortable columns.
_LABEL_UNIT = re.compile(r"^(?P<label>.*?)(?: \[(?P<unit>.*)\])?$")


def _split_label_unit(series: pd.Series) -> pd.DataFrame:
    extracted = series.str.extract(_LABEL_UNIT)
    return extracted.fillna({"unit": ""})


def _long(runs: pd.DataFrame, prefix: str, name: str) -> pd.DataFrame:
    id_cols = ["powertrain", "cycle", "source_file"]
    value_cols = [c for c in runs.columns if c.startswith(f"{prefix}:")]
    long = runs.melt(
        id_vars=id_cols, value_vars=value_cols, var_name=name, value_name="value"
    )
    long[name] = long[name].str.removeprefix(f"{prefix}:")
    parts = _split_label_unit(long[name])
    long[name] = parts["label"]
    long.insert(long.columns.get_loc("value"), "unit", parts["unit"])
    return long.dropna(subset=["value"]).reset_index(drop=True)


def totals_long(runs: pd.DataFrame) -> pd.DataFrame:
    """The `total:` columns reshaped long, dropping figures a run does not report."""
    return _long(runs, "total", "quantity")


def params_long(runs: pd.DataFrame) -> pd.DataFrame:
    """The `param:` columns reshaped long."""
    return _long(runs, "param", "parameter")


@st.cache_data(show_spinner="Reading workbook…")
def load_block(filename: str) -> pd.DataFrame:
    """One workbook's labelled cells exactly as the sheet holds them."""
    return read_block(course_file(filename))
