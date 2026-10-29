"""Plotly figure builders.

Each function is pure — `(data, palette) -> go.Figure` — with no Streamlit calls, so a figure
can also be written to PNG later without touching the app.

Conventions enforced here, from the data-viz method:
  * one y-axis per chart, never a second scale;
  * 2px lines, >=8px markers, 4px rounded bar ends, a 2px surface gap between adjacent bars;
  * a legend whenever two or more series are drawn, and direct value labels on bars (which is
    also the required relief for aqua/yellow falling below 3:1 on the light surface);
  * recessive grid and axes; hover on every mark.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import POWERTRAIN_ORDER, Palette
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

LINE_WIDTH = 2
MARKER_SIZE = 8
CORNER_RADIUS = 4
BAR_GAP_PX = 2
#: Shown in place of a figure from a run flagged in `layout.RUN_NOTICES`.
GAP_LABEL = "electricity not counted"

#: Dash patterns in a fixed order, used as a secondary encoding when several lines share a
#: colour. Position determines pattern, so a member keeps its pattern as the selection changes.
DASH_CYCLE: tuple[str, ...] = ("solid", "dash", "dot", "dashdot")


def _rgba(hex_colour: str, alpha: float) -> str:
    """A hex colour as rgba(), so fills track the active palette."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _fmt(value: float) -> str:
    """Compact value label: keeps small figures readable and large ones short."""
    if value is None or pd.isna(value):
        return ""
    magnitude = abs(value)
    if magnitude >= 10000:
        return f"{value:,.0f}"
    if magnitude >= 100:
        return f"{value:,.1f}"
    if magnitude >= 1:
        return f"{value:,.2f}"
    return f"{value:,.3f}"


def grouped_totals(
    runs: pd.DataFrame,
    column: str,
    pal: Palette,
    *,
    unit: str = "",
    gaps: set[tuple[str, str]] | None = None,
) -> go.Figure:
    """One bar per (cycle, powertrain) for a single reported quantity.

    Cycles sit on the x-axis and powertrains are the series, so the comparison the group cares
    about — technologies on the same cycle — is the one read left to right within a group.
    Runs that do not report this quantity are simply absent rather than drawn as zero.

    `gaps` names (powertrain, cycle) pairs whose figures leave something out. Their bar is
    labelled with `GAP_LABEL` rather than its value, so a zero-height bar cannot be read as the
    whole result.
    """
    gaps = gaps or set()
    fig = go.Figure()
    cycles = [c for c in CYCLE_NAMES if c in set(runs["cycle"])]

    for powertrain in POWERTRAIN_ORDER:
        subset = runs[runs["powertrain"] == powertrain]
        if subset.empty:
            continue
        by_cycle = subset.set_index("cycle")[column]
        values = [by_cycle.get(c) for c in cycles]
        if all(v is None or pd.isna(v) for v in values):
            continue  # e.g. a BEV has no fuel consumption to show
        fig.add_bar(
            name=POWERTRAIN_NAMES[powertrain],
            x=[CYCLE_NAMES[c] for c in cycles],
            y=values,
            marker=dict(
                color=pal.for_powertrain(powertrain),
                cornerradius=CORNER_RADIUS,
                line=dict(color=pal.surface, width=BAR_GAP_PX),
            ),
            text=[
                GAP_LABEL if (powertrain, cycle) in gaps else _fmt(value)
                for cycle, value in zip(cycles, values)
            ],
            textposition="outside",
            textfont=dict(color=pal.text_secondary, size=11),
            cliponaxis=False,
            hovertemplate=(
                f"<b>{POWERTRAIN_NAMES[powertrain]}</b><br>%{{x}}<br>"
                f"%{{y:.4g}} {unit}<extra></extra>"
            ),
            textfont_size=11,
        )

    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.06, showlegend=True)
    return fig


def trace_lines(
    trace: pd.DataFrame, columns: list[str], x_column: str, pal: Palette
) -> go.Figure:
    """Selected per-step columns against a chosen x-axis.

    Single-axis by rule: plotting quantities of different magnitude together is the caller's
    choice, and the honest fix is separate charts rather than a second y-scale.
    """
    fig = go.Figure()
    for index, column in enumerate(columns):
        colour = pal.series[index % len(pal.series)]
        fig.add_scatter(
            name=column,
            x=trace[x_column],
            y=trace[column],
            mode="lines+markers",
            line=dict(color=colour, width=LINE_WIDTH),
            marker=dict(size=MARKER_SIZE, color=colour, line=dict(color=pal.surface, width=2)),
            hovertemplate=f"<b>{column}</b><br>{x_column} %{{x:.4g}}<br>%{{y:.4g}}<extra></extra>",
        )
    fig.update_layout(showlegend=len(columns) > 1, hovermode="x unified")
    return fig


def speed_and_altitude(trace: pd.DataFrame, x_column: str, pal: Palette) -> go.Figure:
    """Speed over the cycle, with altitude as a recessive filled band behind it.

    Altitude is drawn on its own subplot row rather than a second y-axis, so the two are
    readable together without two scales on one frame.
    """
    from plotly.subplots import make_subplots

    has_altitude = "altitude_m" in trace.columns and trace["altitude_m"].notna().any()
    rows = 2 if has_altitude else 1
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.68, 0.32] if has_altitude else [1.0],
    )

    fig.add_scatter(
        name="Speed (kph)",
        x=trace[x_column],
        y=trace["speed_kph"],
        mode="lines+markers",
        line=dict(color=pal.series[0], width=LINE_WIDTH, shape="linear"),
        marker=dict(size=MARKER_SIZE, color=pal.series[0], line=dict(color=pal.surface, width=2)),
        hovertemplate="Speed %{y:.1f} kph<extra></extra>",
        row=1,
        col=1,
    )

    if has_altitude:
        fig.add_scatter(
            name="Altitude (m)",
            x=trace[x_column],
            y=trace["altitude_m"],
            mode="lines",
            line=dict(color=pal.text_muted, width=LINE_WIDTH),
            fill="tozeroy",
            fillcolor=_rgba(pal.text_muted, 0.18),
            hovertemplate="Altitude %{y:.0f} m<extra></extra>",
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Altitude (m)", row=2, col=1)
        # Altitude varies over a narrow band; starting the axis at zero would flatten it.
        low, high = trace["altitude_m"].min(), trace["altitude_m"].max()
        pad = max((high - low) * 0.15, 1.0)
        fig.update_yaxes(range=[low - pad, high + pad], row=2, col=1)

    fig.update_yaxes(title_text="Speed (kph)", row=1, col=1)
    fig.update_layout(showlegend=False, hovermode="x unified")
    return fig


def gear_steps(trace: pd.DataFrame, x_column: str, pal: Palette) -> go.Figure:
    """Gear as a step plot — it is a held state, not a continuous quantity."""
    fig = go.Figure()
    fig.add_scatter(
        name="Gear",
        x=trace[x_column],
        y=trace["gear"],
        mode="lines+markers",
        line=dict(color=pal.series[1], width=LINE_WIDTH, shape="hv"),
        marker=dict(size=MARKER_SIZE, color=pal.series[1], line=dict(color=pal.surface, width=2)),
        hovertemplate="Gear %{y}<extra></extra>",
    )
    fig.update_yaxes(dtick=1)
    fig.update_layout(showlegend=False, hovermode="x unified")
    return fig


def force_breakdown(trace: pd.DataFrame, x_column: str, pal: Palette) -> go.Figure:
    """Resistive and acceleration force per step, plus their total.

    Both components are signed in the supplied data — acceleration force goes negative under
    braking and resistive force negative downhill — so these are drawn as overlaid lines, not
    a stack. A stack would imply they are same-signed parts of a whole, which they are not.
    """
    fig = go.Figure()
    series = [
        ("resistive_force_n", "Resistive force (N)", pal.series[0]),
        ("acceleration_force_n", "Acceleration force (N)", pal.series[1]),
        ("total_force_n", "Total force (N)", pal.series[2]),
    ]
    for column, label, colour in series:
        if column not in trace.columns or trace[column].isna().all():
            continue
        fig.add_scatter(
            name=label,
            x=trace[x_column],
            y=trace[column],
            mode="lines",
            line=dict(color=colour, width=LINE_WIDTH),
            hovertemplate=f"{label} %{{y:,.0f}}<extra></extra>",
        )
    fig.add_hline(y=0, line=dict(color=pal.axis, width=1, dash="dot"))
    fig.update_layout(showlegend=True, hovermode="x unified")
    return fig


def overlay_traces(
    frames: list[pd.DataFrame],
    labels: list[str],
    colours: list[str],
    column: str,
    x_column: str,
    pal: Palette,
    dashes: list[str] | None = None,
) -> go.Figure:
    """One per-step column from several runs on a single axis.

    A run that does not carry the column is skipped rather than drawn as a gap — the electric
    workbooks have no gear column at all, and an empty series in the legend would suggest the
    data is missing when the concept simply does not apply.

    `dashes` is an optional secondary encoding, one Plotly dash string per frame in the same
    order as `frames`, for when several lines share a colour and need another way to tell them
    apart. When `None`, every line is solid.
    """
    patterns = dashes or ["solid"] * len(frames)
    fig = go.Figure()
    for frame, label, colour, dash in zip(frames, labels, colours, patterns):
        if column not in frame.columns or frame[column].isna().all():
            continue
        fig.add_scatter(
            name=label,
            x=frame[x_column],
            y=frame[column],
            mode="lines+markers",
            line=dict(color=colour, width=LINE_WIDTH, dash=dash),
            marker=dict(size=MARKER_SIZE, color=colour, line=dict(color=pal.surface, width=2)),
            hovertemplate=f"<b>{label}</b><br>%{{y:.4g}}<extra></extra>",
        )
    fig.update_layout(showlegend=len(fig.data) > 1, hovermode="x unified")
    return fig


def compare_traces(
    left: pd.DataFrame,
    right: pd.DataFrame,
    column: str,
    x_column: str,
    labels: tuple[str, str],
    colours: tuple[str, str],
    pal: Palette,
) -> go.Figure:
    """One per-step column from two runs on a single axis."""
    fig = overlay_traces(
        [left, right], list(labels), list(colours), column, x_column, pal
    )
    fig.update_layout(showlegend=True)
    return fig
