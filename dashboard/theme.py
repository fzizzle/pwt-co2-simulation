"""Colour and layout tokens, applied identically on every page.

Palette provenance — these are not taste choices, they were computed:

  * The four powertrains need four categorical colours. Enumerating all 70 four-slot
    combinations of the reference palette against the validator showed that **no** set of four
    clears the all-pairs gates in both light and dark. Only three slots can.
  * So the charts here stay on forms whose pairlist is *adjacent* — grouped bars and lines with
    a fixed series order — never a four-series scatter. On that pairlist the documented slots
    1-4 pass every hard gate: worst adjacent CVD ΔE 9.1 light / 8.4 dark, worst normal-vision
    ΔE 22.9 light / 19.8 dark.
  * Aqua (2.74:1) and yellow (2.11:1) fall below 3:1 on the light surface, so the relief rule
    applies: every chart ships visible value labels and a table view. That is an obligation,
    not a preference — do not remove the labels or the tables.

Series order is fixed by POWERTRAIN_ORDER and colour follows the powertrain, never its rank,
so filtering the view never repaints the survivors.

The app pins `base = "light"` in `.streamlit/config.toml`, so the light palette is what
viewers actually see — a deliberate single-look commitment rather than an automatic flip. DARK
is kept and validated against the dark surface so that unpinning the theme stays a one-line
change; `palette()` already resolves it from the viewer's active theme.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

#: Fixed series order. Colour is bound to the entity, so this order never changes.
POWERTRAIN_ORDER = ("petrol", "bev", "hybrid", "phev")


@dataclass(frozen=True, slots=True)
class Palette:
    surface: str
    text_primary: str
    text_secondary: str
    text_muted: str
    grid: str
    axis: str
    series: tuple[str, str, str, str]

    def for_powertrain(self, powertrain: str | None) -> str:
        try:
            return self.series[POWERTRAIN_ORDER.index(powertrain or "")]
        except ValueError:
            return self.text_muted


LIGHT = Palette(
    surface="#fcfcfb",
    text_primary="#0b0b0b",
    text_secondary="#52514e",
    text_muted="#8a8880",
    grid="#e8e7e3",
    axis="#c3c2b7",
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100"),
)

DARK = Palette(
    surface="#1a1a19",
    text_primary="#ffffff",
    text_secondary="#c3c2b7",
    text_muted="#8a8880",
    grid="#2e2e2c",
    axis="#52514e",
    series=("#3987e5", "#d95926", "#199e70", "#c98500"),
)


def palette() -> Palette:
    """The palette matching the viewer's active Streamlit theme."""
    try:
        if getattr(st.context.theme, "type", "light") == "dark":
            return DARK
    except Exception:
        pass  # older Streamlit, or no script run context (e.g. under pytest)
    return LIGHT


def style_axes(fig, pal: Palette, *, x_title: str = "", y_title: str = ""):
    """Recessive grid and axes, transparent surface, consistent fonts.

    The figure background is left transparent so the page surface shows through and the chart
    cannot disagree with the theme.
    """
    fig.update_layout(
        # Importing Streamlit registers a default template whose colorway is placeholder
        # values (#000001…#000010) meant to be substituted by its own charting theme. The
        # charts here are drawn with theme=None so the validated palette survives untouched,
        # which means those placeholders would never be replaced — pin the template to "none"
        # so a trace without an explicit colour can never render as near-black.
        template="none",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif",
            size=13,
            color=pal.text_secondary,
        ),
        margin=dict(l=8, r=8, t=8, b=8),
        hoverlabel=dict(font_size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(color=pal.text_secondary),
        ),
    )
    axis_common = dict(
        # Let Plotly grow the margins to fit tick labels and titles; the 8px margin above is
        # only the floor, and without this the axis labels are clipped.
        automargin=True,
        showgrid=True,
        gridcolor=pal.grid,
        gridwidth=1,
        zeroline=False,
        linecolor=pal.axis,
        tickfont=dict(color=pal.text_muted, size=12),
        title_font=dict(color=pal.text_secondary, size=12),
    )
    # Only set a title when one is given: a subplot figure sets its own per-row titles before
    # calling this, and passing title_text="" here would wipe them.
    fig.update_xaxes(**axis_common, **({"title_text": x_title} if x_title else {}))
    fig.update_yaxes(**axis_common, **({"title_text": y_title} if y_title else {}))
    return fig
