"""Shared page furniture: the header, the sidebar controls, and small display helpers.

Kept in one place so all three pages carry the same controls in the same order and the same
vocabulary. Wording rule followed here: label things by what the reader recognises — "Fuel
consumption", not "total consumption [l/100km]".
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import POWERTRAIN_ORDER, Palette, palette
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

#: The four canonical figures, with the display name and unit the reader sees.
CANONICAL_QUANTITIES: dict[str, tuple[str, str]] = {
    "co2_g_per_km": ("CO₂ per km", "g CO₂/km"),
    "consumption_l_per_100km": ("Fuel consumption", "l/100 km"),
    "energy_wh_per_100km": ("Electrical energy", "Wh/100 km"),
    "co2_g_total": ("CO₂ over the run", "g CO₂"),
}


def configure(title: str) -> Palette:
    """Page config plus the active palette. Call first in every page."""
    st.set_page_config(
        page_title=f"{title} · PWT workbooks",
        page_icon="🛞",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    return palette()


def _rgba(hex_colour: str, alpha: float) -> str:
    """A hex colour as rgba(), so fills track the active palette instead of being hardcoded."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def elevation_strip(trace: pd.DataFrame, pal: Palette) -> go.Figure | None:
    """The Spa elevation profile as a thin band.

    This is the recurring motif of the tool and it is real data, not ornament: the altitude
    column drives the grade term, which is why the same car returns different figures on the
    lap and on NEDC. Drawn flat and quiet so it frames the page without competing with it.
    """
    if "altitude_m" not in trace.columns or trace["altitude_m"].isna().all():
        return None
    x = "distance_m" if "distance_m" in trace.columns else "step"
    fig = go.Figure()
    fig.add_scatter(
        x=trace[x],
        y=trace["altitude_m"],
        mode="lines",
        line=dict(color=pal.series[0], width=1.5),  # linear: smoothing would misstate the profile
        fill="tozeroy",
        fillcolor=_rgba(pal.series[0], 0.14),
        hoverinfo="skip",
    )
    low, high = trace["altitude_m"].min(), trace["altitude_m"].max()
    fig.update_layout(
        height=64,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[low - (high - low) * 0.4, high + (high - low) * 0.2]),
    )
    return fig


def run_label(powertrain: str, cycle: str) -> str:
    return f"{POWERTRAIN_NAMES.get(powertrain, powertrain)} · {CYCLE_NAMES.get(cycle, cycle)}"


def sidebar_filters(runs: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Powertrain and cycle selection, shared by every page."""
    st.sidebar.subheader("Show")
    powertrains = st.sidebar.multiselect(
        "Powertrains",
        options=list(POWERTRAIN_ORDER),
        default=list(POWERTRAIN_ORDER),
        format_func=lambda p: POWERTRAIN_NAMES[p],
    )
    cycles = st.sidebar.multiselect(
        "Cycles",
        options=list(CYCLE_NAMES),
        default=list(CYCLE_NAMES),
        format_func=lambda c: CYCLE_NAMES[c],
    )
    return powertrains, cycles


def run_picker(runs: pd.DataFrame, label: str, *, key: str, index: int = 0) -> pd.Series:
    """Pick a single run. Returns that run's row."""
    options = list(runs.index)
    choice = st.selectbox(
        label,
        options=options,
        index=min(index, len(options) - 1),
        key=key,
        format_func=lambda i: run_label(runs.loc[i, "powertrain"], runs.loc[i, "cycle"]),
    )
    return runs.loc[choice]


def source_caption(*rows: pd.Series) -> None:
    """Name the workbook every figure on screen came from."""
    files = [f"`{row['source_file']}`" for row in rows]
    st.caption("Source: " + " · ".join(files))


def download(frame: pd.DataFrame, filename: str, label: str = "Download CSV") -> None:
    st.download_button(
        label,
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def data_notes(runs: pd.DataFrame) -> list[str]:
    """Plain statements about what the selected cells contain.

    Descriptive only — it says a figure is zero or negative so an empty or inverted bar is not
    mistaken for a rendering fault. It does not explain why, or what it would be if corrected.
    """
    notes: list[str] = []
    for _, row in runs.iterrows():
        name = run_label(row["powertrain"], row["cycle"])
        zeros = [
            display
            for column, (display, _) in CANONICAL_QUANTITIES.items()
            if pd.notna(row.get(column)) and row[column] == 0
        ]
        negatives = [
            column.removeprefix("total:")
            for column in runs.columns
            if column.startswith("total:") and pd.notna(row.get(column)) and row[column] < 0
        ]
        if zeros:
            notes.append(f"**{name}** reports 0 for {', '.join(zeros)}.")
        if negatives:
            notes.append(f"**{name}** reports a negative value for {', '.join(negatives)}.")
    return notes
