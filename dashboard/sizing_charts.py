"""Figures for the Sizing page. Each one carries a single claim.

Full hybrid and plug-in hybrid keep their powertrain colours from `theme`; anything that is
not the subject of a chart stays neutral, so the eye lands on the claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import Palette, style_axes

#: Sequential blue, reversed for the dark surface: brightest cell is lowest CO2; every stop >= 3:1 vs #000000.
_RAMP = [[0.0, "#eef5fe"], [0.2, "#94c4f7"], [0.45, "#4c96ec"], [0.75, "#2874d2"],
         [1.0, "#1c5cab"]]
#: Both heatmaps share this scale, so a flat map and a steep one can be compared.
HEAT_MAX_PCT = 30.0
#: Label shown wherever an engine-shortfall point is plotted or summarised.
PROVISIONAL_LABEL = "provisional: engine short of the trace"
_BY_BATTERY_COLUMNS = ["battery_kwh", "motor_kw", "co2", "short_steps", "short_kw", "provisional"]


def best_by_battery(
    frame: pd.DataFrame,
    powertrain: str,
    cycle: str,
    co2: str = "co2_eu",
    *,
    feasible_only: bool = False,
) -> pd.DataFrame:
    """Lowest-CO2 buildable motor at each battery size, keeping motor and shortfall fields."""
    part = frame[(frame["powertrain"] == powertrain) & (frame["cycle"] == cycle) & frame["buildable"]]
    if feasible_only:
        part = part[part["short_steps"] == 0]
    if part.empty:
        return pd.DataFrame(columns=_BY_BATTERY_COLUMNS)
    rows = []
    for battery_kwh, group in part.groupby("battery_kwh", sort=True):
        top = group.loc[group[co2].idxmin()]
        short_steps = int(top["short_steps"])
        rows.append({
            "battery_kwh": float(battery_kwh),
            "motor_kw": float(top["motor_kw"]),
            "co2": float(top[co2]),
            "short_steps": short_steps,
            "short_kw": float(top["short_kw"]),
            "provisional": short_steps > 0,
        })
    return pd.DataFrame(rows, columns=_BY_BATTERY_COLUMNS)


def best_selection(frame: pd.DataFrame, co2: str = "co2_eu") -> dict[str, object]:
    """Separate feasible and provisional lowest-CO2 selections for one (powertrain, cycle) slice."""
    built = frame[frame["buildable"]]
    feasible = built[built["short_steps"] == 0]
    best_feasible = feasible.loc[feasible[co2].idxmin()] if not feasible.empty else None
    best_overall = built.loc[built[co2].idxmin()] if not built.empty else None
    best_provisional = (
        best_overall
        if best_overall is not None and int(best_overall["short_steps"]) > 0
        else None
    )
    return {
        "feasible": best_feasible,
        "provisional": best_provisional,
        "feasible_count": int(len(feasible)),
        "buildable_count": int(len(built)),
    }


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
            showarrow=True, arrowcolor=pal.text_muted, arrowhead=0, ax=56, ay=-42,
            font=dict(color=pal.text_primary, size=12),
        )
    style_axes(fig, pal, x_title="Energy kept each way through motor, inverter and battery (%)",
               y_title="g CO₂/km")
    fig.update_xaxes(autorange=False, range=[101.5, 73], tickvals=x, showgrid=False)
    fig.update_layout(height=380, hovermode="x unified", margin=dict(l=8, r=128, t=28, b=12))
    return fig


def petrol_gap(free: dict[str, float], lossy: dict[str, float], pal: Palette) -> go.Figure:
    """How far below petrol the full hybrid sits, without and with storage losses."""
    fig = go.Figure()
    names = list(free)[::-1]
    for name in names:
        fig.add_trace(go.Scatter(
            x=[free[name], lossy[name]], y=[name, name], mode="lines", showlegend=False,
            line=dict(color=pal.text_muted, width=2), hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=[free[n] for n in names], y=names, mode="markers+text", name="Free storage",
        marker=dict(size=13, color=pal.surface, line=dict(color=_hybrid(pal), width=2)),
        text=[f"{free[n]:+.0f} %" for n in names], textposition="middle left",
        textfont=dict(color=pal.text_secondary, size=12), cliponaxis=False,
        hovertemplate="%{y}, free storage: %{x:+.1f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[lossy[n] for n in names], y=names, mode="markers+text", name="85 % each way",
        marker=dict(size=13, color=_hybrid(pal)),
        text=[f"{lossy[n]:+.0f} %" for n in names], textposition="middle right",
        textfont=dict(color=pal.text_primary, size=12), cliponaxis=False,
        hovertemplate="%{y}, 85 %% each way: %{x:+.1f} %<extra></extra>".replace("%%", "%"),
    ))
    fig.add_vline(x=0, line=dict(color=pal.text_muted, width=1.5))
    fig.add_annotation(x=0, y=1, yref="paper", text="Level with petrol", showarrow=False,
                       xanchor="right", xshift=-6, yanchor="bottom",
                       font=dict(color=pal.text_muted, size=12))
    style_axes(fig, pal, x_title="Full hybrid CO₂ compared with petrol (%)")
    low = min([*free.values(), *lossy.values()])
    high = max([*free.values(), *lossy.values()])
    pad = max((high - low) * 0.35, 11.0)
    fig.update_xaxes(range=[low - pad, max(high, 0.0) + pad], ticksuffix=" %", zeroline=False)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=pal.text_primary, size=13))
    fig.update_layout(height=300, margin=dict(l=8, r=24, t=40, b=12))
    return fig


def size_heatmap(frame: pd.DataFrame, pal: Palette, show_scale: bool = True) -> go.Figure:
    """One powertrain on one cycle: every size, as % above the best feasible buildable one."""
    selection = best_selection(frame, "co2_eu")
    top_feasible = selection["feasible"]
    top_provisional = selection["provisional"]
    if top_feasible is not None:
        top = top_feasible
        reference_is_provisional = False
    else:
        top = top_provisional
        reference_is_provisional = True

    grid = frame.pivot(index="battery_kwh", columns="motor_kw", values="co2_eu")
    allowed = frame.pivot(index="battery_kwh", columns="motor_kw", values="buildable")
    short_steps_grid = frame.pivot(index="battery_kwh", columns="motor_kw", values="short_steps")
    short_kw_grid = frame.pivot(index="battery_kwh", columns="motor_kw", values="short_kw")
    co2 = grid.where(allowed.astype(bool))
    above = (co2 / top["co2_eu"] - 1) * 100

    # Indexed cells: numeric-looking category labels get read as positions by the annotations.
    motors, batteries = list(grid.columns), list(grid.index)
    x, y = list(range(len(motors))), list(range(len(batteries)))
    custom = []
    for b in batteries:
        row_data = []
        for m in motors:
            val = co2.loc[b, m]
            steps = short_steps_grid.loc[b, m]
            kw = short_kw_grid.loc[b, m]
            if pd.isna(val):
                status = "Outside C-rate limit"
            elif int(steps) > 0:
                status = f"{PROVISIONAL_LABEL} ({int(steps)} steps, ≤ {float(kw):.1f} kW)"
            else:
                status = "Passes engine check"
            row_data.append([val, status])
        custom.append(row_data)

    fig = go.Figure(go.Heatmap(
        z=above.values, x=x, y=y, customdata=custom, zmin=0, zmax=HEAT_MAX_PCT,
        colorscale=_RAMP, xgap=2, ygap=2, hoverongaps=False, showscale=show_scale,
        colorbar=dict(title=dict(text="% above best", font=dict(size=12, color=pal.text_muted)),
                      ticksuffix=" %", thickness=10, len=0.8, outlinewidth=0,
                      tickfont=dict(color=pal.text_muted, size=12)),
        text=[[f"{b:g} kWh, {m:g} kW" for m in motors] for b in batteries],
        hovertemplate="%{text}<br>%{customdata[0]:.1f} g CO₂/km"
                      "<br>%{z:.1f} % above best<br>%{customdata[1]}<extra></extra>",
    ))

    # Overlay hollow markers on any buildable cell where the engine falls short of the trace.
    infeasible = frame[frame["buildable"] & (frame["short_steps"] > 0)]
    if not infeasible.empty:
        fig.add_trace(go.Scatter(
            x=[motors.index(m) for m in infeasible["motor_kw"]],
            y=[batteries.index(b) for b in infeasible["battery_kwh"]],
            mode="markers",
            name=PROVISIONAL_LABEL,
            marker=dict(size=12, symbol="x-open", color=pal.text_primary, line=dict(width=2)),
            customdata=infeasible[["battery_kwh", "motor_kw", "co2_eu", "short_steps", "short_kw"]].to_numpy(),
            hovertemplate="%{customdata[0]:g} kWh, %{customdata[1]:g} kW"
                          "<br>%{customdata[2]:.1f} g CO₂/km"
                          f"<br>{PROVISIONAL_LABEL}"
                          "<br>Short steps: %{customdata[3]:.0f}, ≤ %{customdata[4]:.1f} kW<extra></extra>",
        ))

    best_x, best_y = motors.index(top["motor_kw"]), batteries.index(top["battery_kwh"])
    fig.add_trace(go.Scatter(
        x=[best_x], y=[best_y], mode="markers",
        marker=dict(
            size=15,
            symbol="diamond-open" if reference_is_provisional else "circle-open",
            color="#0b0b0b",
            line=dict(width=3),
        ),
        showlegend=False, hoverinfo="skip",
    ))
    if reference_is_provisional:
        best_text = (
            f"<b>Lowest (provisional): {top['battery_kwh']:g} kWh, {top['motor_kw']:g} kW</b>"
            f"<br>{top['co2_eu']:.0f} g/km · no feasible size"
            f"<br>{PROVISIONAL_LABEL} ({int(top['short_steps'])} steps, ≤ {top['short_kw']:.1f} kW)"
        )
    else:
        best_text = (
            f"<b>Best: {top['battery_kwh']:g} kWh, {top['motor_kw']:g} kW</b>"
            f"<br>{top['co2_eu']:.0f} g/km"
        )
    fig.add_annotation(
        x=best_x, y=best_y, ax=-58 if best_x > len(x) / 2 else 58, ay=-48,
        text=best_text,
        arrowcolor=pal.text_primary, arrowhead=0, bgcolor=pal.surface, borderpad=4,
        font=dict(color=pal.text_primary, size=12), align="left",
    )
    if not reference_is_provisional and top_provisional is not None:
        px, py = motors.index(top_provisional["motor_kw"]), batteries.index(top_provisional["battery_kwh"])
        fig.add_annotation(
            x=px, y=py, ax=-58 if px > len(x) / 2 else 58, ay=44,
            text=(
                f"<b>Lowest (provisional): {top_provisional['battery_kwh']:g} kWh, "
                f"{top_provisional['motor_kw']:g} kW</b>"
                f"<br>{top_provisional['co2_eu']:.0f} g/km ({PROVISIONAL_LABEL})"
            ),
            arrowcolor=pal.text_muted, arrowhead=0, bgcolor=pal.surface, borderpad=4,
            font=dict(color=pal.text_secondary, size=11), align="left",
        )

    if len(x) >= 2 and not allowed.astype(bool).all().all():
        fig.add_annotation(x=x[-2], y=0.5, text="Battery can't<br>supply this power",
                           showarrow=False, font=dict(color=pal.text_muted, size=12))
    style_axes(fig, pal, x_title="Motor (kW)", y_title="Battery (kWh)")
    fig.update_xaxes(tickvals=x, ticktext=[f"{m:g}" for m in motors], showgrid=False,
                     showline=False, range=[-0.5, len(x) - 0.5], constrain="domain")
    fig.update_yaxes(tickvals=y, ticktext=[f"{b:g}" for b in batteries], showgrid=False,
                     showline=False, range=[-0.5, len(y) - 0.5])
    fig.update_layout(height=430)
    return fig


def _phev_customdata(points: pd.DataFrame) -> list[list[object]]:
    return [
        [
            row.motor_kw,
            int(row.short_steps),
            row.short_kw,
            PROVISIONAL_LABEL if row.provisional else "Passes engine check",
        ]
        for row in points.itertuples()
    ]


def phev_lines(
    eu: pd.DataFrame,
    fr: pd.DataFrame,
    ymax: float,
    note: tuple[float, str] | None,
    pal: Palette,
    *,
    eu_feasible: pd.DataFrame | None = None,
    fr_feasible: pd.DataFrame | None = None,
) -> go.Figure:
    """CO2 against battery size on both grids, marking infeasible points hollow and dashed."""
    fig = go.Figure()
    phev_colour = _phev(pal)
    specs = (
        (eu, eu_feasible, "EU grid, 250 g/kWh", "solid", "dash", pal.text_primary, 3),
        (fr, fr_feasible, "French grid, 73 g/kWh", "longdash", "dot", pal.text_secondary, 2),
    )
    eu_feas_resolved = eu[~eu["provisional"]] if eu_feasible is None else eu_feasible

    for all_df, feas_override, name, feas_dash, prov_dash, text_colour, width in specs:
        feas_df = all_df[~all_df["provisional"]] if feas_override is None else feas_override
        prov_df = all_df[all_df["provisional"]]
        hover = (
            f"{name}: %{{y:.1f}} g CO₂/km"
            "<br>Winning motor: %{customdata[0]:g} kW"
            "<br>Short steps: %{customdata[1]:.0f} (≤ %{customdata[2]:.1f} kW)"
            "<br>%{customdata[3]}<extra></extra>"
        )
        if not feas_df.empty:
            fig.add_trace(go.Scatter(
                x=feas_df["battery_kwh"], y=feas_df["co2"], name=name, mode="lines+markers",
                legendgroup=name,
                line=dict(color=phev_colour, width=width, dash=feas_dash),
                marker=dict(size=7, symbol="circle", color=phev_colour),
                customdata=_phev_customdata(feas_df),
                hovertemplate=hover,
            ))
            last = feas_df.iloc[-1]
            fig.add_annotation(
                x=last["battery_kwh"], y=last["co2"], text=f"{last['co2']:.0f}",
                showarrow=False, xanchor="left", xshift=8,
                font=dict(color=text_colour, size=12),
            )
        if not prov_df.empty:
            fig.add_trace(go.Scatter(
                x=prov_df["battery_kwh"], y=prov_df["co2"],
                name=f"{name} ({PROVISIONAL_LABEL})",
                mode="lines+markers",
                # One legend entry per grid, so the two panels' legends match; hollow markers
                # carry the provisional state, as the caption under the chart says.
                legendgroup=name,
                showlegend=feas_df.empty,
                line=dict(color=phev_colour, width=width, dash=prov_dash),
                marker=dict(size=8, symbol="circle-open", color=phev_colour, line=dict(width=2)),
                customdata=_phev_customdata(prov_df),
                hovertemplate=hover,
            ))
            if feas_df.empty:
                last = prov_df.iloc[-1]
                fig.add_annotation(
                    x=last["battery_kwh"], y=last["co2"], text=f"{last['co2']:.0f}*",
                    showarrow=False, xanchor="left", xshift=8,
                    font=dict(color=text_colour, size=12),
                )

    if eu_feas_resolved.empty:
        fig.add_annotation(
            x=0.5, y=0.98, xref="paper", yref="paper",
            text=f"No feasible size in grid — {PROVISIONAL_LABEL}",
            showarrow=False, xanchor="center", yanchor="top",
            bgcolor=pal.surface, borderpad=4,
            font=dict(color=pal.text_secondary, size=11),
        )

    if note:
        at, text = note
        source = eu_feas_resolved if (not eu_feas_resolved.empty and (eu_feas_resolved["battery_kwh"] == at).any()) else eu
        match = source[source["battery_kwh"] == at]
        if not match.empty:
            fig.add_annotation(
                x=at, y=float(match.iloc[0]["co2"]), text=text,
                ax=-60 if at > 15 else 70, ay=-62, arrowhead=0,
                arrowcolor=pal.text_muted, align="left",
                font=dict(color=pal.text_primary, size=12),
            )
    style_axes(fig, pal, x_title="Battery (kWh)", y_title="g CO₂/km")
    fig.update_xaxes(range=[0, 22], showgrid=False, tickvals=[1, 5, 10, 15, 20])
    fig.update_yaxes(range=[0, ymax])
    fig.update_layout(height=390, hovermode="x unified")
    return fig
