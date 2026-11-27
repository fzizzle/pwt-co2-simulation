"""Tests for track-map framing, controls, workbook fidelity, strip metric and contrast."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.loaders import trace_for
from dashboard.theme import DARK
from dashboard.track_charts import (
    DIVERGING,
    SEQUENTIAL,
    fit_camera,
    lap_map,
    metric_strip,
    metrics,
    project_to_pixels,
)
from pwt.phase2 import result_for
from pwt.trackmap import LANDMARKS, outline, place

PAGES = ROOT / "dashboard" / "views"


def _luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# --- Task 1: camera fitting & no cropping ----------------------------------------------------


@pytest.mark.parametrize(
    "width_px, height_px, pad_x, pad_y",
    [
        (320, 460, 36, 30),
        (360, 480, 40, 32),
        (480, 500, 44, 34),
        (760, 500, 44, 34),
        (1276, 500, 44, 34),
    ],
)
def test_fit_camera_keeps_full_outline_and_extreme_corners_inside(
    width_px: int, height_px: int, pad_x: int, pad_y: int
):
    track = outline()
    cam = fit_camera(track, width_px=width_px, height_px=height_px, pad_x=pad_x, pad_y=pad_y)
    assert cam["bearing"] == 0
    assert cam["pitch"] == 0

    px, py = project_to_pixels(track["lat"].to_numpy(), track["lon"].to_numpy(), cam, width_px, height_px)
    assert px.min() >= pad_x - 0.5
    assert px.max() <= width_px - pad_x + 0.5
    assert py.min() >= pad_y - 0.5
    assert py.max() <= height_px - pad_y + 0.5

    # Specifically verify La Source (top/north) and Bruxelles (bottom/south) are inside.
    la_source_d = next(d for d, name in LANDMARKS.items() if name == "La Source")
    bruxelles_d = next(d for d, name in LANDMARKS.items() if name == "Bruxelles")
    lm_lat, lm_lon = place(np.array([la_source_d, bruxelles_d], dtype=float))
    lm_x, lm_y = project_to_pixels(lm_lat, lm_lon, cam, width_px, height_px)
    assert (lm_x >= pad_x - 0.5).all() and (lm_x <= width_px - pad_x + 0.5).all()
    assert (lm_y >= pad_y - 0.5).all() and (lm_y <= height_px - pad_y + 0.5).all()
    # North up: La Source must sit above Bruxelles (smaller pixel y).
    assert lm_y[0] < lm_y[1]


def test_lap_map_places_colorbar_below_map_and_has_no_plotly_overlap_controls():
    wb = trace_for.__wrapped__("petrol", "franco_eco")
    vals, unit, div = metrics(wb, source="workbook")["Speed"]
    fig = lap_map(wb, vals, "Speed", unit, div, DARK, source="workbook", width_px=360, basemap="tiles")

    # Map domain leaves room below for the horizontal colourbar.
    map_y0, map_y1 = fig.layout.map.domain.y
    assert map_y0 > 0.08
    assert map_y1 == pytest.approx(1.0)

    # Colourbar is horizontal and sits below the map domain, never on top of the track.
    cb_traces = [t for t in fig.data if getattr(t, "marker", None) and getattr(t.marker, "colorbar", None) and t.marker.colorbar.title.text]
    assert len(cb_traces) == 1
    cb = cb_traces[0].marker.colorbar
    assert cb.orientation == "h"
    assert cb.y < map_y0
    assert "Speed" in cb.title.text and "km/h" in cb.title.text

    # No Plotly SVG buttons or sliders overlapping the map.
    assert not fig.layout.updatemenus
    assert not fig.layout.sliders


# --- Task 3: painted-metric strip & only available measures ----------------------------------


def test_metric_strip_plots_selected_measure_not_always_speed():
    wb = trace_for.__wrapped__("petrol", "franco_eco")
    vals, unit, div = metrics(wb, source="workbook")["Altitude"]
    fig = metric_strip(wb, vals, "Altitude", unit, div, DARK, car_index=5, source="workbook")

    y_vals = np.asarray(fig.data[0].y, dtype=float)
    assert np.allclose(y_vals, wb["altitude_m"].to_numpy())
    assert "Altitude" in fig.layout.yaxis.title.text
    assert "m" in fig.layout.yaxis.title.text
    # Vertical cursor sits at the selected car step's distance.
    expected_km = float(wb["distance_m"].iloc[5]) / 1000.0
    cursor_xs = [float(t.x[0]) for t in fig.data[1:] if len(t.x) >= 1]
    assert any(abs(x - expected_km) < 1e-6 for x in cursor_xs)


def test_petrol_never_offers_battery_charge():
    wb_petrol = trace_for.__wrapped__("petrol", "franco_eco")
    assert "Battery state of charge" not in metrics(wb_petrol, source="workbook")

    mod_petrol = result_for("petrol", "franco_sport_generated", "storage losses").steps
    assert "Battery state of charge" not in metrics(mod_petrol, source="model")


# --- Task 4: workbook maps vs model maps fidelity --------------------------------------------


def test_workbook_metrics_use_exact_reported_columns_and_units():
    wb_petrol = trace_for.__wrapped__("petrol", "franco_eco")
    m_petrol = metrics(wb_petrol, source="workbook")
    assert "CO₂ per segment distance" not in m_petrol
    assert m_petrol["Speed"][1] == "km/h"
    assert m_petrol["Power demand"][1] == "W"
    assert np.allclose(m_petrol["Power demand"][0].to_numpy(), wb_petrol["engine_power_drivetrain_w"].to_numpy())
    assert m_petrol["CO₂ emitted"][1] == "g"
    assert np.allclose(m_petrol["CO₂ emitted"][0].to_numpy(), wb_petrol["emission_g_co2"].to_numpy())
    assert m_petrol["Altitude"][1] == "m"
    assert "Battery state of charge" not in m_petrol

    wb_hybrid = trace_for.__wrapped__("hybrid", "franco_eco")
    m_hybrid = metrics(wb_hybrid, source="workbook")
    assert "CO₂ per segment distance" not in m_hybrid
    assert m_hybrid["Battery state of charge"][1] == "fraction"
    assert np.allclose(m_hybrid["Battery state of charge"][0].to_numpy(), wb_hybrid["batt_soc"].to_numpy())

    wb_bev = trace_for.__wrapped__("bev", "franco_eco")
    m_bev = metrics(wb_bev, source="workbook")
    assert "CO₂ per segment distance" not in m_bev
    assert "Battery state of charge" not in m_bev
    assert m_bev["CO₂ from the grid"][1] == "g"
    assert np.allclose(m_bev["CO₂ from the grid"][0].to_numpy(), wb_bev["co2_g"].to_numpy())


def test_model_metrics_keep_derived_measures():
    mod_hybrid = result_for("hybrid", "franco_sport_generated", "storage losses").steps
    m = metrics(mod_hybrid, source="model")
    assert m["Power demand"][1] == "kW"
    assert m["CO₂ per segment distance"][1] == "g CO₂/km"
    assert m["Battery state of charge"][1] == "%"


def test_workbook_map_hover_is_only_on_reported_segment_ends():
    wb = trace_for.__wrapped__("petrol", "franco_eco")
    vals, unit, div = metrics(wb, source="workbook")["Power demand"]
    fig = lap_map(wb, vals, "Power demand", unit, div, DARK, source="workbook", basemap="tiles")

    # Find every trace with a data hovertemplate (excluding landmark tooltips).
    data_hover_traces = [
        t for t in fig.data
        if t.hoverinfo != "skip" and t.hovertemplate and "Power demand" in t.hovertemplate
    ]
    assert len(data_hover_traces) == 1
    assert len(data_hover_traces[0].lat) == len(wb)


# --- Task 5: contrast & 8_Track_Map style_axes -----------------------------------------------


def test_colour_scales_clear_wcag_non_text_contrast():
    for _, colour in [*SEQUENTIAL, *DIVERGING]:
        assert _contrast(colour, "#1a1a19") >= 3.0, f"{colour} fails 3:1 vs #1a1a19"
        assert _contrast(colour, "#000000") >= 3.0, f"{colour} fails 3:1 vs #000000"


def test_map_has_dark_halo_behind_car_and_labels():
    wb = trace_for.__wrapped__("petrol", "franco_eco")
    vals, unit, div = metrics(wb, source="workbook")["Speed"]
    fig = lap_map(wb, vals, "Speed", unit, div, DARK, source="workbook", basemap="tiles")

    # Car marker: outer dark dot larger than inner bright dot at the exact same coordinate.
    dark_car = [t for t in fig.data if t.mode == "markers" and len(t.lat) == 1 and t.marker.size >= 18]
    bright_car = [t for t in fig.data if t.mode == "markers" and len(t.lat) == 1 and 10 <= t.marker.size < 18]
    assert dark_car and bright_car
    assert dark_car[0].marker.color in ("#000000", "#0b0b0c")
    assert bright_car[0].marker.color == "#ffffff"

    # Corner labels: dark shadow/halo text trace(s) exist behind white text trace(s).
    text_traces = [t for t in fig.data if t.mode and "text" in t.mode]
    dark_text = [t for t in text_traces if t.textfont.color in ("#000000", "#0b0b0c")]
    light_text = [t for t in text_traces if t.textfont.color == "#ffffff"]
    assert dark_text and light_text


# --- Integration: Streamlit pages & native playback controls ---------------------------------


def test_workbook_pages_never_offer_derived_co2_or_missing_soc():
    app = AppTest.from_file(str(PAGES / "3_Trace_Explorer.py"), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    paint = next(b for b in app.button_group if b.label == "Map colour")
    assert "CO₂ per segment distance" not in paint.options
    assert "Battery state of charge" not in paint.options
    # Native keyboard-accessible slider and playback buttons exist.
    assert len(app.slider) >= 1
    assert any("Play" in b.label for b in app.button)
    # Scrubbing to the final step works without error.
    slider = app.slider[0]
    slider.set_value(slider.max).run()
    assert not app.exception, [e.value for e in app.exception]


def test_track_map_page_offers_model_measures_and_calls_style_axes(monkeypatch):
    from dashboard import theme

    styled: list[str] = []
    original = theme.style_axes

    def spy(fig, pal, *, x_title="", y_title=""):
        styled.append(x_title)
        return original(fig, pal, x_title=x_title, y_title=y_title)

    monkeypatch.setattr(theme, "style_axes", spy)

    app = AppTest.from_file(str(PAGES / "8_Track_Map.py"), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    paint = next(b for b in app.button_group if b.label == "Map colour")
    assert "CO₂ per segment distance" in paint.options
    assert "Battery state of charge" not in paint.options  # default is petrol
    assert "Distance (m)" in styled
    # Model output is clearly labelled.
    all_text = " ".join([*(c.value for c in app.caption), *(m.value for m in app.markdown)])
    assert "model output" in all_text.lower()


def test_switching_from_hybrid_soc_to_petrol_resets_cleanly():
    app = AppTest.from_file(str(PAGES / "8_Track_Map.py"), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    # Switch to Full hybrid and pick Battery state of charge.
    app.button_group[1].set_value("hybrid").run()
    assert not app.exception, [e.value for e in app.exception]
    paint = next(b for b in app.button_group if b.label == "Map colour")
    assert "Battery state of charge" in paint.options
    paint.set_value("Battery state of charge").run()
    assert not app.exception, [e.value for e in app.exception]
    # Switch back to Petrol: Battery state of charge must disappear without crashing.
    app.button_group[1].set_value("petrol").run()
    assert not app.exception, [e.value for e in app.exception]
    paint_after = next(b for b in app.button_group if b.label == "Map colour")
    assert "Battery state of charge" not in paint_after.options


@pytest.mark.parametrize("page_name", ["1_Overview.py", "2_Category_View.py", "4_Compare.py"])
def test_all_other_workbook_pages_omit_derived_co2_on_map(page_name: str):
    app = AppTest.from_file(str(PAGES / page_name), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    paints = [b for b in app.button_group if b.label == "Map colour"]
    assert paints
    assert "CO₂ per segment distance" not in paints[0].options

