"""The interactive Francorchamps map: the lap painted on the real circuit, with a car on it.

Any page showing a single lap calls `lap_section`, so a lap always comes with its corners.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.layout import show_chart
from dashboard.theme import Palette, style_axes
from pwt.trackmap import LANDMARKS, outline, place

#: Metres between steps of a generated lap, and between painted points and animation frames.
STEP_M, PAINT_M, FRAME_M = 5, 20, 60
#: Tall portrait map sized to Spa's ~0.62 width-to-height ratio, with a colourbar strip below.
MAP_HEIGHT = 560
STRIP_HEIGHT = 250
#: Brightened low stops so every step clears 3:1 contrast against both #1a1a19 and #000000.
SEQUENTIAL = [[0.0, "#2874d2"], [0.35, "#4c96ec"], [0.7, "#94c4f7"], [1.0, "#eef5fe"]]
#: Blue coasting or recovering, mid-grey near zero, coral-red pulling hard (all >= 3.9:1).
DIVERGING = [[0.0, "#3a8ce8"], [0.5, "#787872"], [1.0, "#f05a4f"]]
PAINTS = ("Speed", "Power demand", "CO₂ per segment distance", "Altitude", "Battery state of charge")

#: Outward/open-space label anchors around Spa (north up) so text avoids the bright track.
LANDMARK_POSITIONS: dict[str, str] = {
    "La Source": "top right",
    "Eau Rouge": "middle right",
    "Kemmel straight": "middle right",
    "Les Combes": "middle right",
    "Bruxelles": "bottom left",
    "Pouhon": "top right",
    "Fagnes": "bottom center",
    "Stavelot": "bottom left",
    "Blanchimont": "middle left",
    "Bus Stop": "top left",
}
#: Subset shown as static text on narrow (<420 px) frames; all 10 remain on hover.
COMPACT_LANDMARKS = frozenset({
    "La Source", "Eau Rouge", "Les Combes", "Bruxelles", "Stavelot", "Blanchimont", "Bus Stop",
})

_MAP_DOMAIN_Y = (0.15, 1.0)
_DEFAULT_REF_WIDTH = 344.0
_HALO_COLOUR = "#0b0b0c"


def is_lap(cycle: str) -> bool:
    """Whether a cycle drives the circuit; NEDC and WLTC have no place on a map."""
    return cycle.startswith("franco")


def mercator_xy(lat, lon) -> tuple[np.ndarray, np.ndarray]:
    """Normalised Web Mercator coordinates in [0, 1] x [0, 1] (includes the cos(lat) factor)."""
    lon_arr = np.asarray(lon, dtype=float)
    lat_rad = np.deg2rad(np.asarray(lat, dtype=float))
    x = (lon_arr + 180.0) / 360.0
    y = (1.0 - np.arcsinh(np.tan(lat_rad)) / np.pi) / 2.0
    return x, y


def fit_camera(
    track: pd.DataFrame | None = None,
    *,
    width_px: float = _DEFAULT_REF_WIDTH,
    height_px: float = 462.0,
    pad_x: float = 40.0,
    pad_y: float = 34.0,
) -> dict:
    """North-up MapLibre camera fitting the full circuit outline inside `width_px x height_px`."""
    if track is None:
        track = outline()
    x, y = mercator_xy(track["lat"].to_numpy(), track["lon"].to_numpy())
    dx = max(float(np.ptp(x)), 1e-9)
    dy = max(float(np.ptp(y)), 1e-9)
    cx = float((x.min() + x.max()) / 2.0)
    cy = float((y.min() + y.max()) / 2.0)

    avail_w = max(float(width_px) - 2.0 * float(pad_x), 1.0)
    avail_h = max(float(height_px) - 2.0 * float(pad_y), 1.0)
    scale = min(avail_w / dx, avail_h / dy)
    return {
        "center": {
            "lat": float(np.rad2deg(np.arctan(np.sinh(np.pi * (1.0 - 2.0 * cy))))),
            "lon": float(360.0 * cx - 180.0),
        },
        "zoom": float(math.log2(scale / 512.0)),
        "bearing": 0,
        "pitch": 0,
    }


def project_to_pixels(
    lat, lon, camera: dict, width_px: float, height_px: float
) -> tuple[np.ndarray, np.ndarray]:
    """Project lat/lon points to MapLibre screen pixels for a north-up `camera`."""
    scale = 512.0 * (2.0 ** float(camera["zoom"]))
    cx, cy = mercator_xy(camera["center"]["lat"], camera["center"]["lon"])
    x, y = mercator_xy(lat, lon)
    px = float(width_px) / 2.0 + (x - cx) * scale
    py = float(height_px) / 2.0 + (y - cy) * scale
    return px, py


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


def metrics(
    steps: pd.DataFrame, *, source: str = "model"
) -> dict[str, tuple[pd.Series, str, bool]]:
    """Choice -> (value per step, unit, diverging around zero), for the columns this run has.

    With `source="workbook"`, every series uses the workbook's exact column and unit with no
    unit conversion or derived g/km calculation. With `source="model"`, derived display units
    (kW, g/km, %) are offered for model output.
    """
    if source not in ("workbook", "model"):
        raise ValueError(f"Unknown source {source!r}; expected 'workbook' or 'model'")

    def has(column: str) -> bool:
        return column in steps and steps[column].notna().any()

    out: dict[str, tuple[pd.Series, str, bool]] = {}
    if has("speed_kph"):
        out["Speed"] = (steps["speed_kph"], "km/h", False)

    if source == "workbook":
        if has("engine_power_drivetrain_w"):
            out["Power demand"] = (steps["engine_power_drivetrain_w"], "W", True)
        if has("emission_g_co2"):
            out["CO₂ emitted"] = (steps["emission_g_co2"], "g", False)
        elif has("co2_g"):
            out["CO₂ from the grid"] = (
                steps["co2_g"], "g", bool((steps["co2_g"].dropna() < 0).any())
            )
        if has("altitude_m"):
            out["Altitude"] = (steps["altitude_m"], "m", False)
        if has("batt_soc"):
            out["Battery state of charge"] = (steps["batt_soc"], "fraction", False)
        return out

    if has("engine_power_drivetrain_w"):
        out["Power demand"] = (steps["engine_power_drivetrain_w"] / 1000.0, "kW", True)
    if has("emission_g_co2") and has("delta_distance_m"):
        per_km = (
            steps["emission_g_co2"]
            / steps["delta_distance_m"].where(lambda d: d > 0)
            * 1000.0
        ).fillna(0.0).clip(lower=0)
        out["CO₂ per segment distance"] = (per_km, "g CO₂/km", False)
    if has("altitude_m"):
        out["Altitude"] = (steps["altitude_m"], "m", False)
    if has("batt_soc"):
        out["Battery state of charge"] = (steps["batt_soc"] * 100.0, "%", False)
    return out


def _fmt_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "—"
    if unit == "fraction":
        return f"{value:.3f}"
    if unit == "W":
        return f"{value:,.0f}"
    if unit in ("km/h", "m"):
        return f"{value:.0f}"
    return f"{value:.1f}"


def _nearest_landmark(distance_m: float) -> str:
    return min(LANDMARKS.items(), key=lambda item: abs(item[0] - distance_m))[1]


def _car_label(row: pd.Series, metric_label: str = "", value: float | None = None,
               unit: str = "") -> str:
    parts = [f"{float(row['distance_m']) / 1000.0:.2f} km"]
    if "time_s" in row and pd.notna(row["time_s"]):
        parts.append(f"{float(row['time_s']):.0f} s")
    parts.append(f"{float(row['speed_kph']):.0f} km/h")
    if metric_label and metric_label != "Speed" and value is not None and pd.notna(value):
        parts.append(f"{metric_label}: {_fmt_value(float(value), unit)} {unit}".strip())
    return "  ·  ".join(parts)


def _frame_indices(steps: pd.DataFrame) -> list[int]:
    """Row indices visited by playback; always includes the start and exact final step."""
    n = len(steps)
    if n <= 1:
        return [0] if n == 1 else []
    if n <= 150:
        return list(range(n))
    stride = max(1, FRAME_M // STEP_M)
    indices = list(range(0, n, stride))
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return indices


def _color_limits(values: pd.Series, diverging: bool) -> tuple[float | None, float | None]:
    clean = values.dropna()
    if clean.empty:
        return None, None
    if diverging:
        # Scale to the drive side: braking peaks are much larger and would wash it out.
        pos = clean.clip(lower=0)
        limit = float(pos.quantile(0.99)) if (pos > 0).any() else float(clean.abs().quantile(0.99))
        limit = limit if limit > 0 else 1.0
        return -limit, limit
    lo, hi = float(clean.min()), float(clean.max())
    if lo == hi:
        return lo - 1.0, hi + 1.0
    return lo, hi


def _is_dark(pal: Palette) -> bool:
    h = pal.surface.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 0.5


def _add_landmark_traces(
    fig: go.Figure,
    camera: dict,
    *,
    compact: bool,
    dark: bool,
) -> None:
    distances = np.array(list(LANDMARKS), dtype=float)
    names = list(LANDMARKS.values())
    near_lat, near_lon = place(distances)

    halo = _HALO_COLOUR if dark else "#ffffff"
    fg = "#ffffff" if dark else "#111111"

    # Outer halo dots + inner landmark dots (all 10 corners carry hover tooltips).
    fig.add_trace(go.Scattermap(
        lat=near_lat, lon=near_lon, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=9, color=halo),
    ))
    fig.add_trace(go.Scattermap(
        lat=near_lat, lon=near_lon, mode="markers", showlegend=False,
        marker=dict(size=5, color=fg),
        customdata=np.column_stack([names, distances / 1000.0]),
        hovertemplate="%{customdata[0]} (%{customdata[1]:.2f} km)<extra></extra>",
    ))

    # Group visible text labels by anchor side; add a 4-direction 1.3 px dark halo behind them.
    scale = 512.0 * (2.0 ** float(camera["zoom"]))
    deg_lon = 1.3 * 360.0 / scale
    deg_lat = deg_lon * math.cos(math.radians(float(camera["center"]["lat"])))
    halo_offsets = ((deg_lat, 0.0), (-deg_lat, 0.0), (0.0, deg_lon), (0.0, -deg_lon))

    visible = COMPACT_LANDMARKS if compact else set(names)
    by_pos: dict[str, list[tuple[float, float, str]]] = {}
    for lat_i, lon_i, name in zip(near_lat, near_lon, names):
        if name not in visible:
            continue
        pos = LANDMARK_POSITIONS.get(name, "middle right")
        by_pos.setdefault(pos, []).append((float(lat_i), float(lon_i), name))

    for pos, items in by_pos.items():
        lats = np.array([it[0] for it in items], dtype=float)
        lons = np.array([it[1] for it in items], dtype=float)
        texts = [it[2] for it in items]
        halo_lats = np.concatenate([lats + dlat for dlat, _ in halo_offsets])
        halo_lons = np.concatenate([lons + dlon for _, dlon in halo_offsets])
        halo_texts = texts * len(halo_offsets)
        fig.add_trace(go.Scattermap(
            lat=halo_lats, lon=halo_lons, mode="markers+text", text=halo_texts,
            marker=dict(size=1, opacity=0), textposition=pos,
            textfont=dict(color=halo, size=12), hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scattermap(
            lat=lats, lon=lons, mode="markers+text", text=texts,
            marker=dict(size=1, opacity=0), textposition=pos,
            textfont=dict(color=fg, size=12), hoverinfo="skip", showlegend=False,
        ))


def lap_map(
    steps: pd.DataFrame,
    values: pd.Series,
    label: str,
    unit: str,
    diverging: bool,
    pal: Palette,
    *,
    source: str = "model",
    car_index: int = 0,
    width_px: int | None = None,
    height_px: int = MAP_HEIGHT,
    uirevision: str | None = None,
) -> go.Figure:
    """`values`, one per step of `steps`, painted along the real Spa circuit (north up).

    The camera is fitted to the full circuit outline with padding so La Source and Bruxelles
    are never cropped. Playback controls live outside the figure as native Streamlit widgets,
    and the colourbar sits horizontally below the map canvas.
    """
    track = outline()
    dark = _is_dark(pal)
    car_idx = max(0, min(int(car_index), len(steps) - 1))

    # Build a smooth 5 m ribbon for visual continuity along the real outline.
    display = resample(steps.assign(_painted=values.to_numpy(dtype=float)))
    interpolated = len(display) != len(steps)
    every = max(1, PAINT_M // STEP_M)
    ribbon = display.iloc[::every]
    all_lat, all_lon = place(display["distance_m"].to_numpy())
    rib_lat, rib_lon = all_lat[::every], all_lon[::every]
    rib_vals = ribbon["_painted"]

    cmin, cmax = _color_limits(values, diverging)
    colorscale = DIVERGING if diverging else SEQUENTIAL

    # Map canvas geometry & Web Mercator camera fit.
    margin_l, margin_r, margin_t, margin_b = 4, 4, 8, 8
    plot_h = float(height_px - margin_t - margin_b)
    map_h = plot_h * (_MAP_DOMAIN_Y[1] - _MAP_DOMAIN_Y[0])
    map_w = float(width_px - margin_l - margin_r) if width_px is not None else _DEFAULT_REF_WIDTH
    # Leave room on the right for "Les Combes" and at the bottom for "Bruxelles" + attribution.
    pad_x = 68.0 if map_w < 420 else 56.0
    pad_y = 40.0
    camera = fit_camera(track, width_px=map_w, height_px=map_h, pad_x=pad_x, pad_y=pad_y)

    colorbar = dict(
        orientation="h",
        title=dict(text=f"{label} ({unit})", side="top",
                   font=dict(color=pal.text_secondary, size=12)),
        thickness=10,
        len=0.78,
        x=0.5,
        xanchor="center",
        y=0.11,
        yanchor="top",
        outlinewidth=0,
        bgcolor="rgba(0,0,0,0)",
        tickfont=dict(color=pal.text_muted, size=12),
    )

    fig = go.Figure()

    # 1. Dark casing along the full circuit outline.
    fig.add_trace(go.Scattermap(
        lat=all_lat, lon=all_lon, mode="lines", hoverinfo="skip", showlegend=False,
        line=dict(color="#000000", width=10),
    ))

    # 2. Painted track ribbon. On workbook laps (or any interpolated lap), hover is disabled on
    #    interpolated points so tooltips never fabricate observations between reported steps.
    ribbon_is_reported = (source == "model") and not interpolated
    ribbon_kwargs: dict = {}
    if ribbon_is_reported:
        ribbon_kwargs["customdata"] = np.column_stack([
            ribbon["distance_m"].to_numpy() / 1000.0,
            ribbon["speed_kph"].to_numpy(),
            [_fmt_value(v, unit) for v in rib_vals],
        ])
        if label == "Speed":
            ribbon_kwargs["hovertemplate"] = (
                "%{customdata[0]:.2f} km · Speed %{customdata[1]:.0f} km/h<extra></extra>"
            )
        else:
            ribbon_kwargs["hovertemplate"] = (
                "%{customdata[0]:.2f} km · Speed %{customdata[1]:.0f} km/h"
                f"<br>{label}: %{{customdata[2]}} {unit}<extra></extra>"
            )
    else:
        ribbon_kwargs["hoverinfo"] = "skip"

    fig.add_trace(go.Scattermap(
        lat=rib_lat, lon=rib_lon, mode="markers", showlegend=False,
        marker=dict(
            size=7, color=rib_vals, colorscale=colorscale, cmin=cmin, cmax=cmax,
            colorbar=colorbar,
        ),
        **ribbon_kwargs,
    ))

    # 3. Exact reported segment-end markers for workbook laps (or sparse model cycles).
    if not ribbon_is_reported:
        step_lat, step_lon = place(steps["distance_m"].to_numpy())
        step_nums = (
            steps["step"].to_numpy() if "step" in steps.columns
            else np.arange(1, len(steps) + 1)
        )
        custom = np.column_stack([
            steps["distance_m"].to_numpy(),
            steps["speed_kph"].to_numpy(),
            [_fmt_value(v, unit) for v in values],
            step_nums,
        ])
        step_hover = (
            "Step %{customdata[3]:.0f} · %{customdata[0]:.0f} m · Speed %{customdata[1]:.0f} km/h<extra></extra>"
            if label == "Speed"
            else (
                "Step %{customdata[3]:.0f} · %{customdata[0]:.0f} m · Speed %{customdata[1]:.0f} km/h"
                f"<br>{label}: %{{customdata[2]}} {unit}<extra></extra>"
            )
        )
        fig.add_trace(go.Scattermap(
            lat=step_lat, lon=step_lon, mode="markers", showlegend=False,
            marker=dict(
                size=10, color=values, colorscale=colorscale, cmin=cmin, cmax=cmax,
                showscale=False,
            ),
            customdata=custom,
            hovertemplate=step_hover,
        ))

    # 4. Corner landmarks with dark halo behind white labels.
    _add_landmark_traces(fig, camera, compact=(width_px is not None and width_px < 420), dark=dark)

    # 5. Car position marker with high-contrast dark halo + bright fill + dark centre dot.
    car_dist = float(steps["distance_m"].iloc[car_idx])
    car_lat, car_lon = place(np.array([car_dist], dtype=float))
    fig.add_trace(go.Scattermap(
        lat=car_lat, lon=car_lon, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=22, color=_HALO_COLOUR),
    ))
    fig.add_trace(go.Scattermap(
        lat=car_lat, lon=car_lon, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=13, color="#ffffff"),
    ))
    fig.add_trace(go.Scattermap(
        lat=car_lat, lon=car_lon, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=5, color="#1a1a19"),
    ))

    layout_kwargs: dict = dict(
        template="none",
        map=dict(
            style="carto-darkmatter" if dark else "carto-positron",
            domain=dict(x=[0.0, 1.0], y=list(_MAP_DOMAIN_Y)),
            **camera,
        ),
        height=height_px,
        margin=dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=pal.text_secondary, size=12),
        hoverlabel=dict(font_size=12),
        showlegend=False,
    )
    if width_px is not None:
        layout_kwargs["width"] = width_px
        layout_kwargs["autosize"] = False
    if uirevision is not None:
        layout_kwargs["uirevision"] = uirevision
    fig.update_layout(**layout_kwargs)
    return fig


def metric_strip(
    steps: pd.DataFrame,
    values: pd.Series,
    label: str,
    unit: str,
    diverging: bool,
    pal: Palette,
    *,
    car_index: int = 0,
    source: str = "model",
    colour: str | None = None,
) -> go.Figure:
    """Plot the selected painted measure along lap distance with a synced car cursor.

    `colour` is the car's colour; without one the line is neutral ink.
    """
    line_colour = colour or pal.text_secondary
    car_idx = max(0, min(int(car_index), len(steps) - 1))
    dist_km = steps["distance_m"].to_numpy(dtype=float) / 1000.0
    y_arr = values.to_numpy(dtype=float)
    car_km = float(dist_km[car_idx])
    car_val = float(y_arr[car_idx]) if pd.notna(y_arr[car_idx]) else 0.0

    fig = go.Figure()
    mode = "lines+markers" if len(steps) <= 200 else "lines"
    formatted = [_fmt_value(v, unit) for v in y_arr]
    fig.add_trace(go.Scatter(
        x=dist_km,
        y=y_arr,
        mode=mode,
        showlegend=False,
        line=dict(color=line_colour, width=2),
        marker=dict(size=6, color=line_colour, line=dict(color=pal.surface, width=1.5)),
        customdata=formatted,
        hovertemplate=f"%{{x:.2f}} km<br>{label}: %{{customdata}} {unit}<extra></extra>",
    ))

    if diverging:
        fig.add_hline(y=0, line=dict(color=pal.axis, width=1, dash="dot"), layer="below")

    max_km = float(dist_km[-1]) if len(dist_km) else 7.0
    for at in LANDMARKS:
        if at <= max_km * 1000.0:
            fig.add_vline(x=at / 1000.0, line=dict(color=pal.grid, width=1, dash="dot"),
                          layer="below")

    clean = values.dropna()
    if clean.empty:
        y_lo, y_hi = 0.0, 1.0
    else:
        y_min, y_max = float(clean.min()), float(clean.max())
        pad = max((y_max - y_min) * 0.12, 1e-3)
        y_lo = min(0.0, y_min - pad) if not diverging and y_min >= 0 and label != "Altitude" else y_min - pad
        y_hi = y_max + pad

    # Vertical cursor line and active point marker synced with the car dot on the map.
    fig.add_trace(go.Scatter(
        x=[car_km, car_km], y=[y_lo, y_hi], mode="lines", hoverinfo="skip", showlegend=False,
        line=dict(color=pal.text_primary, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=[car_km], y=[car_val], mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=10, color=pal.text_primary, line=dict(color=pal.surface, width=2)),
    ))

    style_axes(fig, pal, x_title="Lap distance (km)", y_title=f"{label} ({unit})")
    fig.update_layout(height=STRIP_HEIGHT, showlegend=False, margin=dict(l=8, r=8, t=12, b=8))
    fig.update_xaxes(range=[0.0, max_km], dtick=1)
    fig.update_yaxes(range=[y_lo, y_hi])
    return fig


def mark_corners(fig: go.Figure, trace: pd.DataFrame, x_column: str, pal: Palette,
                 labels: bool = True) -> None:
    """Draw the circuit's corners on a chart of one lap, whichever axis it is plotted against.

    Names sit above the plot area, on two staggered rows so neighbours do not collide, rather
    than across the line they annotate.
    """
    for i, (at, name) in enumerate(LANDMARKS.items()):
        x = float(np.interp(at, trace["distance_m"], trace[x_column]))
        fig.add_vline(x=x, line=dict(color=pal.axis, width=1, dash="dot"), layer="below")
        if labels:
            fig.add_annotation(x=x, y=1, xref="x", yref="paper", text=name, showarrow=False,
                               xanchor="center", yanchor="bottom", yshift=2 + 14 * (i % 2),
                               font=dict(color=pal.text_muted, size=11))
    if labels:
        # A top legend would print on the two label rows, so lift it above them.
        shows_legend = fig.layout.showlegend is True or (
            fig.layout.showlegend is None and sum(t.showlegend is not False for t in fig.data) > 1
        )
        top = 76 if shows_legend else 44
        fig.update_layout(margin=dict(t=max(fig.layout.margin.t or 0, top)))
        if shows_legend:
            fig.update_layout(legend=dict(orientation="h", y=1.16, yanchor="bottom",
                                          x=0, xanchor="left"))


def lap_section(
    laps: dict[str, pd.DataFrame],
    key: str,
    pal: Palette,
    paint: str = "Speed",
    *,
    source: str = "workbook",
    colour: str | None = None,
) -> tuple[pd.Series, str] | None:
    """The map for one lap, with native keyboard-accessible playback and a painted-metric strip.

    `laps` maps a run's name to its steps; more than one adds a picker. Returns the painted
    values, one per step of the chosen lap, and their unit.

    Defaults to `source="workbook"` so workbook pages show only reported values and units;
    model pages pass `source="model"` for derived measures labelled as model output.
    """
    if not laps:
        return None

    run_names = list(laps)
    name = run_names[0]
    if len(run_names) > 1:
        run_key = f"{key}_run"
        if run_key not in st.session_state or st.session_state[run_key] not in laps:
            st.session_state[run_key] = name
        name = st.segmented_control("Run", run_names, key=run_key) or name

    steps = laps[name]
    choices = metrics(steps, source=source)
    options = list(choices)
    default_paint = paint if paint in choices else options[0]
    paint_key = f"{key}_paint"
    if paint_key not in st.session_state or st.session_state[paint_key] not in choices:
        st.session_state[paint_key] = default_paint
    metric = st.segmented_control("Map colour", options, key=paint_key) or default_paint
    values, unit, diverging = choices[metric]

    frame_ids = _frame_indices(steps)
    max_frame = max(0, len(frame_ids) - 1)
    play_key = f"{key}_playing"
    pos_key = f"{key}_frame"
    reset_key = f"{key}_reset_count"
    if play_key not in st.session_state:
        st.session_state[play_key] = False
    if pos_key not in st.session_state or st.session_state[pos_key] > max_frame:
        st.session_state[pos_key] = 0
    if reset_key not in st.session_state:
        st.session_state[reset_key] = 0

    def _render_player() -> None:
        if st.session_state[play_key]:
            nxt = st.session_state[pos_key] + 1
            if nxt > max_frame:
                st.session_state[pos_key] = max_frame
                st.session_state[play_key] = False
            else:
                st.session_state[pos_key] = nxt

        frame_pos = min(int(st.session_state[pos_key]), max_frame)
        car_idx = frame_ids[frame_pos]
        row = steps.iloc[car_idx]
        cur_val = float(values.iloc[car_idx]) if pd.notna(values.iloc[car_idx]) else None
        corner = _nearest_landmark(float(row["distance_m"]))

        # Tall portrait map on the left; readout, playback controls and painted strip on the right.
        map_col, ctrl_col = st.columns([5, 6], gap="large")

        with ctrl_col:
            scope = (
                "Model output — computed along the lap."
                if source == "model"
                else "Workbook figures as reported — exact values at segment ends."
            )
            st.caption(scope)
            st.markdown(f"**{_car_label(row, metric, cur_val, unit)}** · near *{corner}*")

            btn_play, btn_reset = st.columns([1, 1])
            toggle_label = "❚❚ Pause" if st.session_state[play_key] else "▶ Play"
            if btn_play.button(toggle_label, key=f"{key}_play_btn", width="stretch"):
                if not st.session_state[play_key] and st.session_state[pos_key] >= max_frame:
                    st.session_state[pos_key] = 0
                st.session_state[play_key] = not st.session_state[play_key]
                st.rerun()
            if btn_reset.button("↺ Reset view & lap", key=f"{key}_reset_btn", width="stretch"):
                st.session_state[play_key] = False
                st.session_state[pos_key] = 0
                st.session_state[reset_key] += 1
                st.rerun()

            if max_frame > 0:
                chosen_pos = st.slider(
                    "Lap position (distance-based)",
                    min_value=0,
                    max_value=max_frame,
                    key=pos_key,
                    format="%d",
                    help="Use arrow keys or drag to move the car along the lap.",
                )
                car_idx = frame_ids[min(int(chosen_pos), max_frame)]

            strip_fig = metric_strip(
                steps, values, metric, unit, diverging, pal, car_index=car_idx, source=source,
                colour=colour,
            )
            show_chart(strip_fig, key=f"{key}_strip")

        with map_col:
            map_fig = lap_map(
                steps, values, metric, unit, diverging, pal,
                source=source,
                car_index=car_idx,
                uirevision=f"{key}_{name}_{st.session_state[reset_key]}",
            )
            show_chart(map_fig, scroll_zoom=True, key=f"{key}_map")

    run_every = 0.25 if st.session_state[play_key] else None
    st.fragment(run_every=run_every)(_render_player)()

    if source == "workbook":
        st.caption(
            f"This workbook has {len(steps)} reported steps. The map interpolates visually "
            "between recorded points; hover and the chart show reported values at segment ends."
        )
    if source == "model" and metric == "CO₂ per segment distance":
        st.caption(
            "Model output — CO₂ per segment distance (g CO₂/km). "
            "End-of-lap battery accounting is excluded."
        )
    st.caption(
        "Map positions and landmark markers are approximate. Circuit outline: "
        "[bacinger/f1-circuits](https://github.com/bacinger/f1-circuits) (MIT licence). "
        "Map tiles © OpenStreetMap contributors, © CARTO."
    )
    return values, unit
