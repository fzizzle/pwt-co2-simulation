"""Plotly figure builders.

Each function is pure — `(data, palette) -> go.Figure` — with no Streamlit calls, so a figure
can also be written to PNG later without touching the app.

Conventions enforced here, aligned with the group deck:
  * one y-axis per chart, never a second scale;
  * 2px lines, >=8px markers, 4px rounded bar ends, a 2px surface gap between adjacent bars;
  * direct value labels on bars, units labelled, subdued horizontal gridlines;
  * dash and marker-symbol redundancy on multi-series lines so same-powertrain overlays and
    BEV vs PHEV stay distinct for colour-blind viewers;
  * outlined bars + "*" for infeasible model results (`short_steps > 0`);
  * compact "†" marker + caption for workbook runs flagged with a gap, so narrow mobile bars
    never shrink a long phrase to ~2 px.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.labels import column as column_label
from dashboard.labels import figure
from dashboard.theme import POWERTRAIN_ORDER, Palette, style_axes
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

LINE_WIDTH = 2
MARKER_SIZE = 8
CORNER_RADIUS = 4
BAR_GAP_PX = 2
#: Full text for tables and chart captions when a workbook leaves something out.
GAP_LABEL = "electricity not counted"
#: Short mark placed above narrow bars so Plotly never shrinks the label to ~2 px.
GAP_MARKER = "†"

#: Dash patterns in a fixed order, used as a secondary encoding when several lines share a
#: colour or when colour-blind viewers compare BEV vs PHEV.
DASH_CYCLE: tuple[str, ...] = ("solid", "dash", "dot", "dashdot")

#: Marker symbols in a fixed order, paired with `DASH_CYCLE` for shape redundancy.
MARKER_CYCLE: tuple[str, ...] = ("circle", "square", "diamond", "triangle-up")

MAX_MARKED_STEPS = 200


def _mode(trace: pd.DataFrame) -> str:
    """Markers show a workbook's segments; on a 5 m lap their halos would hide the line."""
    return "lines+markers" if len(trace) <= MAX_MARKED_STEPS else "lines"


def _rgba(hex_colour: str, alpha: float) -> str:
    """A hex colour as rgba(), so fills track the active palette."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def _fmt(value: float) -> str:
    """Bar label, at the same precision as the tables."""
    if value is None or pd.isna(value):
        return ""
    return figure(value)


def grouped_totals(
    runs: pd.DataFrame,
    column: str,
    pal: Palette,
    *,
    unit: str = "",
    gaps: set[tuple[str, str]] | None = None,
    infeasible: set[tuple[str, str]] | None = None,
    show_footnote: bool = True,
) -> go.Figure:
    """One bar per (cycle, powertrain) for a single reported or modelled quantity.

    Cycles sit on the x-axis and powertrains are the series, so technologies on the same cycle
    are read left to right within a group. Runs that do not report this quantity are absent
    rather than drawn as zero.

    `gaps` names `(powertrain, cycle)` pairs whose workbook figures leave something out. Their
    bar carries `GAP_MARKER` ("†") with an inline footnote caption so the label stays readable
    at 390 px instead of shrinking to ~2 px.

    `infeasible` names `(powertrain, cycle)` pairs where the engine falls short of the trace
    (`short_steps > 0`). They follow the deck's hollow outlined bar + "*" convention.
    """
    gaps = gaps or set()
    infeasible = infeasible or set()
    fig = go.Figure()
    cycles = [c for c in CYCLE_NAMES if c in set(runs["cycle"])]
    extra_cycles = [c for c in runs["cycle"].drop_duplicates() if c not in cycles]
    cycles.extend(extra_cycles)
    has_gap = False
    has_infeasible = False

    for powertrain in POWERTRAIN_ORDER:
        subset = runs[runs["powertrain"] == powertrain]
        if subset.empty:
            continue
        by_cycle = subset.set_index("cycle")[column]
        values = [by_cycle.get(c) for c in cycles]
        if all(v is None or pd.isna(v) for v in values):
            continue  # e.g. a BEV has no fuel consumption to show

        colour = pal.for_powertrain(powertrain)
        is_infeasible = [(powertrain, c) in infeasible for c in cycles]
        is_gap = [(powertrain, c) in gaps for c in cycles]
        has_gap = has_gap or any(is_gap)
        has_infeasible = has_infeasible or any(is_infeasible)

        if any(is_infeasible):
            marker_colour: str | list[str] = [
                _rgba(colour, 0.10) if bad else colour for bad in is_infeasible
            ]
            line_colour: str | list[str] = [
                colour if bad else pal.surface for bad in is_infeasible
            ]
            line_width: float | list[float] = [
                2.5 if bad else BAR_GAP_PX for bad in is_infeasible
            ]
        else:
            marker_colour = colour
            line_colour = pal.surface
            line_width = BAR_GAP_PX

        labels = []
        notes = []
        for cycle, value, gap, bad in zip(cycles, values, is_gap, is_infeasible):
            if gap:
                labels.append(GAP_MARKER)
                notes.append(f"<br>{GAP_MARKER} {GAP_LABEL}")
            elif bad:
                base = _fmt(value)
                labels.append(f"{base}*" if base else "")
                notes.append("<br>* engine short of trace (conditional)")
            else:
                labels.append(_fmt(value))
                notes.append("")

        fig.add_bar(
            name=POWERTRAIN_NAMES[powertrain],
            x=[CYCLE_NAMES.get(c, c) for c in cycles],
            y=values,
            customdata=notes,
            marker=dict(
                color=marker_colour,
                cornerradius=CORNER_RADIUS,
                line=dict(color=line_colour, width=line_width),
            ),
            text=labels,
            textposition="outside",
            textfont=dict(color=pal.text_secondary, size=12),
            cliponaxis=False,
            hovertemplate=(
                f"<b>{POWERTRAIN_NAMES[powertrain]}</b><br>%{{x}}<br>"
                f"%{{y:,.4~r}} {unit}%{{customdata}}<extra></extra>"
            ),
        )

    footnotes = []
    if has_gap:
        footnotes.append(f"{GAP_MARKER} {GAP_LABEL}")
    if has_infeasible:
        footnotes.append("* outlined: engine short of trace on some steps (conditional result)")
    if footnotes and show_footnote:
        fig.add_annotation(
            text=" · ".join(footnotes),
            xref="paper",
            yref="paper",
            x=0,
            y=-0.22,
            xanchor="left",
            yanchor="top",
            showarrow=False,
            font=dict(color=pal.text_muted, size=12),
        )

    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.06, showlegend=True)
    return fig


def model_co2_bars(
    frame: pd.DataFrame,
    pal: Palette,
    *,
    column: str = "co2_eu",
    unit: str = "g CO₂/km",
    height: int = 280,
    show_footnote: bool = True,
) -> go.Figure:
    """Deck-style bar chart for model CO₂ results with outlined hollow bars for `short_steps > 0`.

    Works cleanly for a single-cycle preview (such as WLTC Class 3 on Home) where each car gets
    its own labelled bar with direct values, units, and explicit feasibility marks.
    """
    fig = go.Figure()
    has_infeasible = False

    for powertrain in POWERTRAIN_ORDER:
        subset = frame[frame["powertrain"] == powertrain]
        if subset.empty:
            continue
        row = subset.iloc[0]
        value = float(row[column])
        short_steps = int(row.get("short_steps", 0) or 0)
        short_kw = float(row.get("short_kw", 0.0) or 0.0)
        hollow = short_steps > 0
        has_infeasible = has_infeasible or hollow
        colour = pal.for_powertrain(powertrain)
        label = f"{value:.1f}*" if hollow else f"{value:.1f}"
        feas_note = (
            f"Short on {short_steps} steps (−{short_kw:.1f} kW peak)"
            if hollow
            else "Feasible on every step"
        )
        fig.add_bar(
            name=POWERTRAIN_NAMES[powertrain],
            x=[POWERTRAIN_NAMES[powertrain]],
            y=[value],
            marker=dict(
                color=_rgba(colour, 0.10) if hollow else colour,
                cornerradius=CORNER_RADIUS,
                line=dict(color=colour if hollow else pal.surface, width=2.5 if hollow else BAR_GAP_PX),
            ),
            text=[label],
            textposition="outside",
            textfont=dict(color=pal.text_primary, size=14),
            cliponaxis=False,
            hovertemplate=(
                f"<b>{POWERTRAIN_NAMES[powertrain]}</b><br>"
                f"{value:.1f} {unit}<br>{feas_note}<extra></extra>"
            ),
        )

    style_axes(fig, pal, y_title=unit)
    ymax = float(frame[column].max()) * 1.24 if not frame.empty else 100.0
    fig.update_yaxes(range=[0, ymax])
    fig.update_layout(
        height=height,
        showlegend=False,
        bargap=0.35,
        margin=dict(l=8, r=8, t=20, b=46 if (has_infeasible and show_footnote) else 12),
    )
    if has_infeasible and show_footnote:
        fig.add_annotation(
            text="* outlined: engine short of trace on some steps (conditional result)",
            xref="paper",
            yref="paper",
            x=0,
            y=-0.26,
            xanchor="left",
            yanchor="top",
            showarrow=False,
            font=dict(color=pal.text_muted, size=12),
        )
    return fig


def trace_lines(
    trace: pd.DataFrame, columns: list[str], x_column: str, pal: Palette
) -> go.Figure:
    """Selected per-step columns against a chosen x-axis.

    Single-axis by rule: plotting quantities of different magnitude together is the caller's
    choice, and the honest fix is separate charts rather than a second y-scale. Each series gets
    a distinct dash pattern and marker symbol alongside its colour.
    """
    fig = go.Figure()
    for index, column in enumerate(columns):
        colour = pal.series[index % len(pal.series)]
        dash = DASH_CYCLE[index % len(DASH_CYCLE)]
        symbol = MARKER_CYCLE[index % len(MARKER_CYCLE)]
        name = column_label(column)
        fig.add_scatter(
            name=name,
            x=trace[x_column],
            y=trace[column],
            mode=_mode(trace),
            line=dict(color=colour, width=LINE_WIDTH, dash=dash),
            marker=dict(
                size=MARKER_SIZE,
                symbol=symbol,
                color=colour,
                line=dict(color=pal.surface, width=2),
            ),
            hovertemplate=f"<b>{name}</b><br>%{{y:,.4~r}}<extra></extra>",
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

    speed_colour = pal.for_powertrain("bev")
    fig.add_scatter(
        name="Speed (km/h)",
        x=trace[x_column],
        y=trace["speed_kph"],
        mode=_mode(trace),
        line=dict(color=speed_colour, width=LINE_WIDTH, shape="linear"),
        marker=dict(size=MARKER_SIZE, color=speed_colour, line=dict(color=pal.surface, width=2)),
        hovertemplate="Speed %{y:.0f} km/h<extra></extra>",
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

    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    fig.update_layout(showlegend=False, hovermode="x unified")
    return fig


def gear_steps(trace: pd.DataFrame, x_column: str, pal: Palette) -> go.Figure:
    """Gear as a step plot — it is a held state, not a continuous quantity."""
    fig = go.Figure()
    gear_colour = pal.series[0]
    fig.add_scatter(
        name="Gear",
        x=trace[x_column],
        y=trace["gear"],
        mode=_mode(trace),
        line=dict(color=gear_colour, width=LINE_WIDTH, shape="hv"),
        marker=dict(size=MARKER_SIZE, color=gear_colour, line=dict(color=pal.surface, width=2)),
        hovertemplate="Gear %{y}<extra></extra>",
    )
    fig.update_yaxes(dtick=1)
    fig.update_layout(showlegend=False, hovermode="x unified")
    return fig


def force_breakdown(trace: pd.DataFrame, x_column: str, pal: Palette) -> go.Figure:
    """Resistive and acceleration force per step, plus their total.

    Both components are signed in the supplied data — acceleration force goes negative under
    braking and resistive force negative downhill — so these are drawn as overlaid lines with
    distinct dash patterns rather than a stack.
    """
    fig = go.Figure()
    series = [
        ("resistive_force_n", "Resistive force (N)", pal.series[3], "solid"),
        ("acceleration_force_n", "Acceleration force (N)", pal.series[0], "dash"),
        ("total_force_n", "Total force (N)", pal.text_primary, "dot"),
    ]
    for column, label, colour, dash in series:
        if column not in trace.columns or trace[column].isna().all():
            continue
        fig.add_scatter(
            name=label,
            x=trace[x_column],
            y=trace[column],
            mode="lines",
            line=dict(color=colour, width=LINE_WIDTH, dash=dash),
            hovertemplate=f"{label.removesuffix(' (N)')} %{{y:,.0f}} N<extra></extra>",
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
    markers: list[str] | None = None,
) -> go.Figure:
    """One per-step column from several runs on a single axis.

    A run that does not carry the column is skipped rather than drawn as a gap — the electric
    workbooks have no gear column at all, and an empty series in the legend would suggest the
    data is missing when the concept simply does not apply.

    `dashes` is an optional secondary encoding, one Plotly dash string per frame in the same
    order as `frames`, for when several lines share a colour and need another way to tell them
    apart. When `None`, every line is solid, while `markers` still assigns distinct marker
    symbols per frame so BEV vs PHEV remain distinguishable under colour-vision deficiency.
    """
    patterns = dashes or ["solid"] * len(frames)
    symbols = markers or [MARKER_CYCLE[i % len(MARKER_CYCLE)] for i in range(len(frames))]
    fig = go.Figure()
    for frame, label, colour, dash, symbol in zip(frames, labels, colours, patterns, symbols):
        if column not in frame.columns or frame[column].isna().all():
            continue
        fig.add_scatter(
            name=label,
            x=frame[x_column],
            y=frame[column],
            mode="lines+markers",
            line=dict(color=colour, width=LINE_WIDTH, dash=dash),
            marker=dict(
                size=MARKER_SIZE,
                symbol=symbol,
                color=colour,
                line=dict(color=pal.surface, width=2),
            ),
            hovertemplate=f"<b>{label}</b><br>{column_label(column)}: %{{y:,.4~r}}<extra></extra>",
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
    """One per-step column from two runs on a single axis.

    Always assigns distinct dash patterns and marker symbols so two runs of the same powertrain
    (or BEV vs PHEV under CVD) never look identical.
    """
    fig = overlay_traces(
        [left, right],
        list(labels),
        list(colours),
        column,
        x_column,
        pal,
        dashes=list(DASH_CYCLE[:2]),
        markers=list(MARKER_CYCLE[:2]),
    )
    fig.update_layout(showlegend=True)
    return fig
