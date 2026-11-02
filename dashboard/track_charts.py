"""The interactive Francorchamps map: the lap painted on the real circuit, with a car on it.

Any page showing a single lap calls `lap_section`, so a lap always comes with its corners.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.theme import Palette
from pwt.trackmap import LANDMARKS, place

#: Metres between steps of a generated lap, and between painted points and animation frames.
STEP_M, PAINT_M, FRAME_M = 5, 20, 60
SEQUENTIAL = [[0.0, "#104281"], [0.35, "#2a78d6"], [0.7, "#86b6ef"], [1.0, "#e6f0fc"]]
#: Blue coasting or recovering, grey near zero, red pulling hard.
DIVERGING = [[0.0, "#2a78d6"], [0.5, "#383835"], [1.0, "#e0483d"]]
PAINTS = ("Speed", "Power demand", "CO₂ emitted here", "Altitude", "Battery charge")


def is_lap(cycle: str) -> bool:
    """Whether a cycle drives the circuit; NEDC and WLTC have no place on a map."""
    return cycle.startswith("franco")


def resample(steps: pd.DataFrame) -> pd.DataFrame:
    """A lap on a 5 m grid, for display only. Generated laps are on it already."""
    numeric = steps.select_dtypes("number")
    if numeric["distance_m"].diff().median() <= STEP_M:
        return numeric
    grid = np.arange(0.0, float(numeric["distance_m"].iloc[-1]) + STEP_M, STEP_M)
    known = numeric.dropna(axis=1, how="all")
    return pd.DataFrame(
        {c: np.interp(grid, known["distance_m"], known[c]) for c in known} | {"distance_m": grid}
    )


def metrics(steps: pd.DataFrame) -> dict[str, tuple[pd.Series, str, bool]]:
    """Choice → (value per step, unit, diverging around zero), for the columns this run has."""

    def has(column: str) -> bool:
        return column in steps and steps[column].notna().any()

    out = {"Speed": (steps["speed_kph"], "km/h", False)}
    if has("engine_power_drivetrain_w"):
        out["Power demand"] = (steps["engine_power_drivetrain_w"] / 1000, "kW", True)
    if has("emission_g_co2"):
        per_km = (steps["emission_g_co2"] / steps["delta_distance_m"].where(lambda d: d > 0) * 1000
                  ).fillna(0.0).clip(lower=0)
        out["CO₂ emitted here"] = (per_km, "g/km", False)
    out["Altitude"] = (steps["altitude_m"], "m", False)
    if has("batt_soc"):
        out["Battery charge"] = (steps["batt_soc"] * 100, "%", False)
    return out


def _car_label(row: pd.Series) -> str:
    # The battery-electric workbooks have no time column.
    parts = [f"{row['distance_m'] / 1000:.2f} km"]
    if "time_s" in row:
        parts.append(f"{row['time_s']:.0f} s")
    return "  ·  ".join([*parts, f"{row['speed_kph']:.0f} km/h"])


def lap_map(steps: pd.DataFrame, values: pd.Series, label: str, unit: str, diverging: bool,
            pal: Palette) -> go.Figure:
    """`values`, one per step of `steps`, painted along the lap; the car plays through it."""
    every = max(1, PAINT_M // STEP_M)
    painted = steps.iloc[::every]
    all_lat, all_lon = place(steps["distance_m"].to_numpy())
    lat, lon = all_lat[::every], all_lon[::every]
    shown = values.iloc[::every]
    # Scaled to the drive side: braking peaks are four times higher and would wash it out.
    limit = float(shown.clip(lower=0).quantile(0.99)) if diverging else None
    near_lat, near_lon = place(np.array(list(LANDMARKS), dtype=float))

    fig = make_subplots(rows=2, cols=1, specs=[[{"type": "map"}], [{"type": "xy"}]],
                        row_heights=[0.8, 0.2], vertical_spacing=0.04)
    on_map = dict(row=1, col=1)
    fig.add_trace(go.Scattermap(
        lat=all_lat, lon=all_lon, mode="lines", hoverinfo="skip", showlegend=False,
        line=dict(color="#000000", width=9),
    ), **on_map)
    fig.add_trace(go.Scattermap(
        lat=lat, lon=lon, mode="markers", showlegend=False,
        marker=dict(
            size=8, color=shown, colorscale=DIVERGING if diverging else SEQUENTIAL,
            cmin=-limit if diverging else None, cmax=limit if diverging else None,
            colorbar=dict(title=dict(text=unit, font=dict(color=pal.text_muted, size=12)),
                          thickness=10, len=0.45, y=0.62, outlinewidth=0, x=0.99, xanchor="right",
                          bgcolor=pal.surface, tickfont=dict(color=pal.text_secondary, size=11)),
        ),
        customdata=pd.DataFrame({
            "km": painted["distance_m"] / 1000, "speed": painted["speed_kph"],
            "value": shown,
        }).to_numpy(),
        hovertemplate=f"%{{customdata[0]:.2f}} km · %{{customdata[1]:.0f}} km/h"
                      f"<br>{label}: %{{customdata[2]:.1f}} {unit}<extra></extra>",
    ), **on_map)
    fig.add_trace(go.Scattermap(
        lat=near_lat, lon=near_lon,
        mode="markers+text", text=list(LANDMARKS.values()), textposition="middle right",
        textfont=dict(color="#ffffff", size=12), hoverinfo="skip", showlegend=False,
        marker=dict(size=5, color="#ffffff"),
    ), **on_map)
    start = steps.iloc[0]
    fig.add_trace(go.Scattermap(
        lat=all_lat[:1], lon=all_lon[:1], mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=17, color="#ffffff"),
    ), **on_map)
    car = len(fig.data) - 1

    # The speed strip: the slider drives its cursor and the car together.
    top = float(steps["speed_kph"].max()) * 1.05
    fig.add_trace(go.Scatter(
        x=steps["distance_m"] / 1000, y=steps["speed_kph"], mode="lines", showlegend=False,
        line=dict(color=pal.text_secondary, width=1.5),
        hovertemplate="%{x:.2f} km · %{y:.0f} km/h<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=[start["distance_m"] / 1000] * 2, y=[0, top], mode="lines", hoverinfo="skip",
        showlegend=False, line=dict(color=pal.text_primary, width=2),
    ), row=2, col=1)
    cursor = len(fig.data) - 1

    stride = max(1, FRAME_M // STEP_M)
    frame_rows = steps.iloc[::stride]
    frames, ticks = [], []
    for i, (row, here_lat, here_lon) in enumerate(zip(frame_rows.itertuples(), all_lat[::stride],
                                                      all_lon[::stride])):
        name = str(i)
        km = row.distance_m / 1000
        frames.append(go.Frame(
            name=name, traces=[car, cursor],
            data=[go.Scattermap(lat=[here_lat], lon=[here_lon]), go.Scatter(x=[km, km], y=[0, top])],
            layout=dict(title_text=_car_label(frame_rows.iloc[i])),
        ))
        whole_km = row.distance_m % 1000 < FRAME_M
        ticks.append(dict(method="animate", label=f"{km:.0f}" if whole_km else "",
                          args=[[name], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                             transition=dict(duration=0))]))
    fig.frames = frames
    centre_lat, centre_lon = float(all_lat.mean()), float(all_lon.mean())
    fig.update_layout(
        map=dict(style="carto-darkmatter", center=dict(lat=centre_lat, lon=centre_lon), zoom=13.2),
        height=800, margin=dict(l=44, r=0, t=38, b=40), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=pal.text_secondary, size=13), hoverlabel=dict(font_size=12),
        title=dict(text=_car_label(start), x=0.01, y=0.98, yanchor="top",
                   font=dict(color=pal.text_primary, size=15)),
        updatemenus=[dict(
            type="buttons", direction="left", x=0.01, y=0.27, xanchor="left", yanchor="bottom",
            bgcolor=pal.surface, font=dict(color=pal.text_primary), showactive=False,
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=110, redraw=True), fromcurrent=True,
                                      mode="immediate", transition=dict(duration=0))]),
                dict(label="❚❚ Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=0, steps=ticks, x=0.2, len=0.72, y=0.27, yanchor="bottom", ticklen=0,
            bgcolor=pal.surface, activebgcolor=pal.text_primary, tickcolor=pal.text_muted,
            font=dict(color=pal.text_muted, size=10), pad=dict(t=0, b=0),
            currentvalue=dict(visible=False),
        )],
    )
    fig.update_xaxes(range=[0, float(steps["distance_m"].iloc[-1]) / 1000], gridcolor=pal.grid,
                     color=pal.text_muted, title=dict(text="Distance (km)", standoff=4))
    fig.update_yaxes(range=[0, top], gridcolor=pal.grid, color=pal.text_muted,
                     title=dict(text="km/h", standoff=4))
    return fig


def mark_corners(fig: go.Figure, trace: pd.DataFrame, x_column: str, pal: Palette,
                 labels: bool = True) -> None:
    """Draw the circuit's corners on a chart of one lap, whichever axis it is plotted against."""
    for at, name in LANDMARKS.items():
        x = float(np.interp(at, trace["distance_m"], trace[x_column]))
        fig.add_vline(x=x, line=dict(color=pal.axis, width=1, dash="dot"), layer="below")
        if labels:
            fig.add_annotation(x=x, y=1, xref="x", yref="paper", text=name, textangle=-90,
                               showarrow=False, xanchor="right", yanchor="top",
                               font=dict(color=pal.text_muted, size=10))


def lap_section(laps: dict[str, pd.DataFrame], key: str, pal: Palette,
                paint: str = "Speed") -> tuple[pd.Series, str] | None:
    """The map for one lap, with its controls; nothing at all when there is no lap to show.

    `laps` maps a run's name to its steps; more than one adds a picker. Returns the painted
    values, one per step of the chosen lap, and their unit.
    """
    if not laps:
        return None
    name = next(iter(laps))
    if len(laps) > 1:
        name = st.segmented_control("Run on the map", list(laps), default=name,
                                    key=f"{key}_run") or name
    steps = laps[name]
    choices = metrics(steps)
    # The options stay the same for every car, so changing car keeps the choice.
    metric = st.segmented_control("Paint the track with", PAINTS, default=paint,
                                  key=f"{key}_paint") or paint
    if metric not in choices:
        st.caption(f"This run has no {metric.lower()} figures, so the map shows speed.")
        metric = "Speed"
    values, unit, diverging = choices[metric]

    shown = resample(steps.assign(painted=values))
    st.plotly_chart(lap_map(shown, shown["painted"], metric, unit, diverging, pal), width="stretch",
                    theme=None, config={"scrollZoom": True}, key=f"{key}_map")
    if len(shown) != len(steps):
        st.caption(f"This lap has {len(steps)} segments; the map interpolates between them to "
                   "draw the whole circuit. Exact figures are at the segment ends.")
    if metric == "CO₂ emitted here":
        st.caption("CO₂ at each point only. It leaves out the electricity a plug-in hybrid "
                   "recharges and the fuel a full hybrid burns to buy back its battery, which the "
                   "lap totals elsewhere include.")
    st.caption("Circuit outline: [bacinger/f1-circuits](https://github.com/bacinger/f1-circuits), "
               "MIT licence. Map tiles © OpenStreetMap contributors, © CARTO. The outline is "
               "coarse and the laps use a single line, so positions are good to about 100 m. "
               "Corner names are placed by hand.")
    return values, unit
