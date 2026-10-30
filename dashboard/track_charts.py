"""The interactive Francorchamps map: the lap painted on the real circuit, with a car on it."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import Palette
from pwt.trackmap import LANDMARKS, place

#: Metres between painted points and between animation frames.
PAINT_M, FRAME_M = 20, 60
SEQUENTIAL = [[0.0, "#104281"], [0.35, "#2a78d6"], [0.7, "#86b6ef"], [1.0, "#e6f0fc"]]
#: Blue coasting or recovering, grey near zero, red pulling hard.
DIVERGING = [[0.0, "#2a78d6"], [0.5, "#383835"], [1.0, "#e0483d"]]


def _car_label(row: pd.Series) -> str:
    return (f"{row['distance_m'] / 1000:.2f} km  ·  {row['time_s']:.0f} s  ·  "
            f"{row['speed_kph']:.0f} km/h")


def lap_map(steps: pd.DataFrame, values: pd.Series, label: str, unit: str, diverging: bool,
            pal: Palette) -> go.Figure:
    """`values`, one per step of `steps`, painted along the lap; the car plays through it."""
    every = max(1, PAINT_M // 5)
    painted = steps.iloc[::every]
    lat, lon = place(painted["distance_m"].to_numpy())
    shown = values.iloc[::every]
    # Scaled to the drive side: braking peaks are four times higher and would wash it out.
    limit = float(shown.clip(lower=0).quantile(0.99)) if diverging else None
    all_lat, all_lon = place(steps["distance_m"].to_numpy())
    near = {at: place(float(at)) for at in LANDMARKS}

    fig = go.Figure()
    fig.add_trace(go.Scattermap(
        lat=all_lat, lon=all_lon, mode="lines", hoverinfo="skip", showlegend=False,
        line=dict(color="#000000", width=9),
    ))
    fig.add_trace(go.Scattermap(
        lat=lat, lon=lon, mode="markers", showlegend=False,
        marker=dict(
            size=8, color=shown, colorscale=DIVERGING if diverging else SEQUENTIAL,
            cmin=-limit if diverging else None, cmax=limit if diverging else None,
            colorbar=dict(title=dict(text=unit, font=dict(color=pal.text_muted, size=12)),
                          thickness=10, len=0.6, outlinewidth=0, x=0.99, xanchor="right",
                          bgcolor=pal.surface, tickfont=dict(color=pal.text_secondary, size=11)),
        ),
        customdata=pd.DataFrame({
            "km": painted["distance_m"] / 1000, "speed": painted["speed_kph"],
            "value": shown,
        }).to_numpy(),
        hovertemplate=f"%{{customdata[0]:.2f}} km · %{{customdata[1]:.0f}} km/h"
                      f"<br>{label}: %{{customdata[2]:.1f}} {unit}<extra></extra>",
    ))
    fig.add_trace(go.Scattermap(
        lat=[p[0] for p in near.values()], lon=[p[1] for p in near.values()],
        mode="markers+text", text=list(LANDMARKS.values()), textposition="middle right",
        textfont=dict(color="#ffffff", size=12), hoverinfo="skip", showlegend=False,
        marker=dict(size=5, color="#ffffff"),
    ))
    start = steps.iloc[0]
    car_lat, car_lon = place([float(start["distance_m"])])
    fig.add_trace(go.Scattermap(
        lat=car_lat, lon=car_lon, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=17, color="#ffffff"),
    ))
    car = len(fig.data) - 1

    frame_rows = steps.iloc[:: max(1, FRAME_M // 5)]
    frames, ticks = [], []
    for i, row in enumerate(frame_rows.itertuples()):
        here_lat, here_lon = place([float(row.distance_m)])
        name = str(i)
        frames.append(go.Frame(
            name=name, traces=[car],
            data=[go.Scattermap(lat=here_lat, lon=here_lon)],
            layout=dict(title_text=_car_label(frame_rows.iloc[i])),
        ))
        whole_km = row.distance_m % 1000 < FRAME_M
        ticks.append(dict(method="animate", label=f"{row.distance_m / 1000:.0f}" if whole_km else "",
                          args=[[name], dict(mode="immediate", frame=dict(duration=0, redraw=True),
                                             transition=dict(duration=0))]))
    fig.frames = frames
    centre_lat, centre_lon = float(all_lat.mean()), float(all_lon.mean())
    fig.update_layout(
        map=dict(style="carto-darkmatter", center=dict(lat=centre_lat, lon=centre_lon), zoom=13.2),
        height=640, margin=dict(l=0, r=0, t=38, b=0), paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=pal.text_secondary, size=13), hoverlabel=dict(font_size=12),
        title=dict(text=_car_label(start), x=0.01, y=0.98, yanchor="top",
                   font=dict(color=pal.text_primary, size=15)),
        updatemenus=[dict(
            type="buttons", direction="left", x=0.01, y=0.09, xanchor="left", yanchor="bottom",
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
            active=0, steps=ticks, x=0.2, len=0.72, y=0.09, yanchor="bottom", ticklen=0,
            bgcolor=pal.surface, activebgcolor=pal.text_primary, tickcolor=pal.text_muted,
            font=dict(color=pal.text_muted, size=10), pad=dict(t=0, b=0),
            currentvalue=dict(visible=False),
        )],
    )
    return fig
