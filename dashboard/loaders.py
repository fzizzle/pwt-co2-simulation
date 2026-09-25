"""Cached access to run data.

Prefers the parquet written by `python -m pwt.build`, and falls back to reading the workbooks
directly when it is absent — so a fresh clone and the deployed app both work with no build
step. Everything is cached per session, so moving a control never re-parses a workbook.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pwt.build import RUNS_PARQUET, TRACES_PARQUET, runs_frame, traces_frame
from pwt.catalog import CATALOG, CYCLE_NAMES, POWERTRAIN_NAMES, course_file
from pwt.workbook import read_run


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


def pretty(kind: str, value: str) -> str:
    """Display name for a powertrain or cycle code."""
    table = POWERTRAIN_NAMES if kind == "powertrain" else CYCLE_NAMES
    return table.get(value, value)


def totals_long(runs: pd.DataFrame) -> pd.DataFrame:
    """The `total:` columns reshaped long, dropping figures a run does not report."""
    id_cols = ["powertrain", "cycle", "source_file"]
    total_cols = [c for c in runs.columns if c.startswith("total:")]
    long = runs.melt(
        id_vars=id_cols, value_vars=total_cols, var_name="quantity", value_name="value"
    )
    long["quantity"] = long["quantity"].str.removeprefix("total:")
    return long.dropna(subset=["value"]).reset_index(drop=True)


def params_long(runs: pd.DataFrame) -> pd.DataFrame:
    """The `param:` columns reshaped long."""
    id_cols = ["powertrain", "cycle", "source_file"]
    param_cols = [c for c in runs.columns if c.startswith("param:")]
    long = runs.melt(
        id_vars=id_cols, value_vars=param_cols, var_name="parameter", value_name="value"
    )
    long["parameter"] = long["parameter"].str.removeprefix("param:")
    return long.dropna(subset=["value"]).reset_index(drop=True)
