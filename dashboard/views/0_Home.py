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
from dashboard.layout import configure
from dashboard.theme import POWERTRAIN_ORDER, Palette
from pwt.catalog import POWERTRAIN_NAMES
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


def _render_hero(pal: Palette) -> None:
    uri = _hero_data_uri(pal.name)
    is_dark = pal.name == "dark"
    hero_bg = "#000000" if is_dark else "#ffffff"
    hero_border = pal.border
    st.html(
        f"""<section class="pwt-hero" style="
            background:{hero_bg};
            border:1px solid {hero_border};
            border-radius:18px;
            padding:18px 24px 20px;
            text-align:center;
            margin-bottom:20px;
        ">
          <div style="display:flex;justify-content:space-between;align-items:center;
                      gap:8px;flex-wrap:wrap;margin-bottom:4px;">
            <span class="pwt-badge">Internal explorer · not a deliverable</span>
            <span style="font-size:12px;font-weight:600;color:{pal.text_muted};">
              Spa-Francorchamps · 7.0 km · 373–470 m
            </span>
          </div>
          <div style="display:flex;justify-content:center;align-items:center;margin:2px 0 -10px;">
            <img src="{uri}"
                 alt="North-up Spa-Francorchamps lap coloured by generated sport speed (40–150 km/h) over an interpolated altitude relief impression (373–470 m)"
                 style="max-height:195px;width:auto;max-width:100%;display:block;"/>
          </div>
          <h1 style="position:relative;z-index:2;margin:0 0 8px;
                     font-size:clamp(28px,4vw,46px);font-weight:700;
                     letter-spacing:-0.035em;line-height:1.06;color:{pal.text_primary};">
            Four cars. Four cycles.
          </h1>
          <p style="margin:0 auto;max-width:600px;font-size:14.5px;line-height:1.5;
                    color:{pal.text_secondary};">
            Internal viewer for the twelve supplied workbooks, the Python CO₂ model,
            and the three personal studies.
          </p>
          <p style="margin:8px 0 0;font-size:11.5px;color:{pal.text_muted};">
            Generated sport lap coloured by speed (40–150 km/h); contour lines are an impression
            interpolated from lap altitude (373–470 m).
          </p>
        </section>"""
    )


def _render_wltc_preview(wltc: pd.DataFrame, pal: Palette) -> None:
    st.html(
        f"""<div style="display:flex;align-items:center;justify-content:space-between;
                        gap:10px;flex-wrap:wrap;margin:6px 0 10px;">
          <div>
            <div style="font-size:12px;font-weight:600;color:{pal.text_muted};">
              WLTC Class 3 baseline preview
            </div>
            <h2 style="margin:2px 0 0;font-size:20px;font-weight:700;
                       letter-spacing:-0.02em;color:{pal.text_primary};">
              Four powertrains on the highway cycle
            </h2>
          </div>
          <span class="pwt-badge pwt-badge-model">
            Model output · storage losses · EU grid 250 g CO₂/kWh
          </span>
        </div>"""
    )

    cards_html = []
    for pt in POWERTRAIN_ORDER:
        subset = wltc[wltc["powertrain"] == pt]
        if subset.empty:
            continue
        row = subset.iloc[0]
        colour = pal.for_powertrain(pt)
        short_steps = int(row["short_steps"])
        short_kw = float(row["short_kw"])
        hollow = short_steps > 0
        swatch_style = (
            f"background:transparent;border:2px solid {colour};"
            if hollow
            else f"background:{colour};border:2px solid {colour};"
        )
        val = f"{row['co2_eu']:.1f}*" if hollow else f"{row['co2_eu']:.1f}"
        feas = (
            f"short on {short_steps} steps (−{short_kw:.1f} kW)"
            if hollow
            else "feasible on every step"
        )
        cards_html.append(
            f"""<div style="background:{pal.surface_raised};border:1px solid {pal.border};
                            border-radius:12px;padding:12px 14px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <span style="width:10px;height:10px;border-radius:3px;flex-shrink:0;
                             {swatch_style}"></span>
                <span style="font-size:12.5px;font-weight:600;color:{pal.text_secondary};">
                  {POWERTRAIN_NAMES[pt]}
                </span>
              </div>
              <div class="pwt-tabular" style="font-size:22px;font-weight:700;
                          letter-spacing:-0.025em;margin-top:4px;color:{pal.text_primary};">
                {val} <span style="font-size:12px;font-weight:500;color:{pal.text_muted};">
                  g CO₂/km
                </span>
              </div>
              <div style="font-size:11.5px;color:{pal.text_muted};margin-top:2px;">
                {feas}
              </div>
            </div>"""
        )

    st.html(
        f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
                        gap:10px;margin-bottom:10px;">
          {"".join(cards_html)}
        </div>"""
    )

    fig = charts.model_co2_bars(wltc, pal, height=230, show_footnote=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, theme=None)
    st.caption(
        "Model output (assignment vehicles, storage losses, EU grid 250 g CO₂/kWh, Plug-in hybrid R101-weighted). "
        "Outlined bars and * mark runs where the engine falls short of the trace (conditional result)."
    )


def _group_header(num: str, title: str, badge: str, badge_cls: str, pal: Palette) -> None:
    st.html(
        f"""<div style="display:flex;align-items:center;justify-content:space-between;
                        gap:10px;flex-wrap:wrap;margin:20px 0 8px;">
          <h2 style="margin:0;font-size:18px;font-weight:700;letter-spacing:-0.02em;
                     color:{pal.text_primary};">
            <span style="color:{pal.text_muted};font-size:13px;margin-right:8px;">{num}</span>
            {title}
          </h2>
          <span class="pwt-badge {badge_cls}">{badge}</span>
        </div>"""
    )


def _link_cards(items: list[tuple[str, str, str]], cols_per_row: int) -> None:
    for start in range(0, len(items), cols_per_row):
        chunk = items[start : start + cols_per_row]
        cols = st.columns(len(chunk))
        for col, (filename, label, desc) in zip(cols, chunk):
            with col:
                with st.container(border=True):
                    try:
                        st.page_link(f"views/{filename}", label=label, width="stretch")
                    except st.errors.StreamlitPageNotFoundError:
                        # Standalone run (e.g. AppTest directly on 0_Home.py without st.navigation)
                        st.markdown(f"**{label}**")
                    st.caption(desc)


pal = configure("Home")
_render_hero(pal)

# --- Entry links for the three menu groups --------------------------------------------------

_group_header("01", "Workbooks", "Reported figures", "pwt-badge-wb", pal)
_link_cards(
    [
        ("1_Overview.py", "Overview", "12 supplied runs in one matrix and grouped bar chart."),
        ("2_Category_View.py", "Category view", "Slice the 4×3 grid by powertrain or cycle."),
        ("3_Trace_Explorer.py", "Trace explorer", "Per-step speed, gear, force, and energy for one run."),
        ("4_Compare.py", "Compare", "Two workbooks side by side: reported figures, parameter differences and traces."),
        ("5_Data.py", "Data", "Raw runs, totals, parameters, traces, and workbook cells."),
    ],
    cols_per_row=5,
)

_group_header("02", "Model", "Model output · EU grid 250 g CO₂/kWh", "pwt-badge-model", pal)
_link_cards(
    [
        ("6_Model.py", "Model", "Five scenarios from workbook vehicles to storage losses."),
        ("8_Track_Map.py", "Track map", "Generated Spa-Francorchamps laps on the circuit."),
    ],
    cols_per_row=2,
)

_group_header("03", "Studies", "Model output · personal studies", "pwt-badge-draft", pal)
_link_cards(
    [
        ("7_Sizing.py", "Hybrid sizing", "Study A · battery and motor sizing sweep."),
        ("9_CO2_Sensitivity.py", "CO₂ sensitivity", "Study B · one-factor sensitivity and grid comparisons."),
        ("10_Cornering_Speed.py", "Cornering speed", "Study C · lap time and CO₂ vs tyre grip and downforce."),
    ],
    cols_per_row=3,
)

# --- Small WLTC baseline preview (Model output) ---------------------------------------------

st.divider()
_render_wltc_preview(_wltc_baseline(), pal)
