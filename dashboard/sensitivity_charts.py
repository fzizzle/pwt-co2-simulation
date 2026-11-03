"""Interactive Study B views using the same palette and evidence as the report."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import Palette, style_axes
from pwt.sensitivity_reporting import FACTOR_NAMES, near_tie


def leaders(group: pd.DataFrame) -> str:
    if group.empty:
        return "No passing comparison"
    largest = group.swing.max()
    return " ≈ ".join(FACTOR_NAMES[row.factor] for row in group.itertuples()
                      if near_tie(largest, row.swing))


def comparison_table(group: pd.DataFrame) -> pd.DataFrame:
    """Readable numbers retain both endpoint identities and their separate flags."""
    return pd.DataFrame({
        "Factor": group.factor.map(FACTOR_NAMES),
        "Parameter −10% (g CO₂/km)": group.co2_low,
        "Baseline (g CO₂/km)": group.baseline,
        "Parameter +10% (g CO₂/km)": group.co2_high,
        "Span (g/km)": group.swing,
        "Elasticity": group.elasticity,
        "−10% short steps": group.short_steps_low,
        "+10% short steps": group.short_steps_high,
        "Baseline short steps": group.baseline_short_steps,
        "Passes engine check": group.engine_check_pass,
    }).reset_index(drop=True)


def research_table(frame: pd.DataFrame) -> pd.DataFrame:
    from pwt.catalog import POWERTRAIN_NAMES
    from pwt.sweep import CYCLES

    out = frame.copy()
    out["powertrain"] = out.powertrain.map(POWERTRAIN_NAMES)
    out["cycle"] = out.cycle.map(CYCLES)
    for column in ("factor", "second_factor"):
        if column in out:
            out[column] = out[column].map({**FACTOR_NAMES, "baseline": "Baseline"})
    if "experiment" in out:
        out["experiment"] = out.experiment.map({
            "baseline": "Baseline", "body_mass": "Body mass", "total_mass": "Total mass",
            "shape_only": "Engine curve shape only", "workbook_curve": "Complete workbook curve",
        })
    return out.rename(columns={
        "powertrain": "Car", "cycle": "Driving cycle", "factor": "Factor", "scale": "Parameter scale",
        "mass_kg": "Total mass (kg)", "fuel_l_100km": "Fuel (l/100 km)",
        "battery_kwh_100km": "Battery energy (kWh/100 km)", "co2_eu": "EU CO₂ (g/km)",
        "co2_fr": "French CO₂ (g/km)", "short_steps": "Short steps", "short_kw": "Worst shortfall (kW)",
        "lap_time_s": "Lap time (s)", "experiment": "Experiment", "setting": "Setting / curve",
        "second_factor": "Factor paired with mass", "mass_scale": "Mass scale", "other_scale": "Other factor scale",
        "interaction_g_km": "Interaction (g/km)", "engine_check_pass": "All terms pass engine check",
    })


def tornado(group: pd.DataFrame, powertrain: str, pal: Palette) -> go.Figure:
    """Endpoint span with signed baseline deltas, labels and independent feasibility flags."""
    fig = go.Figure()
    own = group.sort_values("rank")
    labels = own.factor.map(FACTOR_NAMES).tolist()
    colour = pal.for_powertrain(powertrain)
    if own.empty:
        return style_axes(fig, pal, x_title="Change from baseline in CO₂ emissions (g/km)")
    fig.add_bar(
        x=own.swing.tolist(), y=labels, base=own[["delta_low", "delta_high"]].min(axis=1).tolist(),
        orientation="h", width=0.46, name="Endpoint span", showlegend=False,
        marker=dict(color=colour, opacity=0.75,
                    pattern=dict(shape=["" if passed else "/" for passed in own.engine_check_pass])),
        customdata=own[["swing", "elasticity", "engine_check_pass"]].to_numpy(),
        hovertemplate="%{y}<br>Span: %{customdata[0]:.3f} g/km"
                      "<br>Elasticity: %{customdata[1]:.3f}<br>Passes engine check: %{customdata[2]}<extra></extra>",
    )
    for suffix, name, shape, position in (("low", "Parameter −10%", "circle", "top center"),
                                          ("high", "Parameter +10%", "diamond", "bottom center")):
        fig.add_scatter(
            x=own[f"delta_{suffix}"].tolist(), y=labels, mode="markers+text", name=name,
            text=[f"{v:.2f}" for v in own[f"co2_{suffix}"]], textposition=position,
            textfont=dict(color=pal.text_primary, size=12), cliponaxis=False,
            marker=dict(color=colour, size=11, line=dict(color=pal.text_primary, width=1.5),
                        symbol=[shape if steps == 0 else f"{shape}-open"
                                for steps in own[f"short_steps_{suffix}"]]),
            customdata=own[[f"co2_{suffix}", f"short_steps_{suffix}", f"short_kw_{suffix}"]].to_numpy(),
            hovertemplate="%{y}<br>CO₂: %{customdata[0]:.3f} g/km<br>Change: %{x:+.3f} g/km"
                          "<br>Short steps: %{customdata[1]:.0f}<br>Worst shortfall: %{customdata[2]:.2f} kW<extra>%{fullData.name}</extra>",
        )
    bound = max(own[["delta_low", "delta_high"]].abs().to_numpy().max()*1.3, 0.1)
    style_axes(fig, pal, x_title="Change from baseline in CO₂ emissions (g/km)")
    fig.update_layout(height=max(360, len(own)*78), bargap=0.4)
    fig.update_xaxes(range=[-bound, bound])
    fig.update_yaxes(categoryorder="array", categoryarray=labels, autorange="reversed", showgrid=False)
    fig.add_vline(x=0, line_color=pal.text_muted, line_dash="dash", line_width=1)
    return fig
