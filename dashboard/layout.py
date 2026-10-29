"""Shared page furniture: the header, the sidebar controls, and small display helpers.

Kept in one place so every page carries the same controls in the same order and the same
vocabulary. Wording rule followed here: label things by what the reader recognises — "Fuel
consumption", not "total consumption [l/100km]".
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import GAP_LABEL
from dashboard.theme import POWERTRAIN_ORDER, Palette, palette
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

#: The four canonical figures, with the display name and unit the reader sees.
CANONICAL_QUANTITIES: dict[str, tuple[str, str]] = {
    "co2_g_per_km": ("CO₂ per km", "g CO₂/km"),
    "consumption_l_per_100km": ("Fuel consumption", "l/100 km"),
    "energy_wh_per_100km": ("Electrical energy", "Wh/100 km"),
    "co2_g_total": ("CO₂ over the run", "g CO₂"),
}

#: Display names for the columns a chart can be plotted against.
X_LABELS: dict[str, str] = {
    "distance_m": "Distance (m)",
    "time_s": "Time (s)",
    "step": "Step",
}


#: What each cycle is. Kept in the dashboard package, not `pwt/`, because it is UI copy —
#: and because Community Cloud hot-reloads this folder but keeps `pwt/` cached from boot.
#: The prose describes the cycle; the figures beside it are measured from the supplied files
#: at run time rather than quoted, so they cannot drift from the data.
CYCLE_DEFINITIONS: dict[str, str] = {
    "nedc": (
        "**New European Driving Cycle** — the European laboratory test that produced official "
        "fuel and CO₂ figures until WLTP replaced it (phased in from 2017). It is synthetic "
        "rather than recorded: four repeated urban segments, then one extra-urban run up to "
        "120 km/h, driven on a rolling road. It is flat by definition — altitude is 0 "
        "throughout, so no energy goes into climbing — and a large share of it is spent "
        "stationary at idle. Its gentle accelerations and low average speed are why "
        "real-world consumption routinely exceeded NEDC figures, and why it was retired."
    ),
    "franco_eco": (
        "**A lap of Spa-Francorchamps, driven economically.** Not a regulatory cycle — a real "
        "7 km circuit, described corner by corner rather than second by second, which is why "
        "it has so few steps. It climbs and descends about 100 m per lap, so unlike NEDC the "
        "road gradient does real work here."
    ),
    "franco_sport": (
        "**The same Spa-Francorchamps lap, driven hard.** Identical route and gradient to the "
        "eco lap; only the speeds differ, which makes the pair a clean before-and-after on "
        "driving style alone."
    ),
}


def cycle_facts(trace: pd.DataFrame) -> str:
    """One line of measured facts about a cycle, computed from the trace itself."""
    speed = trace.get("speed_kph")
    if speed is None or speed.empty:
        return ""
    bits = [f"{len(trace)} steps"]

    # Distance is cumulative in the lap workbooks and per-step in the NEDC ones, so take
    # whichever reading that column actually supports rather than assuming one.
    distance = trace.get("distance_m")
    if distance is not None and distance.notna().any():
        metres = (
            distance.max() if distance.dropna().is_monotonic_increasing else distance.sum()
        )
        bits.append(f"{metres / 1000:.1f} km")

    time = trace.get("time_s")
    if time is not None and time.notna().any():
        bits.append(f"{time.max() / 60:.1f} min")

    bits.append(f"average {speed.mean():.0f} km/h, peak {speed.max():.0f} km/h")

    stopped = int((speed == 0).sum())
    if stopped:
        bits.append(f"stationary for {stopped} of {len(trace)} steps")

    altitude = trace.get("altitude_m")
    if altitude is not None and altitude.notna().any():
        spread = altitude.max() - altitude.min()
        bits.append("flat" if spread == 0 else f"{spread:.0f} m of elevation range")

    return " · ".join(bits)


#: Runs whose reported figures leave something out, keyed by (powertrain, cycle). Kept here
#: in the dashboard package so Community Cloud picks it up without a reboot.
RUN_NOTICES: dict[tuple[str, str], str] = {
    ("phev", "nedc"): (
        "**Charge-depleting run — electricity not counted.** `34 NEDC PHYBRID engine.xlsx` "
        "reports 0 l/100 km and 0 g CO₂/km, and that is what its formulas compute: the 40 kW "
        "motor covers every NEDC demand, and the battery falls only from 98 % to 78 %, never "
        "reaching the 23 % that brings the engine in. The sheet does not count the electricity "
        "the run draws (14.3 kWh/100 km, about 36 g CO₂/km at the EU grid's 250 g/kWh), so the "
        "zeros are not the car's footprint. `data/derived/` adds a charge-sustaining run "
        "(5.96 l/100 km); weighted the UN R101 way the two give 2.22 l/100 km."
    ),
}


def run_notice(powertrain: str | None, cycle: str | None) -> str | None:
    return RUN_NOTICES.get((powertrain or "", cycle or ""))


def mark_gap_value(
    value: float | None,
    powertrain: str | None,
    cycle: str | None,
    *,
    decimals: int = 3,
) -> str:
    """Format a reported figure for display, labelling a known gap in place.

    A figure the workbook does not report becomes an em dash. A figure from a run flagged in
    RUN_NOTICES keeps its value but carries `GAP_LABEL`, so a zero that leaves the electricity
    out cannot be read as the run's whole footprint.
    """
    if value is None or pd.isna(value):
        return "—"
    formatted = f"{value:,.{decimals}f}"
    return f"{formatted} — {GAP_LABEL}" if run_notice(powertrain, cycle) else formatted


def render_run_notices(*runs: pd.Series) -> None:
    """Warn about any run on screen whose figures leave something out."""
    seen: set[tuple[str, str]] = set()
    for row in runs:
        key = (row.get("powertrain") or "", row.get("cycle") or "")
        if key in seen:
            continue
        seen.add(key)
        notice = RUN_NOTICES.get(key)
        if notice:
            st.warning(f"**{run_label(*key)}** — {notice}", icon="⚠️")


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


def varying_parameters(runs: pd.DataFrame) -> pd.DataFrame:
    """Parameters that are not identical across every run given.

    A parameter counts as varying when the runs disagree on its value, or when some runs carry
    it and others do not — a plug-in hybrid has a battery mass that a petrol car has no row
    for, and that absence is a real difference, not a match. Values are compared as the
    workbooks report them; nothing is rounded to force agreement beyond float noise.
    """
    if len(runs) < 2:
        return pd.DataFrame()

    labels = [run_label(row["powertrain"], row["cycle"]) for _, row in runs.iterrows()]
    records = []
    for column in (c for c in runs.columns if c.startswith("param:")):
        values = [runs.iloc[i][column] for i in range(len(runs))]
        present = [v for v in values if pd.notna(v)]
        if not present:
            continue
        distinct = {round(float(v), 9) for v in present}
        if len(distinct) == 1 and len(present) == len(values):
            continue  # every run agrees and none is missing it
        record = {"Parameter": column.removeprefix("param:")}
        record.update(dict(zip(labels, values)))
        record["Distinct values"] = len(distinct)
        record["_missing"] = len(values) - len(present)
        records.append(record)

    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return (
        frame.sort_values(
            ["Distinct values", "_missing", "Parameter"], ascending=[False, False, True]
        )
        .drop(columns="_missing")
        .reset_index(drop=True)
    )


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
        if run_notice(row["powertrain"], row["cycle"]):
            continue  # already stated in full by its own notice
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
