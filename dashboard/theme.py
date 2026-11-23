"""Colour and layout tokens aligned with the group presentation deck (`pwt/deck/`).

Surfaces and car colours match `pwt/deck/art.py` and `pwt/deck/data.py`:
  * Dark surfaces: #000000 canvas, #1c1c1e raised, #2c2c2e rule, #f5f5f7 ink, #86868b muted.
  * Light twin:    #ffffff canvas, #f5f5f7 raised, #e5e5ea rule, #1d1d1f ink, #6e6e73 muted
                   (strengthened from #86868b on white so small text clears WCAG AA 4.5:1).
  * Car colours (fixed by powertrain, never by rank):
    petrol #d09539, full hybrid #4fb267, plug-in hybrid #b677d5, battery electric #3984d0.

Under deuteranopia and protanopia, plug-in hybrid (#b677d5) and battery electric (#3984d0)
shift closer in hue. Every multi-series line or scatter chart therefore pairs colour with
`POWERTRAIN_DASHES` and `POWERTRAIN_MARKERS` (and bar charts keep direct value labels and a
table view).
"""

from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go
import streamlit as st

#: Fixed series order (increasing electrification, matching `pwt.deck.data.POWERTRAINS`).
POWERTRAIN_ORDER = ("petrol", "hybrid", "phev", "bev")

#: Exact car colours from `pwt/deck/data.py`.
CAR_COLOURS: dict[str, str] = {
    "petrol": "#d09539",
    "hybrid": "#4fb267",
    "phev": "#b677d5",
    "bev": "#3984d0",
}

#: Redundant dash and marker encodings so BEV vs PHEV (and petrol vs hybrid) remain distinct
#: for colour-blind viewers and in monochrome printouts.
POWERTRAIN_DASHES: dict[str, str] = {
    "petrol": "solid",
    "hybrid": "dash",
    "phev": "dashdot",
    "bev": "dot",
}

POWERTRAIN_MARKERS: dict[str, str] = {
    "petrol": "circle",
    "hybrid": "square",
    "phev": "diamond",
    "bev": "triangle-up",
}

FONT_STACK = (
    "'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', "
    "'Segoe UI', Helvetica, Arial, sans-serif"
)


@dataclass(frozen=True, slots=True)
class Palette:
    surface: str
    text_primary: str
    text_secondary: str
    text_muted: str
    grid: str
    axis: str
    series: tuple[str, str, str, str]
    surface_raised: str = ""
    border: str = ""
    primary: str = ""
    name: str = "dark"

    def for_powertrain(self, powertrain: str | None) -> str:
        try:
            return self.series[POWERTRAIN_ORDER.index(powertrain or "")]
        except ValueError:
            return self.text_muted

    def dash_for_powertrain(self, powertrain: str | None) -> str:
        return POWERTRAIN_DASHES.get(powertrain or "", "solid")

    def marker_for_powertrain(self, powertrain: str | None) -> str:
        return POWERTRAIN_MARKERS.get(powertrain or "", "circle")


_CAR_SERIES: tuple[str, str, str, str] = tuple(CAR_COLOURS[p] for p in POWERTRAIN_ORDER)

LIGHT = Palette(
    surface="#ffffff",
    text_primary="#1d1d1f",
    text_secondary="#424245",
    text_muted="#6e6e73",
    grid="#e5e5ea",
    axis="#d1d1d6",
    series=_CAR_SERIES,
    surface_raised="#f5f5f7",
    border="#e5e5ea",
    primary="#1f63a8",
    name="light",
)

DARK = Palette(
    surface="#000000",
    text_primary="#f5f5f7",
    text_secondary="#c7c7cc",
    text_muted="#86868b",
    grid="#1c1c1e",
    axis="#2c2c2e",
    series=_CAR_SERIES,
    surface_raised="#1c1c1e",
    border="#2c2c2e",
    primary="#2f78c1",
    name="dark",
)


def palette() -> Palette:
    """The palette matching the active Streamlit theme.

    Checks both `"dark"` and `"light"` on `st.context.theme` before consulting the configured
    `theme.base` fallback, so switching themes in Settings immediately repaints charts and CSS.
    """
    try:
        theme_type = getattr(st.context.theme, "type", None)
        if theme_type == "dark":
            return DARK
        if theme_type == "light":
            return LIGHT
    except Exception:
        pass  # no script run context
    try:
        if st.get_option("theme.base") == "dark":
            return DARK
    except Exception:
        pass
    return LIGHT


def plotly_template(pal: Palette) -> go.layout.Template:
    """Deck-aligned Plotly template: transparent canvas, subdued horizontal grid, Inter type.

    Leaves `colorway=None` so Streamlit's placeholder colorway (`#000001…#000010`) can never
    leak when charts render with `theme=None`.
    """
    axis_base = dict(
        automargin=True,
        zeroline=False,
        linecolor=pal.axis,
        tickfont=dict(color=pal.text_muted, size=12),
        title_font=dict(color=pal.text_secondary, size=12),
    )
    return go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family=FONT_STACK, size=13, color=pal.text_secondary),
            margin=dict(l=8, r=8, t=12, b=8),
            hoverlabel=dict(
                bgcolor=pal.surface_raised or pal.surface,
                bordercolor=pal.border or pal.axis,
                font=dict(family=FONT_STACK, size=12, color=pal.text_primary),
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                title_text="",
                font=dict(color=pal.text_secondary, size=12),
            ),
            xaxis=dict(**axis_base, showgrid=False),
            yaxis=dict(**axis_base, showgrid=True, gridcolor=pal.grid, gridwidth=1),
        )
    )


def style_axes(fig, pal: Palette, *, x_title: str = "", y_title: str = ""):
    """Apply the deck Plotly template and keep subplot titles and automargins intact.

    The figure background stays transparent so the page surface shows through and the chart
    cannot disagree with the active theme.
    """
    fig.update_layout(
        template=plotly_template(pal),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=13, color=pal.text_secondary),
        margin=dict(l=8, r=8, t=12, b=8),
        hoverlabel=dict(
            bgcolor=pal.surface_raised or pal.surface,
            bordercolor=pal.border or pal.axis,
            font=dict(family=FONT_STACK, size=12, color=pal.text_primary),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
            font=dict(color=pal.text_secondary, size=12),
        ),
    )
    axis_common = dict(
        # Let Plotly grow the margins to fit tick labels and titles; the 8px margin above is
        # only the floor, and without this the axis labels are clipped.
        automargin=True,
        zeroline=False,
        linecolor=pal.axis,
        tickfont=dict(color=pal.text_muted, size=12),
        title_font=dict(color=pal.text_secondary, size=12),
    )
    # Subdued horizontal reference gridlines only; no vertical cage.
    fig.update_xaxes(**axis_common, showgrid=False)
    # Only set a y-title when one is given: a subplot figure sets its own per-row titles before
    # calling this, and passing title_text="" here would wipe them.
    fig.update_yaxes(
        **axis_common,
        showgrid=True,
        gridcolor=pal.grid,
        gridwidth=1,
        **({"title_text": y_title} if y_title else {}),
    )

    if x_title:
        # On a stacked subplot figure every row has an x-axis, so titling them all prints the
        # label once per row. Only the bottom axis carries it.
        x_axes = sorted(
            (k for k in fig.layout if k.startswith("xaxis")),
            key=lambda k: int(k.removeprefix("xaxis") or 1),
        )
        fig.layout[x_axes[-1]].title.text = x_title
    return fig
