"""The Study A, B and C charts, redrawn in the deck's themes.

The studies' own figures (`docs/phase-3-sizing.png`, `docs/study-b-*.png`,
`docs/study-c-*.png`) have white
backgrounds and report-sized text. These charts show the same data, read from the studies'
saved results, in the deck's colours and in Inter. A slot asks for one with
`figure: chart:<name>`, where `<name>` is the study figure's file name without `.png`.

The charts reread the saved CSVs; they never rerun a sweep. Rebuild a study's results with
its own entry point (`python -m pwt.sweep`, `python -m pwt.sensitivity_report`,
`python -m pwt.cornering`) first. Study A's charts have no figure of the same name, so
`STUDY_FIGURES` names the study document they come from.
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
SIZING = DOCS / "phase-3-sizing.csv"
STORAGE = DOCS / "phase-3-storage.csv"

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

#: Study A charts show two cycles only, to stay legible on a slide: the regulatory WLTC Class 3
#: and the hardest lap. NEDC and the eco lap are in `docs/phase-3-sizing.md`.
SHOWN_CYCLES = ("wltc", "franco_sport_generated")
#: Colour is the car, as everywhere in the deck; line style is the cycle.
CYCLE_STYLES = {"wltc": "-", "franco_sport_generated": (0, (5, 3))}
#: Study A text sizes, in slide units: larger than the B and C charts, for projection.
A_TICK, A_LABEL, A_NOTE, A_LINE = 21, 20, 19, 23
#: Each entry is (powertrain, CO2 column, y-axis label, one panel per cycle).
#: The full hybrid's WLTC curve spans about 12 g CO2/km against 70 on the sport lap, so it
#: gets its own panel and its own scale.
SIZING_CHARTS = {
    "phase-3-hybrid": ("hybrid", "co2_eu", "Full hybrid, g CO2/km", True),
    "phase-3-plugin": ("phev", "co2_eu", "Plug-in hybrid, g CO2/km, EU grid", False),
}
#: Where a "lowest" label sits, in axes fractions, when the spot next to its point is taken;
#: a leader line joins it to the point.
LABEL_SPOTS = {
    ("phase-3-plugin", "franco_sport_generated"): (0.40, 0.62),
    ("phase-3-plugin", "wltc"): (0.48, 0.25),
}
#: The assumed one-way storage efficiency of the "storage losses" scenario (0.85 each way).
ASSUMED_STORAGE = 0.85
FIGURES: dict[str, Path] = {
    "phase-3-storage": STORAGE,
    **{name: SIZING for name in SIZING_CHARTS},
    **{name: SWINGS for name in TORNADOS},
    **{name: CORNERING for name in SWEEPS},
    "study-c-comparison": COMPARISON,
}


#: The study figure or document each chart stands for, when it isn't `docs/<name>.png`.
STUDY_FIGURES = {name: "docs/phase-3-sizing.md" for name in ("phase-3-storage", *SIZING_CHARTS)}


def study_figure(name: str) -> str:
    return STUDY_FIGURES.get(name, f"docs/{name}.png")


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


@cache
def _sizing() -> pd.DataFrame:
    return pd.read_csv(SIZING)


@cache
def _storage() -> pd.DataFrame:
    return pd.read_csv(STORAGE)


def best_by_battery(powertrain: str, cycle: str, co2: str = "co2_eu") -> pd.DataFrame:
    """The lowest-CO2 buildable motor at each battery size, as `pwt.sweep.by_battery` picks it.

    Keeps the chosen row's motor and feasibility, so a short step can be drawn hollow.
    """
    frame = _sizing()
    part = frame[(frame.powertrain == powertrain) & (frame.cycle == cycle) & frame.buildable]
    rows = part.loc[part.groupby("battery_kwh")[co2].idxmin()]
    return rows.sort_values("battery_kwh").reset_index(drop=True)


def storage_rows(cycle: str) -> pd.DataFrame:
    frame = _storage()
    return frame[frame.cycle == cycle].sort_values("storage_efficiency")


def storage_short(cycle: str) -> pd.Series:
    """True where either strategy's engine falls short of the trace, by storage efficiency."""
    rows = storage_rows(cycle)
    return rows.groupby("storage_efficiency").short_steps.max() > 0


def storage_gap(cycle: str) -> pd.Series:
    """Band minus sheets' rule, g CO2/km, indexed by one-way storage efficiency."""
    wide = storage_rows(cycle).pivot(index="storage_efficiency", columns="strategy",
                                      values="co2_eu")
    return (wide["band"] - wide["sheets' rule"]).round(1)


def tornado_rows(powertrain: str, cycle: str) -> pd.DataFrame:
    frame = _swings()
    rows = frame[(frame.powertrain == powertrain) & (frame.cycle == cycle)]
    return rows.sort_values("rank").reset_index(drop=True)


def shared_lap_time(frame: pd.DataFrame) -> bool:
    """True when every car has the same lap time at each grip or spoiler setting."""
    keys = ["variant", "grip_factor", "scz_m2"]
    return bool((frame.groupby(keys).lap_time_s.nunique() == 1).all())


def _figure(theme: str, constrained: bool = True):
    _register_inter()
    palette = art.THEMES[theme]
    fig = Figure(figsize=SIZE_IN, dpi=DPI, facecolor="none")
    FigureCanvasAgg(fig)
    if constrained:
        fig.set_layout_engine("constrained", w_pad=0.12, h_pad=0.06, wspace=0.08)
    return fig, palette


def _style(ax, palette, grid_axis: str, tick: float = 20) -> None:
    ax.set_facecolor("none")
    ax.spines[:].set_visible(False)
    ax.tick_params(colors=palette["muted"], labelsize=pt(tick), length=0, pad=8)
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
                            fontsize=pt(18), color=palette["muted"], fontfamily="Inter")
        ax.set_yticks(range(len(rows)), [FACTOR_NAMES[f] for f in rows.factor],
                      color=palette["fg"], fontsize=pt(21), fontfamily="Inter")
        ax.set_ylim(len(rows) - 0.4, -0.7)
        ax.set_xlim(-bound, bound)
        ax.axvline(0, color=palette["muted"], linewidth=pt(2), linestyle=(0, (4, 4)))
        ax.set_xlabel("Change from baseline, g CO2/km", color=palette["muted"],
                      fontsize=pt(19), fontfamily="Inter")
        warning = " · baseline fails engine check" if rows.baseline_short_steps.iloc[0] else ""
        half.suptitle(f"{POWERTRAIN_NAMES[powertrain]} · {data.CYCLE_LABELS[cycle]}",
                      x=0.0, ha="left", color=palette["fg"], fontsize=pt(24), fontweight=600,
                      fontfamily="Inter")
        ax.set_title(f"Baseline {rows.baseline.iloc[0]:.1f} g CO2/km{warning}", loc="left",
                     color=palette["muted"], fontsize=pt(19), fontfamily="Inter", pad=pt(10))
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
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False,
               labelcolor=key, prop={"family": "Inter", "size": pt(18)},
               handletextpad=0.3, columnspacing=1.6,
               title="labels: absolute g CO2/km", title_fontproperties={
                   "family": "Inter", "size": pt(18)})
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
        ax.set_xlabel(xlabel, color=palette["muted"], fontsize=pt(19), fontfamily="Inter")
        ax.set_xticks(sorted(rows[x].unique()))
    axes[0].set_ylabel(label, color=palette["muted"], fontsize=pt(19), fontfamily="Inter")
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
               labelcolor=palette["fg"], prop={"family": "Inter", "size": pt(20)},
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
                     fontsize=pt(21), fontweight=600, fontfamily="Inter")
        ax.set_xlabel("Spoiler SCz, m²", color=palette["muted"], fontsize=pt(19),
                      fontfamily="Inter")
        ax.set_xticks(sorted(part.scz_m2.unique()))
    axes[0].set_ylabel("Spoiler minus tyres, g CO2/km", color=palette["muted"],
                       fontsize=pt(19), fontfamily="Inter")
    handles = [Line2D([], [], color=data.CAR_COLOURS[car], linewidth=pt(4), marker="o",
                      markersize=pt(11), label=POWERTRAIN_NAMES[car])
               for car in data.POWERTRAINS if car in set(frame.powertrain)]
    if ((frame.spoiler_short_steps > 0) | (frame.tyres_short_steps > 0)).any():
        handles.append(Line2D([], [], marker="o", ls="", markerfacecolor="none",
                              markeredgecolor=palette["muted"], markersize=pt(11),
                              label="hollow: engine short of the trace"))
    fig.legend(handles=handles, loc="outside upper center", ncol=len(handles), frameon=False,
               labelcolor=palette["fg"], prop={"family": "Inter", "size": pt(20)},
               columnspacing=2.0)
    return fig


def _a_axes(fig, palette, rows: int = 1):
    # Fixed margins: the line labels on the right need room the automatic layout
    # doesn't reserve. The terms are defined on the Study A glossary slide (A-terms).
    fig.subplots_adjust(left=0.09, right=0.75, top=0.88, bottom=0.14, hspace=0.42)
    axes = fig.subplots(rows, 1, sharex=True, squeeze=False)[:, 0]
    for ax in axes:
        _style(ax, palette, "y", A_TICK)
    return list(axes)


def _end_label(ax, x, y, text: str, colour: str) -> None:
    """Name a line at its right end, instead of a legend."""
    ax.annotate(text, (x, y), xytext=(pt(22), 0), textcoords="offset points", ha="left",
                va="center", fontsize=pt(A_LINE), fontweight=600, color=colour,
                fontfamily="Inter", annotation_clip=False)


def _hollow_key(fig, palette, text: str) -> None:
    """The hollow-point key, in the strip above the plot where nothing collides with it."""
    fig.text(0.09, 0.985, "○  " + text, ha="left", va="top", fontsize=pt(A_NOTE),
             color=palette["fg"], fontfamily="Inter")


def _note(ax, palette, x, y, text, ha="left", va="top", colour=None) -> None:
    ax.text(x, y, text, transform=ax.transAxes, ha=ha, va=va, fontsize=pt(A_NOTE),
            color=colour or palette["muted"], fontfamily="Inter")


def _petrol_line(ax, palette, cycle: str) -> None:
    """The assignment petrol car on the same cycle, from the deck's baseline, labelled."""
    petrol = data.cell("petrol", cycle)
    colour = data.CAR_COLOURS["petrol"]
    ax.axhline(petrol.co2_eu, color=colour, linewidth=pt(3), linestyle=(0, (1, 2.5)),
               dash_capstyle="round")
    flag = " (engine short)" if petrol.short_steps > 0 else ""
    name = "sport lap" if cycle == "franco_sport_generated" else data.CYCLE_LABELS[cycle]
    # The label is in the text colour: the petrol orange is too faint on the light theme.
    ax.annotate(f"petrol, {name}{flag}", (20.6, petrol.co2_eu), xytext=(0, pt(6)),
                textcoords="offset points", ha="right", va="bottom", fontsize=pt(A_NOTE),
                color=palette["muted"], fontfamily="Inter")


def _points(ax, palette, x, y, short, colour, size=13) -> None:
    ax.scatter(x[~short], y[~short], s=pt(size) ** 2, color=colour, edgecolors=palette["bg"],
               linewidths=pt(2), zorder=3)
    ax.scatter(x[short], y[short], s=pt(size) ** 2, color=palette["bg"], edgecolors=colour,
               linewidths=pt(3), zorder=3)


def _sizing_chart(name: str, theme: str):
    """CO2 against battery size at the best buildable motor, WLTC and the sport lap."""
    fig, palette = _figure(theme, constrained=False)
    powertrain, column, ylabel, split = SIZING_CHARTS[name]
    colour = data.CAR_COLOURS[powertrain]
    cycles = SHOWN_CYCLES[::-1]  # sport lap on top: it has the higher CO2
    axes = _a_axes(fig, palette, len(cycles) if split else 1)
    any_short = False
    for k, cycle in enumerate(cycles):
        ax = axes[k] if split else axes[0]
        style = "-" if split else CYCLE_STYLES[cycle]
        rows = best_by_battery(powertrain, cycle, column)
        _petrol_line(ax, palette, cycle)
        ax.plot(rows.battery_kwh, rows[column], color=colour, linewidth=pt(5), linestyle=style,
                solid_capstyle="round")
        short = rows.short_steps > 0
        any_short |= bool(short.any())
        _points(ax, palette, rows.battery_kwh, rows[column], short, colour)
        top = rows.loc[rows[column].idxmin()]
        ax.scatter(top.battery_kwh, top[column], s=pt(28) ** 2, facecolors="none",
                   edgecolors=palette["fg"], linewidths=pt(3), zorder=4)
        from pwt.sweep import BATTERY_KWH, MOTOR_KW
        edge = top.motor_kw == max(MOTOR_KW) or top.battery_kwh == max(BATTERY_KWH)
        text = (f"lowest: {top.battery_kwh:g} kWh · {top.motor_kw:g} kW"
                + (", at the grid edge" if edge else ""))
        style = dict(fontsize=pt(A_NOTE), color=palette["fg"], fontfamily="Inter")
        spot = LABEL_SPOTS.get((name, cycle))
        if spot:
            ax.annotate(text, (top.battery_kwh, top[column]), xytext=spot,
                        textcoords="axes fraction", ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=palette["muted"],
                                        linewidth=pt(2), shrinkA=4, shrinkB=pt(16)), **style)
        else:
            ax.annotate(text, (top.battery_kwh, top[column]), xytext=(pt(20), -pt(16)),
                        textcoords="offset points", ha="left", va="top", **style)
        last = rows.iloc[-1]
        if not split:
            _end_label(ax, last.battery_kwh, last[column], data.CYCLE_LABELS[cycle], colour)
        if split:
            # Each panel has its own scale, so each names its cycle.
            ax.set_title(data.CYCLE_LABELS[cycle] + ", own scale", loc="left",
                         color=palette["fg"], fontsize=pt(A_LABEL), fontweight=600,
                         fontfamily="Inter", pad=pt(8))
            low, high = ax.get_ylim()
            ax.set_ylim(low - 0.25 * (high - low), high + 0.1 * (high - low))
    if not split:
        axes[0].set_ylim(bottom=0)
    axes[-1].set_xticks([1, 2, 4, 6, 8, 10, 12, 15, 20])
    axes[-1].set_xlim(0, 21)
    axes[-1].set_xlabel("Battery, kWh", color=palette["muted"], fontsize=pt(A_LABEL),
                        fontfamily="Inter")
    fig.supylabel(ylabel, color=palette["muted"], fontsize=pt(A_LABEL), fontfamily="Inter",
                  x=0.01)
    if any_short:
        _hollow_key(fig, palette, "hollow point: the engine is short of the trace, so that "
                    "CO2 is conditional")
    return fig


def _storage_chart(theme: str):
    """Band minus sheets' rule for the assignment full hybrid, by storage efficiency."""
    fig, palette = _figure(theme, constrained=False)
    ax = _a_axes(fig, palette)[0]
    colour = data.CAR_COLOURS["hybrid"]
    ax.axhline(0, color=palette["fg"], linewidth=pt(2))
    ax.axvline(ASSUMED_STORAGE, color=palette["muted"], linewidth=pt(2), linestyle=(0, (4, 4)))
    ax.annotate("assumed: 85 %", (ASSUMED_STORAGE, 0.02), xycoords=("data", "axes fraction"),
                xytext=(pt(8), 0), textcoords="offset points", ha="left", va="bottom",
                fontsize=pt(A_NOTE), color=palette["muted"], fontfamily="Inter")
    any_short = False
    for cycle in SHOWN_CYCLES:
        gap, short = storage_gap(cycle), storage_short(cycle)
        any_short |= bool(short.any())
        ax.plot(gap.index, gap.values, color=colour, linewidth=pt(5),
                linestyle=CYCLE_STYLES[cycle], solid_capstyle="round")
        _points(ax, palette, gap.index, gap.values, short.reindex(gap.index), colour)
        _end_label(ax, gap.index[-1], gap.iloc[-1], data.CYCLE_LABELS[cycle], colour)
    _note(ax, palette, 0.99, 0.97, "↑ band strategy emits more", ha="right")
    _note(ax, palette, 0.99, 0.03, "↓ band strategy emits less", ha="right", va="bottom")
    if any_short:
        every = all(storage_short(c).all() for c in SHOWN_CYCLES)
        _hollow_key(fig, palette, "every point is conditional: the sheets'-rule car's engine "
                    "can't follow either trace" if every else "hollow point: the sheets'-rule "
                    "car's engine is short of the trace, so the gap is conditional")
    bound = max(abs(v) for v in ax.get_ylim()) * 1.15
    ax.set_ylim(-bound, bound)
    ax.set_xticks(sorted(_storage().storage_efficiency.unique()))
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}".replace("%", " %"))
    ax.set_xlabel("One-way storage efficiency", color=palette["muted"], fontsize=pt(A_LABEL),
                  fontfamily="Inter")
    ax.set_ylabel("Band strategy minus sheets' rule,\ng CO2/km", color=palette["muted"],
                  fontsize=pt(A_LABEL), fontfamily="Inter")
    return fig


def render(name: str, theme: str, out_dir: Path) -> Path:
    """Draw chart `name` for `theme` as a transparent PNG in `out_dir`."""
    if name not in FIGURES:
        raise ValueError(f"Unknown chart {name!r}. Use one of: {', '.join(sorted(FIGURES))}.")
    if name == "phase-3-storage":
        fig = _storage_chart(theme)
    elif name in SIZING_CHARTS:
        fig = _sizing_chart(name, theme)
    elif name in TORNADOS:
        fig = _tornado(name, theme)
    elif name in SWEEPS:
        fig = _sweep(name, theme)
    else:
        fig = _comparison_chart(theme)
    path = Path(out_dir) / f"{theme}-{name}.png"
    fig.savefig(path, dpi=DPI, transparent=True)
    return path
