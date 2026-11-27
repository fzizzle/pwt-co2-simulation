"""Shared page furniture: the header, the sidebar controls, and small display helpers.

Kept in one place so every page carries the same controls in the same order and the same
vocabulary. Wording rule followed here: label things by what the reader recognises — "Fuel
consumption", not "total consumption [l/100km]".
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.charts import GAP_LABEL
from dashboard.labels import column as column_label
from dashboard.labels import figure, parameter, sheet_label
from dashboard.theme import FONT_STACK, POWERTRAIN_ORDER, Palette, palette
from pwt.catalog import CYCLE_NAMES, POWERTRAIN_NAMES

#: The four canonical figures, with the display name and unit the reader sees.
CANONICAL_QUANTITIES: dict[str, tuple[str, str]] = {
    "co2_g_per_km": ("CO₂ emissions", "g CO₂/km"),
    "consumption_l_per_100km": ("Fuel consumption", "l/100 km"),
    "energy_wh_per_100km": ("Electrical energy", "Wh/100 km"),
    "co2_g_total": ("Total CO₂", "g CO₂"),
}

#: Display names for the columns a chart can be plotted against.
X_LABELS: dict[str, str] = {c: column_label(c) for c in ("distance_m", "time_s", "step")}


#: Plain definitions of the three supplied workbook cycles.
CYCLE_DEFINITIONS: dict[str, str] = {
    "nedc": (
        "NEDC stands for New European Driving Cycle. The laboratory cycle has four urban "
        "segments and one extra-urban segment up to 120 km/h, at 0 m altitude."
    ),
    "franco_eco": (
        "The workbook records the Spa-Francorchamps eco lap in segments of different lengths."
    ),
    "franco_sport": (
        "The sport lap uses the same route as the eco lap, with a different speed trace."
    ),
}


def cycle_facts(trace: pd.DataFrame) -> str:
    """One line of measured facts about a cycle, computed from the trace itself."""
    speed = trace.get("speed_kph")
    if speed is None or speed.empty:
        return ""
    bits = [f"{len(trace)} steps"]

    # Distance is cumulative in the lap workbooks and per-step in the NEDC ones, so take
    # whichever reading that column actually supports rather than assuming one.
    distance = trace.get("distance_m")
    if distance is not None and distance.notna().any():
        metres = (
            distance.max() if distance.dropna().is_monotonic_increasing else distance.sum()
        )
        bits.append(f"{metres / 1000:.1f} km")

    time = trace.get("time_s")
    if time is not None and time.notna().any():
        bits.append(f"{time.max() / 60:.1f} min")

    bits.append(f"average {speed.mean():.0f} km/h, peak {speed.max():.0f} km/h")

    stopped = int((speed == 0).sum())
    if stopped:
        bits.append(f"stationary for {stopped} of {len(trace)} steps")

    altitude = trace.get("altitude_m")
    if altitude is not None and altitude.notna().any():
        spread = altitude.max() - altitude.min()
        bits.append("flat" if spread == 0 else f"{spread:.0f} m of elevation range")

    return " · ".join(bits)


#: Runs whose reported figures leave something out, keyed by (powertrain, cycle): the one
#: sentence shown in the warning, and the explanation behind an "Electricity accounting" toggle.
#: Kept here in the dashboard package so Community Cloud picks it up without a reboot.
#: Workbook pages must state only what the workbook reports and omit model-derived figures.
RUN_NOTICES: dict[tuple[str, str], tuple[str, str]] = {
    ("phev", "nedc"): (
        "electricity not counted. The workbook reports 0 l/100 km and 0 g CO₂/km.",
        "**Electricity not counted.** `34 NEDC PHYBRID engine.xlsx` reports 0 l/100 km and "
        "0 g CO₂/km. Its 40 kW motor covers every step and battery state of charge falls from "
        "98% to 78%, above its 23% engine threshold. The workbook omits the electricity drawn "
        "from the battery. See the **Model** page for computed electricity and CO₂ figures.",
    ),
}


def run_notice(powertrain: str | None, cycle: str | None) -> tuple[str, str] | None:
    return RUN_NOTICES.get((powertrain or "", cycle or ""))


def mark_gap_value(
    value: float | None,
    powertrain: str | None,
    cycle: str | None,
) -> str:
    """Format a reported figure for display, labelling a known gap in place.

    A figure the workbook does not report becomes an em dash. A figure from a run flagged in
    RUN_NOTICES keeps its value but carries `GAP_LABEL`, so a zero that leaves the electricity
    out cannot be read as the run's whole footprint.
    """
    if value is None or pd.isna(value):
        return "—"
    formatted = figure(value)
    return f"{formatted} — {GAP_LABEL}" if run_notice(powertrain, cycle) else formatted


def render_run_notices(*runs: pd.Series) -> None:
    """Warn about any run on screen whose figures leave something out."""
    seen: set[tuple[str, str]] = set()
    for row in runs:
        key = (row.get("powertrain") or "", row.get("cycle") or "")
        if key in seen:
            continue
        seen.add(key)
        notice = RUN_NOTICES.get(key)
        if notice:
            short, why = notice
            st.warning(f"**{run_label(*key)}** — {short}", icon="⚠️")
            with st.expander("Electricity accounting"):
                st.markdown(why)


def inject_css(pal: Palette) -> None:
    """Apply deck typography, tabular numerals, WCAG-AA active controls, and card tokens."""
    is_dark = pal.name == "dark"
    link_fg = "#6eb4fa" if is_dark else "#1f63a8"
    badge_wb_fg = "#e2b36a" if is_dark else "#7a5210"
    badge_model_fg = "#7bb4ec" if is_dark else "#1b5594"
    badge_draft_fg = "#cfa2e5" if is_dark else "#6c3688"
    st.html(
        f"""<style>
        .stApp, .stApp button, .stApp input, .stApp select {{
            font-family: {FONT_STACK};
            -webkit-font-smoothing: antialiased;
        }}
        .stMetricValue, [data-testid="stMetricValue"], .pwt-tabular {{
            font-variant-numeric: tabular-nums;
        }}
        /* Active segmented controls and pills, filled with the accent and its own ink.
           Selectors come from the live Streamlit 1.66 DOM: the selected button carries
           data-variant and aria-checked, not a `kind` attribute. */
        .stApp button[data-variant="segmented_control"][aria-checked="true"],
        .stApp button[data-variant="pills"][aria-checked="true"] {{
            background-color: {pal.primary} !important;
            color: {pal.primary_ink} !important;
            border-color: {pal.primary} !important;
            font-weight: 600 !important;
        }}
        /* Multiselect chips: Streamlit fills them with primaryColor but forces white text,
           which is unreadable on silver. Give the chip, its label and its close icon the ink. */
        [data-testid="stMultiSelectTagsContainer"] [data-tag],
        [data-testid="stMultiSelectTagsContainer"] [data-tag] * {{
            background-color: {pal.primary};
            color: {pal.primary_ink} !important;
            fill: {pal.primary_ink} !important;
        }}
        [data-testid="stMultiSelectTagsContainer"] [data-tag] * {{
            background-color: transparent;
        }}
        /* Inline code (file names, formulas) in quiet greys instead of Streamlit's green. */
        .stApp code {{
            background-color: {pal.surface_raised} !important;
            color: {pal.text_secondary} !important;
            border: 1px solid {pal.border};
            border-radius: 5px;
            padding: 1px 5px;
        }}
        /* Keep caption hyperlinks at full contrast instead of inheriting 0.6 opacity. */
        [data-testid="stCaptionContainer"] {{
            color: {pal.text_muted} !important;
            opacity: 1 !important;
        }}
        [data-testid="stCaptionContainer"] a {{
            color: {link_fg} !important;
            opacity: 1 !important;
            text-decoration: underline;
        }}
        /* Provenance pills & Keynote Darkroom cards (used by Home and shared headers). */
        .pwt-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 11.5px;
            font-weight: 600;
            border: 1px solid {pal.border};
            background: {pal.surface_raised};
            color: {pal.text_secondary};
            white-space: nowrap;
        }}
        .pwt-badge-wb {{
            border-color: rgba(208, 149, 57, 0.5);
            color: {badge_wb_fg};
            background: rgba(208, 149, 57, 0.12);
        }}
        .pwt-badge-model {{
            border-color: rgba(57, 132, 208, 0.5);
            color: {badge_model_fg};
            background: rgba(57, 132, 208, 0.12);
        }}
        .pwt-badge-draft {{
            border-color: rgba(182, 119, 213, 0.5);
            color: {badge_draft_fg};
            background: rgba(182, 119, 213, 0.12);
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {pal.border} !important;
            border-radius: 14px !important;
        }}
        </style>"""
    )


def configure(title: str) -> Palette:
    """Page config plus the active palette. Call first in every page."""
    st.set_page_config(
        page_title=f"{title} · PWT CO₂ simulation",
        page_icon="🛞",
        layout="wide",
        initial_sidebar_state="auto",
    )
    pal = palette()
    inject_css(pal)
    return pal


def _rgba(hex_colour: str, alpha: float) -> str:
    """A hex colour as rgba(), so fills track the active palette instead of being hardcoded."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def elevation_strip(trace: pd.DataFrame, pal: Palette) -> go.Figure | None:
    """The Spa elevation profile as a thin band.

    This is the recurring motif of the tool and it is real data, not ornament: the altitude
    column drives the grade term, which is why the same car returns different figures on the
    lap and on NEDC. Drawn flat and quiet so it frames the page without competing with it.
    """
    if "altitude_m" not in trace.columns or trace["altitude_m"].isna().all():
        return None
    x = "distance_m" if "distance_m" in trace.columns else "step"
    accent = pal.for_powertrain("bev")
    fig = go.Figure()
    fig.add_scatter(
        x=trace[x],
        y=trace["altitude_m"],
        mode="lines",
        line=dict(color=accent, width=1.5),  # linear: smoothing would misstate the profile
        fill="tozeroy",
        fillcolor=_rgba(accent, 0.14),
        hoverinfo="skip",
    )
    low, high = trace["altitude_m"].min(), trace["altitude_m"].max()
    fig.update_layout(
        height=64,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[low - (high - low) * 0.4, high + (high - low) * 0.2]),
    )
    return fig


def run_label(powertrain: str, cycle: str) -> str:
    return f"{POWERTRAIN_NAMES.get(powertrain, powertrain)} · {CYCLE_NAMES.get(cycle, cycle)}"


def varying_parameters(runs: pd.DataFrame) -> pd.DataFrame:
    """Parameters that are not identical across every run given.

    A parameter counts as varying when the runs disagree on its value, or when some runs carry
    it and others do not — a plug-in hybrid has a battery mass that a petrol car has no row
    for, and that absence is a real difference, not a match. Values are compared as the
    workbooks report them; nothing is rounded to force agreement beyond float noise.
    """
    if len(runs) < 2:
        return pd.DataFrame()

    labels = [run_label(row["powertrain"], row["cycle"]) for _, row in runs.iterrows()]
    records = []
    for column in (c for c in runs.columns if c.startswith("param:")):
        values = [runs.iloc[i][column] for i in range(len(runs))]
        present = [v for v in values if pd.notna(v)]
        if not present:
            continue
        distinct = {round(float(v), 9) for v in present}
        if len(distinct) == 1 and len(present) == len(values):
            continue  # every run agrees and none is missing it
        record = {"Parameter": parameter(column.removeprefix("param:"))}
        record.update(dict(zip(labels, values)))
        record["Distinct values"] = len(distinct)
        record["_missing"] = len(values) - len(present)
        records.append(record)

    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    return (
        frame.sort_values(
            ["Distinct values", "_missing", "Parameter"], ascending=[False, False, True]
        )
        .drop(columns="_missing")
        .reset_index(drop=True)
    )


#: Persistent session-state keys for compatible workbook selections across pages.
#: Stored separately from widget keys because Streamlit clears unmounted widget keys on navigation.
WB_POWERTRAINS_KEY = "_pwt_wb_powertrains"
WB_CYCLES_KEY = "_pwt_wb_cycles"
WB_MEASURE_KEY = "_pwt_wb_measure"
WB_TRACE_RUN_KEY = "_pwt_wb_trace_run"
WB_CMP_LEFT_KEY = "_pwt_wb_cmp_left"
WB_CMP_RIGHT_KEY = "_pwt_wb_cmp_right"

_WB_WIDGET_PREFIXES = (
    "wb_filter_powertrains",
    "wb_filter_cycles",
    "wb_measure_",
    "trace_run",
    "cmp_left",
    "cmp_right",
)


def reset_workbook_selections() -> None:
    """Restore shared workbook filter, measure and run selections to their defaults."""
    for key in (
        WB_POWERTRAINS_KEY,
        WB_CYCLES_KEY,
        WB_MEASURE_KEY,
        WB_TRACE_RUN_KEY,
        WB_CMP_LEFT_KEY,
        WB_CMP_RIGHT_KEY,
    ):
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith(_WB_WIDGET_PREFIXES):
            st.session_state.pop(key, None)


def sidebar_reset_button(key_suffix: str = "") -> None:
    """Sidebar button to restore all persisted workbook selections."""
    btn_key = f"wb_reset_btn_{key_suffix}" if key_suffix else "wb_reset_btn"
    st.sidebar.button(
        "Reset selections",
        key=btn_key,
        on_click=reset_workbook_selections,
        width="stretch",
    )


def sidebar_filters(runs: pd.DataFrame, *, key_prefix: str = "wb") -> tuple[list[str], list[str]]:
    """Powertrain and cycle selection, persisted across workbook pages with a reset."""
    valid_pts = list(POWERTRAIN_ORDER)
    valid_cycles = list(CYCLE_NAMES)
    pts_key = f"wb_filter_powertrains_{key_prefix}"
    cyc_key = f"wb_filter_cycles_{key_prefix}"

    if WB_POWERTRAINS_KEY in st.session_state:
        saved_pts = [p for p in st.session_state[WB_POWERTRAINS_KEY] if p in valid_pts]
    else:
        saved_pts = valid_pts
    if WB_CYCLES_KEY in st.session_state:
        saved_cycles = [c for c in st.session_state[WB_CYCLES_KEY] if c in valid_cycles]
    else:
        saved_cycles = valid_cycles

    if pts_key not in st.session_state:
        st.session_state[pts_key] = list(saved_pts)
    if cyc_key not in st.session_state:
        st.session_state[cyc_key] = list(saved_cycles)

    powertrains = st.sidebar.multiselect(
        "Powertrains",
        options=valid_pts,
        key=pts_key,
        format_func=lambda p: POWERTRAIN_NAMES[p],
    )
    cycles = st.sidebar.multiselect(
        "Driving cycles",
        options=valid_cycles,
        key=cyc_key,
        format_func=lambda c: CYCLE_NAMES[c],
    )
    st.session_state[WB_POWERTRAINS_KEY] = list(powertrains)
    st.session_state[WB_CYCLES_KEY] = list(cycles)
    sidebar_reset_button(key_prefix)
    return powertrains, cycles


def measure_picker(
    container,
    *,
    key: str,
    widget: str = "radio",
    label: str = "Measure",
    label_visibility: str = "visible",
) -> str:
    """Canonical workbook measure selector, persisted across workbook pages."""
    options = list(CANONICAL_QUANTITIES)
    saved = st.session_state.get(WB_MEASURE_KEY, options[0])
    if saved not in options:
        saved = options[0]
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = saved
    if widget == "selectbox":
        choice = container.selectbox(
            label,
            options=options,
            key=key,
            format_func=lambda q: CANONICAL_QUANTITIES[q][0],
            label_visibility=label_visibility,
        )
    else:
        choice = container.radio(
            label,
            options=options,
            key=key,
            format_func=lambda q: CANONICAL_QUANTITIES[q][0],
            label_visibility=label_visibility,
        )
    st.session_state[WB_MEASURE_KEY] = choice
    return choice


def run_picker(
    runs: pd.DataFrame,
    label: str,
    *,
    key: str,
    index: int = 0,
    persist_key: str | None = None,
) -> pd.Series:
    """Pick a single run. Persists across pages when `persist_key` is given."""
    options = list(runs.index)
    default_value = options[min(index, len(options) - 1)]
    if persist_key is not None:
        saved = st.session_state.get(persist_key, default_value)
        if saved not in options:
            saved = default_value
        if key not in st.session_state or st.session_state[key] not in options:
            st.session_state[key] = saved
        choice = st.selectbox(
            label,
            options=options,
            key=key,
            format_func=lambda i: run_label(runs.loc[i, "powertrain"], runs.loc[i, "cycle"]),
        )
        st.session_state[persist_key] = choice
    else:
        choice = st.selectbox(
            label,
            options=options,
            index=min(index, len(options) - 1),
            key=key,
            format_func=lambda i: run_label(runs.loc[i, "powertrain"], runs.loc[i, "cycle"]),
        )
    return runs.loc[choice]


def source_caption(*rows: pd.Series) -> None:
    """Name the workbook every figure on screen came from."""
    files = [f"`{row['source_file']}`" for row in rows]
    prefix = "Workbook: " if len(files) == 1 else "Workbooks: "
    st.caption(prefix + " · ".join(files))


def download(frame: pd.DataFrame, filename: str, label: str = "Download CSV") -> None:
    st.download_button(
        label,
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def data_notes(runs: pd.DataFrame) -> list[str]:
    """Plain statements about what the selected cells contain.

    Descriptive only — it says a figure is zero or negative so an empty or inverted bar is not
    mistaken for a rendering fault. It does not explain why, or what it would be if corrected.
    """
    notes: list[str] = []
    for _, row in runs.iterrows():
        if run_notice(row["powertrain"], row["cycle"]):
            continue  # already stated in full by its own notice
        name = run_label(row["powertrain"], row["cycle"])
        zeros = [
            f"{display} (0 {unit})"
            for column, (display, unit) in CANONICAL_QUANTITIES.items()
            if pd.notna(row.get(column)) and row[column] == 0
        ]
        negatives = [
            sheet_label(column.removeprefix("total:"))
            for column in runs.columns
            if column.startswith("total:") and pd.notna(row.get(column)) and row[column] < 0
        ]
        if zeros:
            notes.append(f"**{name}** reports {', '.join(zeros)}.")
        if negatives:
            notes.append(f"**{name}** reports a negative value for {', '.join(negatives)}.")
    return notes
