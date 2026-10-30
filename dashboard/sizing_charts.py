"""Figures for the Sizing page. Each one carries a single claim.

Full hybrid and plug-in hybrid keep their powertrain colours from `theme`; anything that is
not the subject of a chart stays neutral, so the eye lands on the claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import Palette, style_axes

#: Sequential blue, reversed for the dark surface: the brightest cell is the best size.
_RAMP = [[0.0, "#cde2fb"], [0.15, "#86b6ef"], [0.35, "#3987e5"], [0.6, "#1c5cab"],
         [1.0, "#0d366b"]]
#: Both heatmaps share this scale, so a flat map and a steep one can be compared.
HEAT_MAX_PCT = 30.0


def _hybrid(pal: Palette) -> str:
    return pal.for_powertrain("hybrid")


def _phev(pal: Palette) -> str:
    return pal.for_powertrain("phev")


def crossover(band: pd.Series, rule: pd.Series) -> tuple[float, float] | None:
    """Where the band falls behind the sheets' rule: (one-way efficiency, g/km)."""
    gap = (band - rule).sort_index(ascending=False)
    for (e1, g1), (e2, g2) in zip(gap.items(), list(gap.items())[1:]):
        if g1 <= 0 < g2:
            at = e1 + (e2 - e1) * (0 - g1) / (g2 - g1)
            return at, float(np.interp(at, sorted(band.index), band.sort_index()))
    return None


def efficiency_lines(band: pd.Series, rule: pd.Series, petrol: float, pal: Palette) -> go.Figure:
    """Band against the sheets' rule as storage gets lossier, left to right."""
    fig = go.Figure()
    x = [e * 100 for e in band.index]
    fig.add_trace(go.Scatter(
        x=x, y=[petrol] * len(x), name="Petrol", mode="lines",
        line=dict(color=pal.text_muted, width=2, dash="dot"),
        hovertemplate="Petrol: %{y:.1f} g/km<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=rule.values, name="Sheets' rule", mode="lines+markers",
        line=dict(color=pal.text_secondary, width=2), marker=dict(size=8),
        hovertemplate="Sheets' rule: %{y:.1f} g/km<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=band.values, name="Charge-sustaining band", mode="lines+markers",
        line=dict(color=_hybrid(pal), width=3), marker=dict(size=9),
        hovertemplate="Band: %{y:.1f} g/km<extra></extra>",
    ))
    for y, text, colour in ((band.iloc[-1], "Band", _hybrid(pal)),
                            (rule.iloc[-1], "Sheets' rule", pal.text_secondary),
                            (petrol, "Petrol", pal.text_muted)):
        fig.add_annotation(x=x[-1], y=y, text=f"<b>{text}</b> {y:.0f}", showarrow=False,
                           xanchor="left", xshift=10, font=dict(color=pal.text_primary, size=12))
    cross = crossover(band, rule)
    if cross:
        fig.add_annotation(
            x=cross[0] * 100, y=cross[1], text=f"They cross near {cross[0] * 100:.0f} %",
            showarrow=True, arrowcolor=pal.text_muted, arrowhead=0, ax=-70, ay=-46,
            font=dict(color=pal.text_primary, size=12),
        )
    style_axes(fig, pal, x_title="Energy kept each way through motor, inverter and battery (%)",
               y_title="g CO₂/km")
    fig.update_xaxes(autorange=False, range=[101.5, 73], tickvals=x, showgrid=False)
    fig.update_layout(height=380, hovermode="x unified", margin=dict(r=30))
    return fig


def petrol_gap(free: dict[str, float], lossy: dict[str, float], pal: Palette) -> go.Figure:
    """How far below petrol the full hybrid sits, without and with storage losses."""
    fig = go.Figure()
    names = list(free)[::-1]
    for name in names:
        fig.add_trace(go.Scatter(
            x=[free[name], lossy[name]], y=[name, name], mode="lines", showlegend=False,
            line=dict(color=pal.axis, width=2), hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=[free[n] for n in names], y=names, mode="markers+text", name="Free storage",
        marker=dict(size=13, color=pal.surface, line=dict(color=_hybrid(pal), width=2)),
        text=[f"{free[n]:+.0f} %" for n in names], textposition="middle left",
        textfont=dict(color=pal.text_secondary, size=12),
        hovertemplate="%{y}, free storage: %{x:+.1f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[lossy[n] for n in names], y=names, mode="markers+text", name="85 % each way",
        marker=dict(size=13, color=_hybrid(pal)),
        text=[f"{lossy[n]:+.0f} %" for n in names], textposition="middle right",
        textfont=dict(color=pal.text_primary, size=12),
        hovertemplate="%{y}, 85 %% each way: %{x:+.1f} %<extra></extra>".replace("%%", "%"),
    ))
    fig.add_vline(x=0, line=dict(color=pal.text_muted, width=1.5))
    fig.add_annotation(x=0, y=1, yref="paper", text="Level with petrol", showarrow=False,
                       xanchor="left", xshift=6, yanchor="bottom",
                       font=dict(color=pal.text_muted, size=12))
    style_axes(fig, pal, x_title="Full hybrid CO₂ compared with petrol (%)")
    low = min([*free.values(), *lossy.values()])
    high = max([*free.values(), *lossy.values()])
    fig.update_xaxes(range=[low - 7, high + 7], ticksuffix=" %", zeroline=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=pal.text_primary, size=13))
    fig.update_layout(height=300, margin=dict(t=30))
    return fig


def size_heatmap(frame: pd.DataFrame, pal: Palette, show_scale: bool = True) -> go.Figure:
    """One powertrain on one cycle: every size, as % above the best buildable one."""
    built = frame[frame["buildable"]]
    top = built.loc[built["co2_eu"].idxmin()]
    grid = frame.pivot(index="battery_kwh", columns="motor_kw", values="co2_eu")
    allowed = frame.pivot(index="battery_kwh", columns="motor_kw", values="buildable")
    co2 = grid.where(allowed.astype(bool))
    above = (co2 / top["co2_eu"] - 1) * 100
    # Indexed cells: numeric-looking category labels get read as positions by the annotations.
    motors, batteries = list(grid.columns), list(grid.index)
    x, y = list(range(len(motors))), list(range(len(batteries)))
    fig = go.Figure(go.Heatmap(
        z=above.values, x=x, y=y, customdata=co2.values, zmin=0, zmax=HEAT_MAX_PCT,
        colorscale=_RAMP, xgap=2, ygap=2, hoverongaps=False, showscale=show_scale,
        colorbar=dict(title=dict(text="% above best", font=dict(size=12, color=pal.text_muted)),
                      ticksuffix=" %", thickness=10, len=0.8, outlinewidth=0,
                      tickfont=dict(color=pal.text_muted, size=11)),
        text=[[f"{b:g} kWh, {m:g} kW" for m in motors] for b in batteries],
        hovertemplate="%{text}<br>%{customdata:.1f} g CO₂/km"
                      "<br>%{z:.1f} % above best<extra></extra>",
    ))
    best_x, best_y = motors.index(top["motor_kw"]), batteries.index(top["battery_kwh"])
    fig.add_trace(go.Scatter(
        x=[best_x], y=[best_y], mode="markers",
        marker=dict(size=15, symbol="circle-open", color="#0b0b0b", line=dict(width=3)),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_annotation(
        x=best_x, y=best_y, ax=-58 if best_x > len(x) / 2 else 58, ay=-48,
        text=f"<b>Best: {top['battery_kwh']:g} kWh, {top['motor_kw']:g} kW</b>"
             f"<br>{top['co2_eu']:.0f} g/km",
        arrowcolor=pal.text_primary, arrowhead=0, bgcolor=pal.surface, borderpad=4,
        font=dict(color=pal.text_primary, size=12), align="left",
    )
    fig.add_annotation(x=x[-2], y=0.5, text="Battery can't<br>supply this power",
                       showarrow=False, font=dict(color=pal.text_muted, size=11))
    style_axes(fig, pal, x_title="Motor (kW)", y_title="Battery (kWh)")
    fig.update_xaxes(tickvals=x, ticktext=[f"{m:g}" for m in motors], showgrid=False,
                     showline=False, range=[-0.5, len(x) - 0.5], constrain="domain")
    fig.update_yaxes(tickvals=y, ticktext=[f"{b:g}" for b in batteries], showgrid=False,
                     showline=False, range=[-0.5, len(y) - 0.5])
    fig.update_layout(height=430)
    return fig


def phev_lines(eu: pd.Series, fr: pd.Series, ymax: float, note: tuple[float, str] | None,
               pal: Palette) -> go.Figure:
    """CO2 against battery size on both grids, best motor at each size."""
    fig = go.Figure()
    for series, name, dash, text_colour in ((eu, "EU grid, 250 g/kWh", "solid", pal.text_primary),
                                            (fr, "French grid, 73 g/kWh", "dash",
                                             pal.text_secondary)):
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values, name=name, mode="lines+markers",
            line=dict(color=_phev(pal), width=3 if dash == "solid" else 2, dash=dash),
            marker=dict(size=6),
            hovertemplate=f"{name}: %{{y:.1f}} g/km<extra></extra>",
        ))
        fig.add_annotation(x=series.index[-1], y=series.iloc[-1], text=f"{series.iloc[-1]:.0f}",
                           showarrow=False, xanchor="left", xshift=8,
                           font=dict(color=text_colour, size=12))
    if note:
        at, text = note
        fig.add_annotation(x=at, y=eu.loc[at], text=text, ax=-60 if at > 15 else 70, ay=-62, arrowhead=0,
                           arrowcolor=pal.text_muted, align="left",
                           font=dict(color=pal.text_primary, size=12))
    style_axes(fig, pal, x_title="Battery (kWh)", y_title="g CO₂/km")
    fig.update_xaxes(range=[0, 22], showgrid=False, tickvals=[1, 5, 10, 15, 20])
    fig.update_yaxes(range=[0, ymax])
    fig.update_layout(height=360, hovermode="x unified")
    return fig
