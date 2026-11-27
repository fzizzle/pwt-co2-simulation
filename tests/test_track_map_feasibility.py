"""Tests for Track map engine feasibility reporting and headline/table hygiene."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAGE = str(ROOT / "dashboard" / "views" / "8_Track_Map.py")


def test_track_map_shows_engine_check_pass_on_default_petrol_lap():
    app = AppTest.from_file(PAGE, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.warning
    captions = " ".join(c.value for c in app.caption)
    assert "engine power check" in captions.lower()
    assert "0 short steps" in captions.lower()
    # Units must sit on the displayed metric values.
    assert app.metric[0].value.endswith(" s")
    assert app.metric[1].value.endswith(" km/h")
    assert app.metric[2].value.endswith(" km/h")
    assert app.metric[3].value.endswith(" l/100 km")


def test_track_map_notes_bev_has_no_combustion_engine_check():
    app = AppTest.from_file(PAGE, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    app.button_group[1].set_value("bev").run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.warning
    captions = " ".join(c.value for c in app.caption)
    assert "battery electric" in captions.lower()
    assert app.metric[3].value.endswith(" kWh/100 km")


def test_track_map_flags_shortfall_with_provisional_warning(monkeypatch):
    """When powertrain_cells reports short_steps > 0, Track map must flag it like 6_Model.py."""
    import pwt.phase2 as phase2
    import streamlit as st

    st.cache_data.clear()
    original = phase2.powertrain_cells

    def fake_powertrain_cells(*args, **kwargs):
        cells, _ = original(*args, **kwargs)
        return cells, (7, 12.4)

    monkeypatch.setattr(phase2, "powertrain_cells", fake_powertrain_cells)
    try:
        app = AppTest.from_file(PAGE, default_timeout=120).run()
        assert not app.exception, [e.value for e in app.exception]
        warnings = " ".join(w.value for w in app.warning)
        assert "provisional" in warnings.lower()
        assert "7" in warnings
        assert "12.4 kW" in warnings
    finally:
        st.cache_data.clear()


def test_track_map_uses_cycles_names_and_avoids_duplicate_table_column():
    app = AppTest.from_file(PAGE, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    # Cycle selector uses pwt.sweep.CYCLES display names.
    assert "Francorchamps sport, generated" in app.button_group[0].options
    assert "Francorchamps eco, generated" in app.button_group[0].options
    # Opening the lap table when Speed is selected must not add a duplicate Speed/km/h column.
    app.toggle[0].set_value(True).run()
    assert not app.exception, [e.value for e in app.exception]
    cols = list(app.dataframe[0].value.columns)
    assert len(cols) == 4
    assert "km/h" not in cols
