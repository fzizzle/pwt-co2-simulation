"""The Study B and C charts, redrawn in the deck's themes.

The studies' own figures (`docs/study-b-*.png`, `docs/study-c-*.png`) have white
backgrounds and report-sized text. These charts show the same data, read from the studies'
saved results, in the deck's colours and in Inter. A slot asks for one with
`figure: chart:<name>`, where `<name>` is the study figure's file name without `.png`.

The charts reread the saved CSVs; they never rerun a sweep. Rebuild a study's results with
its own entry point (`python -m pwt.sensitivity_report`, `python -m pwt.cornering`) first.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import pandas as pd
from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from pwt.catalog import POWERTRAIN_NAMES
from pwt.deck import art, data, fonts

DOCS = Path(__file__).resolve().parents[2] / "docs"
SWINGS = DOCS / "study-b-swings.csv"
CORNERING = DOCS / "study-c-results.csv"
COMPARISON = DOCS / "study-c-comparison.csv"

#: The chart fills the slot: 1100 by 520 slide units, drawn at 200 dpi.
SIZE_IN = (11.0, 5.2)
DPI = 200

FACTOR_NAMES = {"mass": "Car mass", "drag": "Drag coefficient", "rolling": "Rolling resistance",
                "gears": "Gear ratios", "engine": "Peak engine efficiency"}

#: Same panels as `pwt.sensitivity_reporting.PANELS`.
TORNADOS = {
    "study-b-combustion": (("petrol", "wltc"), ("hybrid", "wltc")),
    "study-b-electric": (("bev", "nedc"), ("bev", "wltc")),
    "study-b-plugin": (("phev", "franco_eco_generated"), ("phev", "franco_sport_generated")),
    "study-b-provisional": (("petrol", "franco_eco_generated"),
                            ("petrol", "franco_sport_generated")),
}
#: Same panels as `pwt.cornering.figures`.
SWEEPS = {
    "study-c-lap-time": ("lap_time_s", "Lap time, s"),
    "study-c-co2": ("co2_eu", "g CO2/km, EU grid"),
}
CORNERING_AXES = (("grip", "grip_factor", "Grip factor (tyres)"),
                  ("spoiler", "scz_m2", "Spoiler SCz, m²"))

#: Same panel titles as `pwt.cornering.figures`.
RADIUS_TITLES = {"inferred": "Inferred radii (default)", "outline": "Fitted outline radii",
                 "line": "Driver's line radii"}

FIGURES: dict[str, Path] = {
    **{name: SWINGS for name in TORNADOS},
    **{name: CORNERING for name in SWEEPS},
    "study-c-comparison": COMPARISON,
}


def pt(units: float) -> float:
    """Slide units (1/100 inch on a 16-inch slide) to points."""
    return units * 0.72


@cache
def _register_inter() -> None:
    for weight in fonts.STYLES:
        font_manager.fontManager.addfont(str(fonts.inter_file(weight)))


@cache
def _swings() -> pd.DataFrame:
    return pd.read_csv(SWINGS)


@cache
def _cornering() -> pd.DataFrame:
    return pd.read_csv(CORNERING)


@cache
def _comparison() -> pd.DataFrame:
    return pd.read_csv(COMPARISON)


def tornado_rows(powertrain: str, cycle: str) -> pd.DataFrame:
    frame = _swings()
    rows = frame[(frame.powertrain == powertrain) & (frame.cycle == cycle)]
    return rows.sort_values("rank").reset_index(drop=True)


def shared_lap_time(frame: pd.DataFrame) -> bool:
    """True when every car has the same lap time at each grip or spoiler setting."""
    keys = ["variant", "grip_factor", "scz_m2"]
    return bool((frame.groupby(keys).lap_time_s.nunique() == 1).all())


def _figure(theme: str):
    _register_inter()
    palette = art.THEMES[theme]
    fig = Figure(figsize=SIZE_IN, dpi=DPI, facecolor="none")
    FigureCanvasAgg(fig)
    fig.set_layout_engine("constrained", w_pad=0.12, h_pad=0.06, wspace=0.08)
    return fig, palette


def _style(ax, palette, grid_axis: str) -> None:
    ax.set_facecolor("none")
    ax.spines[:].set_visible(False)
    ax.tick_params(colors=palette["muted"], labelsize=pt(17), length=0, pad=8)
    ax.grid(axis=grid_axis, color=palette["line"], linewidth=pt(2))
    ax.set_axisbelow(True)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily("Inter")


def _tornado(name: str, theme: str):
    fig, palette = _figure(theme)
    selection = TORNADOS[name]
    panels = [tornado_rows(p, c) for p, c in selection]
    # Room on both sides for the value labels.
    bound = max(max(r[["delta_low", "delta_high"]].abs().to_numpy().max() for r in panels) * 1.6,
                0.1)
    # One subfigure per panel, so a long title can start over the factor names.
    halves = fig.subfigures(1, 2, wspace=0.04)
    axes = [half.subplots() for half in halves]
    for half, ax, (powertrain, cycle), rows in zip(halves, axes, selection, panels):
        colour = data.CAR_COLOURS[powertrain]
        _style(ax, palette, "x")
        for y, row in enumerate(rows.itertuples()):
            low, high = sorted((row.delta_low, row.delta_high))
            hollow_bar = not row.engine_check_pass
            ax.barh(y, high - low, left=low, height=0.46,
                    color="none" if hollow_bar else colour,
                    edgecolor=colour, linewidth=pt(3) if hollow_bar else 0)
            for end, marker in (("low", "o"), ("high", "D")):
                x = getattr(row, f"delta_{end}")
                short = getattr(row, f"short_steps_{end}") > 0
                ax.scatter(x, y, marker=marker, s=(pt(15) if marker == "o" else pt(13)) ** 2,
                           zorder=3, facecolors=palette["bg"] if short else colour,
                           edgecolors=colour if short else palette["bg"], linewidths=pt(2.5))
                # Each label sits outside its own end of the bar.
                outward = 1 if x >= getattr(row, f"delta_{'high' if end == 'low' else 'low'}") else -1
                ax.annotate(f"{getattr(row, f'co2_{end}'):.1f}", (x, y),
                            xytext=(outward * pt(16), 0), textcoords="offset points",
                            ha="left" if outward > 0 else "right", va="center",
                            fontsize=pt(15), color=palette["muted"], fontfamily="Inter")
        ax.set_yticks(range(len(rows)), [FACTOR_NAMES[f] for f in rows.factor],
                      color=palette["fg"], fontsize=pt(18), fontfamily="Inter")
        ax.set_ylim(len(rows) - 0.4, -0.7)
        ax.set_xlim(-bound, bound)
        ax.axvline(0, color=palette["muted"], linewidth=pt(2), linestyle=(0, (4, 4)))
        ax.set_xlabel("Change from baseline, g CO2/km", color=palette["muted"],
                      fontsize=pt(16), fontfamily="Inter")
        warning = " · baseline fails engine check" if rows.baseline_short_steps.iloc[0] else ""
        half.suptitle(f"{POWERTRAIN_NAMES[powertrain]} · {data.CYCLE_LABELS[cycle]}",
                      x=0.0, ha="left", color=palette["fg"], fontsize=pt(21), fontweight=600,
                      fontfamily="Inter")
        ax.set_title(f"Baseline {rows.baseline.iloc[0]:.1f} g CO2/km{warning}", loc="left",
                     color=palette["muted"], fontsize=pt(16), fontfamily="Inter", pad=pt(10))
    key = palette["muted"]
    handles = [
        Line2D([], [], marker="o", ls="", color=key, markersize=pt(13), label="parameter −10 %"),
        Line2D([], [], marker="D", ls="", color=key, markersize=pt(11), label="parameter +10 %"),
        Line2D([], [], marker="o", ls="", markerfacecolor="none", markeredgecolor=key,
               markersize=pt(13), markeredgewidth=pt(2.5),
               label="hollow: endpoint fails engine check"),
        Line2D([], [], marker="s", ls="", markerfacecolor="none", markeredgecolor=key,
               markersize=pt(13), markeredgewidth=pt(2.5),
               label="outlined bar: baseline or an endpoint fails it"),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=4, frameon=False,
               labelcolor=key, prop={"family": "Inter", "size": pt(15)},
               handletextpad=0.3, columnspacing=1.6,
               title="labels: absolute g CO2/km", title_fontproperties={
                   "family": "Inter", "size": pt(15)})
    fig.legends[0].get_title().set_color(key)
    return fig


def _sweep(name: str, theme: str):
    fig, palette = _figure(theme)
    column, label = SWEEPS[name]
    frame = _cornering()
    one_line = column == "lap_time_s" and shared_lap_time(frame)
    axes = fig.subplots(1, 2)
    for ax, (variant, x, xlabel) in zip(axes, CORNERING_AXES):
        _style(ax, palette, "y")
        rows = frame[frame.variant == variant]
        groups = ([("all", rows.drop_duplicates(x))] if one_line
                  else list(rows.groupby("powertrain", sort=False)))
        for car, d in groups:
            colour = palette["fg"] if one_line else data.CAR_COLOURS[car]
            ax.plot(d[x], d[column], color=colour, linewidth=pt(4), solid_capstyle="round")
            short = d.short_steps > 0
            ax.scatter(d[x][~short], d[column][~short], s=pt(13) ** 2, color=colour,
                       edgecolors=palette["bg"], linewidths=pt(2.5), zorder=3)
            ax.scatter(d[x][short], d[column][short], s=pt(13) ** 2, color=palette["bg"],
                       edgecolors=colour, linewidths=pt(2.5), zorder=3)
        ax.set_xlabel(xlabel, color=palette["muted"], fontsize=pt(16), fontfamily="Inter")
        ax.set_xticks(sorted(rows[x].unique()))
    axes[0].set_ylabel(label, color=palette["muted"], fontsize=pt(16), fontfamily="Inter")
    if one_line:
        note = "one line: every car drives the same lap at each setting"
        handles = [Line2D([], [], color=palette["fg"], linewidth=pt(4), marker="o",
                          markersize=pt(11), label=note)]
    else:
        handles = [Line2D([], [], color=data.CAR_COLOURS[car], linewidth=pt(4), marker="o",
                          markersize=pt(11), label=POWERTRAIN_NAMES[car])
                   for car in data.POWERTRAINS if car in set(frame.powertrain)]
    if (frame.short_steps > 0).any():
        handles.append(Line2D([], [], marker="o", ls="", markerfacecolor="none",
                              markeredgecolor=palette["muted"], markersize=pt(11),
                              label="hollow: engine short of the trace"))
    fig.legend(handles=handles, loc="outside upper center", ncol=len(handles), frameon=False,
               labelcolor=palette["fg"], prop={"family": "Inter", "size": pt(17)},
               columnspacing=2.0)
    return fig


def _comparison_chart(theme: str):
    """Spoiler minus tyres at the same lap time, one panel per radius method."""
    fig, palette = _figure(theme)
    frame = _comparison()
    methods = list(frame.radius_method.unique())
    axes = fig.subplots(1, len(methods), sharey=True, squeeze=False)[0]
    for ax, method in zip(axes, methods):
        _style(ax, palette, "y")
        part = frame[frame.radius_method == method]
        for car, d in part.groupby("powertrain", sort=False):
            colour = data.CAR_COLOURS[car]
            ax.plot(d.scz_m2, d.delta_co2_eu, color=colour, linewidth=pt(4),
                    solid_capstyle="round")
            short = (d.spoiler_short_steps > 0) | (d.tyres_short_steps > 0)
            ax.scatter(d.scz_m2[~short], d.delta_co2_eu[~short], s=pt(13) ** 2, color=colour,
                       edgecolors=palette["bg"], linewidths=pt(2.5), zorder=3)
            ax.scatter(d.scz_m2[short], d.delta_co2_eu[short], s=pt(13) ** 2,
                       color=palette["bg"], edgecolors=colour, linewidths=pt(2.5), zorder=3)
        ax.axhline(0, color=palette["muted"], linewidth=pt(2), linestyle=(0, (4, 4)))
        ax.set_title(RADIUS_TITLES.get(method, method), loc="left", color=palette["fg"],
                     fontsize=pt(18), fontweight=600, fontfamily="Inter")
        ax.set_xlabel("Spoiler SCz, m²", color=palette["muted"], fontsize=pt(16),
                      fontfamily="Inter")
        ax.set_xticks(sorted(part.scz_m2.unique()))
    axes[0].set_ylabel("Spoiler minus tyres, g CO2/km", color=palette["muted"],
                       fontsize=pt(16), fontfamily="Inter")
    handles = [Line2D([], [], color=data.CAR_COLOURS[car], linewidth=pt(4), marker="o",
                      markersize=pt(11), label=POWERTRAIN_NAMES[car])
               for car in data.POWERTRAINS if car in set(frame.powertrain)]
    if ((frame.spoiler_short_steps > 0) | (frame.tyres_short_steps > 0)).any():
        handles.append(Line2D([], [], marker="o", ls="", markerfacecolor="none",
                              markeredgecolor=palette["muted"], markersize=pt(11),
                              label="hollow: engine short of the trace"))
    fig.legend(handles=handles, loc="outside upper center", ncol=len(handles), frameon=False,
               labelcolor=palette["fg"], prop={"family": "Inter", "size": pt(17)},
               columnspacing=2.0)
    return fig


def render(name: str, theme: str, out_dir: Path) -> Path:
    """Draw chart `name` for `theme` as a transparent PNG in `out_dir`."""
    if name not in FIGURES:
        raise ValueError(f"Unknown chart {name!r}. Use one of: {', '.join(sorted(FIGURES))}.")
    if name in TORNADOS:
        fig = _tornado(name, theme)
    elif name in SWEEPS:
        fig = _sweep(name, theme)
    else:
        fig = _comparison_chart(theme)
    path = Path(out_dir) / f"{theme}-{name}.png"
    fig.savefig(path, dpi=DPI, transparent=True)
    return path
