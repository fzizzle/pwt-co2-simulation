"""Home — landing page for the PWT CO₂ Simulation explorer.

Opened by default from `dashboard/Overview.py`. Keeps supplied workbooks, model outputs, and
personal studies visually separated. No study conclusions live here; the WLTC baseline preview
is formatted directly from `pwt.deck.data.baseline()` and clearly labelled as model output.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard import charts
from dashboard.layout import configure, show_chart
from dashboard.theme import Palette
from pwt.deck.data import baseline

VIEWS = Path(__file__).resolve().parent
ASSETS = VIEWS.parent / "assets"


@st.cache_data(show_spinner=False)
def _hero_data_uri(theme_name: str) -> str:
    path = ASSETS / f"spa-hero-{theme_name}.png"
    raw = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


@st.cache_data(show_spinner="Loading WLTC baseline…")
def _wltc_baseline() -> pd.DataFrame:
    frame = baseline()
    return frame[frame["cycle"] == "wltc"].copy()


def _render_hero_text(pal: Palette) -> None:
    st.html(
        f"""<section class="pwt-hero" style="padding:8px 0 4px;">
          <span class="pwt-badge">Internal explorer, not a deliverable</span>
          <h1 style="margin:18px 0 10px;font-size:clamp(32px,4.4vw,52px);font-weight:700;
                     letter-spacing:-0.035em;line-height:1.04;color:{pal.text_primary};">
            Four cars. Four cycles.
          </h1>
          <p style="margin:0;max-width:44ch;font-size:15.5px;line-height:1.55;
                    color:{pal.text_secondary};">
            The twelve supplied workbooks, the Python CO₂ model, and the three personal
            studies, in one place.
          </p>
        </section>"""
    )


def _render_hero_art(pal: Palette) -> None:
    uri = _hero_data_uri(pal.name)
    st.html(
        f"""<figure style="margin:0;">
          <img src="{uri}"
               alt="North-up Spa-Francorchamps lap coloured by generated sport speed (40–150 km/h) over an interpolated altitude relief impression (373–470 m)"
               style="width:100%;max-height:340px;object-fit:contain;display:block;"/>
          <figcaption style="margin-top:6px;font-size:12px;line-height:1.45;color:{pal.text_muted};">
            Spa-Francorchamps, 7.0 km, 373 to 470 m. The generated sport lap, coloured by speed
            (40 to 150 km/h), over contours interpolated from the lap's altitude.
          </figcaption>
        </figure>"""
    )


#: Three tasks, not a copy of the sidebar: one link per kind of figure the app shows.
TASKS = [
    ("1_Overview.py", "See the workbook figures", "The twelve supplied runs, exactly as reported."),
    ("6_Model.py", "See what the model computes", "Five scenarios, from the workbook vehicles to storage losses."),
    ("7_Sizing.py", "Read the studies", "Hybrid sizing, CO₂ sensitivity and cornering speed. Drafts."),
]


def _task_links() -> None:
    for filename, label, description in TASKS:
        try:
            st.page_link(f"views/{filename}", label=label)
        except st.errors.StreamlitPageNotFoundError:
            # Run on its own (AppTest on this file, outside st.navigation): no page registry.
            st.markdown(f"**{label}**")
        st.caption(description)


def _render_wltc_preview(wltc: pd.DataFrame, pal: Palette) -> None:
    st.html(
        f"""<div style="display:flex;align-items:baseline;justify-content:space-between;
                        gap:10px;flex-wrap:wrap;margin:6px 0 4px;">
          <h2 style="margin:0;font-size:20px;font-weight:700;letter-spacing:-0.02em;
                     color:{pal.text_primary};">
            Four powertrains on the WLTC Class 3 cycle
          </h2>
          <span class="pwt-badge pwt-badge-model">Model output</span>
        </div>"""
    )
    fig = charts.model_co2_bars(wltc, pal, height=260, show_footnote=False)
    show_chart(fig)
    st.caption(
        "g CO₂/km. Assignment vehicles, storage losses included, EU grid 250 g CO₂/kWh, plug-in "
        "hybrid weighted the UN R101 way. Outlined bars and * mark runs where the engine falls "
        "short of the trace, so their figure is conditional."
    )


pal = configure("Home")
text_column, art_column = st.columns([5, 4], gap="large", vertical_alignment="center")
with text_column:
    _render_hero_text(pal)
    _task_links()
with art_column:
    _render_hero_art(pal)

st.divider()
_render_wltc_preview(_wltc_baseline(), pal)
