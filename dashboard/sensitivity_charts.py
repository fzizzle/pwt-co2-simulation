"""Interactive Study B views using the same palette and evidence as the report."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.theme import Palette, style_axes
from pwt.sensitivity_reporting import FACTOR_NAMES, near_tie


def ranking_visual(group: pd.DataFrame, pal: Palette) -> go.Figure:
    """Span badges in report order, preserving anchored ties."""
    own = group.sort_values(['swing', 'factor'], ascending=[False, True])
    labels, anchor, rank = [], None, 0
    for index, row in enumerate(own.itertuples(), 1):
        tied = anchor is not None and near_tie(anchor, row.swing)
        if not tied:
            anchor, rank = row.swing, index
        labels.append(f'{"≈ " if tied else ""}{rank} · {row.swing:.2f} g CO₂/km' +
                      (' †' if not row.engine_check_pass else ''))
    fig = go.Figure(go.Scatter(
        x=own.swing.tolist(), y=own.factor.map(FACTOR_NAMES).tolist(),
        mode='markers+text', text=labels, textposition='middle right',
        marker=dict(size=16, color=[pal.for_powertrain(c) for c in own.powertrain],
                    symbol=['circle' if p else 'circle-open' for p in own.engine_check_pass], line_width=2),
        customdata=['Passes engine check' if p else '† Provisional: baseline or endpoint fails engine check'
                    for p in own.engine_check_pass],
        hovertemplate='%{y}<br>%{text}<br>%{customdata}<extra></extra>', showlegend=False))
    style_axes(fig, pal, x_title='Span (g CO₂/km)')
    fig.update_layout(height=max(240, len(own)*48), margin=dict(r=170))
    fig.update_xaxes(range=[0, max(own.swing.max()*1.4, 0.1)])
    fig.update_yaxes(categoryorder='array', categoryarray=own.factor.map(FACTOR_NAMES).tolist(),
                     autorange='reversed', showgrid=False)
    return fig


def variable_key(selected: pd.DataFrame) -> str:
    """Visible definitions with examples from the selected saved comparison."""
    from pwt.sensitivity import BASE, SCALES
    mass = selected[selected.factor == 'mass'].iloc[0]
    vehicle = BASE[mass.powertrain]
    low, high = SCALES
    step = high-low
    eta = (f'Peak engine efficiency scales eta_max from {vehicle.eta_max:.3f} to '
           f'{vehicle.eta_max*low:.3f} or {vehicle.eta_max*high:.3f}; curve shape stays fixed.'
           if mass.powertrain != 'bev' else 'The battery-electric car has no peak engine efficiency variant.')
    checks = '; '.join(
        f'{FACTOR_NAMES[r.factor]} ({label}): {int(getattr(r, "short_steps_"+suffix))} short steps, '
        f'{getattr(r, "short_kw_"+suffix):.2f} kW'
        for r in selected.itertuples()
        for suffix, label in (('low', 'lower endpoint'), ('high', 'upper endpoint'))
        if getattr(r, 'short_steps_'+suffix) > 0) or 'All selected endpoints pass.'
    return (
        '**Elasticity (no unit)** — % change in CO₂ per 1% change in the parameter: '
        f'`(CO2(+{(high-1)*100:.0f}%) − CO2(−{(1-low)*100:.0f}%)) / ({step:.1f} × baseline)`. '
        'The sign gives the direction. It depends on the sampled step and is not a true derivative. '
        f'Selected car mass example: ({mass.co2_high:.2f} − {mass.co2_low:.2f}) / '
        f'({step:.1f} × {mass.baseline:.2f}) = **{mass.elasticity:.2f}**.\n\n'
        '**Span (g CO₂/km)** — the positive absolute difference between endpoint CO₂ values; '
        f'the bar length. Selected car mass: **{mass.swing:.2f} g CO₂/km**.\n\n'
        '**Engine check** — whether the engine can deliver the power the trace demands at every step. '
        f'Short steps and largest shortfall: {checks}.\n\n'
        '**† (provisional)** — the baseline or an endpoint fails the engine check; its CO₂ is conditional. '
        f'The selected baseline has {int(mass.baseline_short_steps)} short steps.\n\n'
        f'**Parameters:** Car mass changes body mass only (`m_vehicle`) by ±{(high-1)*100:.0f}%; '
        'driver, battery and machine masses stay fixed, so total mass moves by less. '
        'Drag scales the drag coefficient; rolling resistance scales the rolling coefficient; '
        f'gear ratios scale every ratio. {eta}'
    )


def elasticity_panels(ranked: pd.DataFrame, across: str, pal: Palette) -> go.Figure:
    """Full saved grid, independent of the single-comparison selectors."""
    from plotly.subplots import make_subplots
    from pwt.catalog import POWERTRAIN_NAMES
    from pwt.sweep import CYCLES
    if across not in ('cars', 'cycles'):
        raise ValueError('Choose cars or cycles')
    panels, series = (CYCLES, POWERTRAIN_NAMES) if across == 'cars' else (POWERTRAIN_NAMES, CYCLES)
    panel_key, series_key = ('cycle', 'powertrain') if across == 'cars' else ('powertrain', 'cycle')
    fig = make_subplots(rows=2, cols=2, subplot_titles=list(panels.values()),
                        horizontal_spacing=0.20, vertical_spacing=0.18)
    shapes = dict(zip(CYCLES, ('circle', 'square', 'diamond', 'triangle-up')))
    bound = max(float(ranked.elasticity.abs().max())*1.12, 0.1)
    for panel_index, panel in enumerate(panels):
        row, col = divmod(panel_index, 2)
        for key in series:
            own = ranked[(ranked[panel_key] == panel) & (ranked[series_key] == key)]
            custom = [[r.powertrain, r.cycle, r.factor, r.elasticity,
                       POWERTRAIN_NAMES[r.powertrain], CYCLES[r.cycle],
                       '' if r.engine_check_pass else ' (provisional)'] for r in own.itertuples()]
            hover = '%{customdata[4]}<br>%{customdata[5]}<br>%{y}<br>Elasticity: %{customdata[3]:.2f}%{customdata[6]}<extra></extra>'
            if across == 'cars':
                # Grouped bars in a fixed series order: the form the palette is validated for.
                trace = go.Bar(
                    x=own.elasticity.tolist(), y=own.factor.map(FACTOR_NAMES).tolist(), orientation='h',
                    name=series[key], legendgroup=key, showlegend=panel_index == 0, offsetgroup=key,
                    marker=dict(color=pal.for_powertrain(key),
                                pattern=dict(shape=['' if p else '/' for p in own.engine_check_pass])),
                    customdata=custom, hovertemplate=hover)
            else:
                # One car per panel, so one colour; the cycle is told apart by marker shape.
                trace = go.Scatter(
                    x=own.elasticity.tolist(), y=own.factor.map(FACTOR_NAMES).tolist(), mode='markers',
                    name=series[key], legendgroup=key, showlegend=False,
                    marker=dict(color=pal.for_powertrain(panel), size=11, line_width=2,
                                symbol=[shapes[key] if p else f'{shapes[key]}-open' for p in own.engine_check_pass]),
                    customdata=custom, hovertemplate=hover)
            fig.add_trace(trace, row=row+1, col=col+1)
        fig.add_vline(x=0, line_dash='dash', line_color=pal.text_muted, row=row+1, col=col+1)
    if across == 'cycles':
        for key in series:  # legend entries in a neutral tone: shape is the key, colour is the car
            fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', name=series[key], legendgroup=key,
                                     marker=dict(color=pal.text_muted, size=11, symbol=shapes[key])), row=1, col=1)
    style_axes(fig, pal)
    fig.update_xaxes(range=[-bound, bound], title_text='Elasticity (no unit)')
    factors = list(FACTOR_NAMES.values())
    fig.update_yaxes(categoryorder='array', categoryarray=factors,
                     range=[len(factors)-0.5, -0.5], autorange=False,
                     tickmode='array', tickvals=factors, showgrid=False)
    fig.update_layout(height=850, margin=dict(t=110), legend=dict(y=1.13), barmode='group')
    return fig


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
        marker=dict(color=colour, opacity=0.6,
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
            marker=dict(color=colour, size=12, line=dict(color=pal.text_primary, width=1.5),
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
