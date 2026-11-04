"""Study C charts and tables: lap time and CO₂ against grip or spoiler size."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import Palette, style_axes
from pwt.catalog import POWERTRAIN_NAMES

#: variant -> (column holding the setting, axis title, short label)
VARIANTS = {
    "grip": ("grip_factor", "Grip factor (1 = baseline tyres)", "Tyres (grip)"),
    "spoiler": ("scz_m2", "Spoiler downforce area SCz (m²)", "Spoiler (downforce)"),
}
CO2 = {"co2_eu": "EU grid · 250 g CO₂/kWh", "co2_fr": "France grid · 73 g CO₂/kWh"}


def rows_for(results: pd.DataFrame, powertrain: str, variant: str) -> pd.DataFrame:
    """The selected car's rows for one variant, in order of the setting."""
    column = VARIANTS[variant][0]
    chosen = results[(results.powertrain == powertrain) & (results.variant == variant)]
    return chosen.sort_values(column).reset_index(drop=True)


def baseline_row(results: pd.DataFrame, powertrain: str) -> pd.Series:
    """Baseline tyres, no spoiler."""
    rows = results[(results.powertrain == powertrain) & (results.variant == "grip")
                   & (results.grip_factor == 1.0)]
    return rows.iloc[0]


def infeasible(rows: pd.DataFrame) -> pd.Series:
    return rows.short_steps > 0


def line_chart(rows: pd.DataFrame, variant: str, column: str, y_title: str,
               powertrain: str, pal: Palette) -> go.Figure:
    """One measure against the setting. Hollow markers cannot follow the lap (provisional)."""
    x_column, x_title, _ = VARIANTS[variant]
    fig = go.Figure()
    fig.add_scatter(
        x=rows[x_column].tolist(), y=rows[column].tolist(), mode="lines+markers",
        name=POWERTRAIN_NAMES[powertrain], showlegend=False,
        line=dict(color=pal.for_powertrain(powertrain), width=2.5),
        marker=dict(color=pal.for_powertrain(powertrain), size=10,
                    line=dict(color=pal.text_primary, width=1.5),
                    symbol=["circle-open" if short else "circle" for short in infeasible(rows)]),
        customdata=rows[["short_steps", "short_kw"]].to_numpy(),
        hovertemplate="%{x}<br>%{y:.2f}<br>Short steps: %{customdata[0]:.0f}"
                      "<br>Worst shortfall: %{customdata[1]:.2f} kW<extra></extra>",
    )
    style_axes(fig, pal, x_title=x_title, y_title=y_title)
    fig.update_layout(height=340)
    return fig


def comparison_table(rows: pd.DataFrame, variant: str, grid: str) -> pd.DataFrame:
    x_column, x_title, _ = VARIANTS[variant]
    table = pd.DataFrame({
        x_title: rows[x_column],
        "Lap time (s)": rows.lap_time_s,
        f"CO₂, {CO2[grid]} (g CO₂/km)": rows[grid],
        "Total mass (kg)": rows.mass_kg,
        "Short steps": rows.short_steps,
        "Worst shortfall (kW)": rows.short_kw,
        "Provisional": infeasible(rows),
    })
    if variant == "spoiler":
        table.insert(1, "Added drag SCx (m²)", rows.added_scx_m2)
        table.insert(2, "Added mass (kg)", rows.added_kg)
    return table.reset_index(drop=True)
