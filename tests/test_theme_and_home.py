"""Tests for the deck-aligned theme, chart redundancy/feasibility, and Home landing page."""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard import charts
from dashboard.loaders import trace_for
from dashboard.theme import (
    DARK,
    LIGHT,
    POWERTRAIN_DASHES,
    POWERTRAIN_MARKERS,
    POWERTRAIN_ORDER,
    ACCENT,
    ACCENT_INK,
    plotly_template,
    style_axes,
)
from pwt.build import runs_frame
from pwt.catalog import CATALOG, course_file
from pwt.deck.data import CAR_COLOURS, POWERTRAINS, baseline
from pwt.workbook import read_run

CONFIG_PATH = ROOT / ".streamlit" / "config.toml"
HOME = str(ROOT / "dashboard" / "views" / "0_Home.py")
OVERVIEW = str(ROOT / "dashboard" / "views" / "1_Overview.py")
ENTRY = str(ROOT / "dashboard" / "Overview.py")


def _rel_luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast_ratio(c1: str, c2: str) -> float:
    l1, l2 = sorted((_rel_luminance(c1), _rel_luminance(c2)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


@pytest.fixture(scope="module")
def runs():
    return runs_frame([read_run(course_file(e.filename)) for e in CATALOG])


@pytest.fixture(scope="module")
def lap():
    return trace_for.__wrapped__("petrol", "franco_eco")


# --- Task 1: Deck palette, config.toml, contrast, CVD redundancy ----------------------------


@pytest.mark.parametrize("pal", [DARK, LIGHT], ids=["dark", "light"])
def test_palette_powertrain_colours_match_deck(pal):
    assert POWERTRAIN_ORDER == POWERTRAINS
    for pt, expected in CAR_COLOURS.items():
        assert pal.for_powertrain(pt).lower() == expected.lower()


def test_dark_and_light_surfaces_match_deck():
    assert DARK.surface.lower() == "#000000"
    assert DARK.surface_raised.lower() == "#1c1c1e"
    assert DARK.border.lower() == "#2c2c2e"
    assert DARK.text_primary.lower() == "#f5f5f7"
    assert DARK.text_muted.lower() == "#86868b"

    assert LIGHT.surface.lower() == "#ffffff"
    assert LIGHT.surface_raised.lower() == "#f5f5f7"
    assert LIGHT.border.lower() == "#e5e5ea"
    assert LIGHT.text_primary.lower() == "#1d1d1f"


def test_config_toml_pins_dark_with_no_light_twin():
    """Owner decision D1: dark for every viewer, so no [theme.light] for Streamlit to follow."""
    cfg = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    theme = cfg["theme"]
    assert theme["base"] == "dark"
    assert theme["backgroundColor"].lower() == "#000000"
    assert theme["secondaryBackgroundColor"].lower() == "#1c1c1e"
    assert theme["textColor"].lower() == "#f5f5f7"

    dark = theme["dark"]
    assert dark["backgroundColor"].lower() == "#000000"
    assert dark["secondaryBackgroundColor"].lower() == "#1c1c1e"
    assert dark["textColor"].lower() == "#f5f5f7"
    assert dark["borderColor"].lower() == "#2c2c2e"

    assert "light" not in theme


@pytest.mark.parametrize("pal", [DARK, LIGHT], ids=["dark", "light"])
def test_palette_ink_and_primary_meet_wcag_aa(pal):
    for surface in (pal.surface, pal.surface_raised):
        assert _contrast_ratio(pal.text_primary, surface) >= 4.5
        assert _contrast_ratio(pal.text_secondary, surface) >= 4.5
        assert _contrast_ratio(pal.text_muted, surface) >= 4.5
    # The accent fills chips and active controls; its own ink sits on it.
    assert _contrast_ratio(pal.primary, pal.surface) >= 4.5
    assert _contrast_ratio(pal.primary_ink, pal.primary) >= 4.5


def test_config_primary_and_links_meet_wcag_aa():
    cfg = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for section in (cfg["theme"], cfg["theme"]["dark"]):
        primary = section["primaryColor"]
        bg = section["backgroundColor"]
        raised = section["secondaryBackgroundColor"]
        link = section["linkColor"]
        assert _contrast_ratio(ACCENT_INK, primary) >= 4.5, "ink on primary"
        assert _contrast_ratio(primary, bg) >= 4.5, "primary on bg"
        assert _contrast_ratio(link, bg) >= 4.5, "link on bg"
        assert _contrast_ratio(link, raised) >= 4.5, "link on raised"


def test_accent_is_not_a_powertrain_colour():
    cfg = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cars = {c.lower() for c in CAR_COLOURS.values()}
    assert ACCENT.lower() == "#d1d1d6"
    assert ACCENT.lower() not in cars
    assert cfg["theme"]["primaryColor"].lower() == ACCENT.lower()
    assert cfg["theme"]["dark"]["primaryColor"].lower() == ACCENT.lower()
    for pal in (DARK, LIGHT):
        assert pal.primary.lower() not in cars


def test_accent_contrast():
    assert _contrast_ratio(ACCENT, "#000000") >= 4.5
    assert _contrast_ratio(ACCENT_INK, ACCENT) >= 4.5


@pytest.mark.parametrize("pal", [DARK, LIGHT], ids=["dark", "light"])
def test_css_paints_active_controls_with_the_accent_and_tames_code(pal, monkeypatch):
    from dashboard import layout

    seen = []
    monkeypatch.setattr(layout.st, "html", lambda body: seen.append(body))
    layout.inject_css(pal)
    css = "".join(seen)
    # Selectors taken from the live Streamlit 1.66 DOM (27 Nov 2026): the active segmented
    # control is button[data-variant=...][aria-checked="true"] (no `kind` attribute), and a
    # multiselect chip is span[data-tag] inside stMultiSelectTagsContainer.
    assert "segmented_controlActive" not in css
    active = css.split('button[data-variant="segmented_control"][aria-checked="true"]', 1)[1]
    active = active.split("}", 1)[0]
    assert f"background-color: {pal.primary}" in active
    assert f"color: {pal.primary_ink}" in active
    chip = css.split('[data-testid="stMultiSelectTagsContainer"] [data-tag]', 1)[1].split("}", 1)[0]
    assert f"color: {pal.primary_ink}" in chip
    assert ".stApp code" in css
    assert pal.primary in css and pal.primary_ink in css


def test_cvd_redundancy_separates_bev_and_phev():
    assert POWERTRAIN_DASHES["bev"] != POWERTRAIN_DASHES["phev"]
    assert POWERTRAIN_MARKERS["bev"] != POWERTRAIN_MARKERS["phev"]
    assert len(set(POWERTRAIN_DASHES.values())) == 4
    assert len(set(POWERTRAIN_MARKERS.values())) == 4
    assert DARK.dash_for_powertrain("bev") != DARK.dash_for_powertrain("phev")
    assert DARK.marker_for_powertrain("bev") != DARK.marker_for_powertrain("phev")


def test_plotly_template_uses_subdued_grid_and_no_placeholder_colorway(lap):
    for pal in (DARK, LIGHT):
        tpl = plotly_template(pal)
        assert tpl.layout.colorway is None
        assert tpl.layout.xaxis.showgrid is False
        assert tpl.layout.yaxis.showgrid is True
        assert tpl.layout.yaxis.gridcolor == pal.grid
        fig = charts.gear_steps(lap, "distance_m", pal)
        style_axes(fig, pal)
        assert fig.layout.template.layout.colorway is None


def test_palette_respects_live_light_theme(monkeypatch):
    """Switching to light in Streamlit settings must return LIGHT even when config base=dark."""
    import types
    import streamlit as st
    from dashboard.theme import palette

    fake_ctx = types.SimpleNamespace(theme=types.SimpleNamespace(type="light"))
    monkeypatch.setattr(st, "context", fake_ctx)
    monkeypatch.setattr(st, "get_option", lambda _k: "dark")
    assert palette() == LIGHT


# --- Task 2: charts.py dash redundancy, hollow infeasible bars, narrow gap marker -----------


def test_compare_traces_separates_same_powertrain_with_dashes_and_markers(lap):
    same_colour = DARK.for_powertrain("petrol")
    fig = charts.compare_traces(
        lap, lap, "speed_kph", "distance_m",
        ("Petrol eco", "Petrol sport"),
        (same_colour, same_colour),
        DARK,
    )
    assert len(fig.data) == 2
    assert fig.data[0].line.dash != fig.data[1].line.dash
    assert fig.data[0].marker.symbol != fig.data[1].marker.symbol


def test_trace_lines_uses_distinct_dashes_and_markers(lap):
    fig = charts.trace_lines(lap, ["speed_kph", "altitude_m", "engine_power_w"], "distance_m", DARK)
    dashes = [t.line.dash for t in fig.data]
    symbols = [t.marker.symbol for t in fig.data]
    assert len(set(dashes)) == 3
    assert len(set(symbols)) == 3


def test_force_breakdown_uses_distinct_dashes(lap):
    fig = charts.force_breakdown(lap, "distance_m", DARK)
    dashes = [t.line.dash for t in fig.data]
    assert len(dashes) >= 2
    assert len(set(dashes)) == len(dashes)


def test_overlay_traces_uses_distinct_marker_symbols(lap):
    fig = charts.overlay_traces(
        [lap, lap, lap, lap],
        ["Petrol", "Full hybrid", "Plug-in hybrid", "Battery electric"],
        [DARK.for_powertrain(pt) for pt in POWERTRAIN_ORDER],
        "speed_kph", "distance_m", DARK,
    )
    symbols = [t.marker.symbol for t in fig.data]
    assert len(set(symbols)) == 4


def test_grouped_totals_uses_short_gap_marker_not_long_text(runs):
    gaps = {("phev", "nedc")}
    fig = charts.grouped_totals(runs, "co2_g_per_km", DARK, unit="g CO₂/km", gaps=gaps)
    phev = next(b for b in fig.data if b.name == "Plug-in hybrid")
    labels = list(phev.text)
    assert charts.GAP_MARKER in labels
    assert charts.GAP_LABEL not in labels
    assert any(charts.GAP_LABEL in (a.text or "") for a in fig.layout.annotations)


def test_grouped_totals_and_model_bars_outline_infeasible_runs():
    wltc = baseline().query("cycle == 'wltc'")
    fig = charts.model_co2_bars(wltc, DARK)
    assert len(fig.data) == 4
    by_name = {trace.name: trace for trace in fig.data}
    # Petrol and PHEV are short on WLTC; hybrid and BEV are feasible.
    assert by_name["Petrol"].text[0].endswith("*")
    assert by_name["Plug-in hybrid"].text[0].endswith("*")
    assert not by_name["Full hybrid"].text[0].endswith("*")
    assert not by_name["Battery electric"].text[0].endswith("*")
    # Hollow outlined bars use a tinted/transparent fill and car-coloured stroke.
    assert by_name["Petrol"].marker.color != DARK.for_powertrain("petrol")
    assert by_name["Petrol"].marker.line.color == DARK.for_powertrain("petrol")
    assert by_name["Full hybrid"].marker.color == DARK.for_powertrain("hybrid")


# --- Task 3 & 4: Sidebar auto, Home page, Overview ordering and nav caption -----------------


def test_sidebar_initial_state_is_auto():
    source = (ROOT / "dashboard" / "layout.py").read_text(encoding="utf-8")
    assert 'initial_sidebar_state="auto"' in source
    assert 'initial_sidebar_state="expanded"' not in source


def test_static_hero_assets_exist():
    assets = ROOT / "dashboard" / "assets"
    assert (assets / "spa-hero-dark.png").is_file()
    assert (assets / "spa-hero-light.png").is_file()


def test_home_page_renders_with_wltc_preview_and_links():
    app = AppTest.from_file(HOME, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    # Header hero and WLTC preview rendered via HTML/markdown/captions
    html_text = " ".join(getattr(h, "value", "") or getattr(h, "body", "") for h in app.html)
    all_text = " ".join([
        html_text,
        *(m.value for m in app.markdown),
        *(c.value for c in app.caption),
    ])
    assert "Four cars. Four cycles." in all_text
    assert "Model output" in all_text
    # The WLTC values sit on the chart; infeasible runs carry the '*' convention.
    bar_labels = " ".join(
        str(t) for chart in app.get("plotly_chart")
        for trace in __import__("json").loads(chart.proto.spec)["data"]
        for t in (trace.get("text") or [])
    )
    assert "145.1*" in bar_labels
    assert "73.6*" in bar_labels
    assert "128.8" in bar_labels
    assert "45.8" in bar_labels


def test_entry_point_defaults_to_home():
    app = AppTest.from_file(ENTRY, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    html_text = " ".join(getattr(h, "value", "") or getattr(h, "body", "") for h in app.html)
    assert "Four cars. Four cycles." in html_text
    # Three task links; the sidebar already lists every page.
    assert len(app.get("page_link")) == 3


def test_overview_nav_caption_and_matrix_above_elevation():
    source = Path(OVERVIEW).read_text(encoding="utf-8")
    # Matrix dataframe must be rendered before the elevation_strip call
    assert source.index("st.dataframe(display") < source.index("elevation_strip(")

    app = AppTest.from_file(OVERVIEW, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    captions = " ".join(c.value for c in app.caption)
    assert "Sizing, Track map and Study B" not in captions
