"""The lap must land on the real circuit, and the Track map page must run."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from pwt.trackmap import ANCHORS, outline, place

PAGE = str(ROOT / "dashboard" / "pages" / "8_Track_Map.py")


def test_outline_is_a_closed_lap_of_the_right_length():
    track = outline()
    assert track["s"].iloc[-1] == pytest.approx(7004, abs=40)
    assert (track[["lon", "lat"]].iloc[0] == track[["lon", "lat"]].iloc[-1]).all()


def test_anchors_only_ever_move_forward():
    model, real = np.array(ANCHORS).T
    assert (np.diff(model) > 0).all() and (np.diff(real) > 0).all()


def test_lap_starts_and_ends_on_the_start_line():
    lat, lon = place([0.0, 7000.0])
    assert lat[0] == pytest.approx(lat[1], abs=1e-5) and lon[0] == pytest.approx(lon[1], abs=1e-5)


def test_neighbouring_points_stay_neighbours():
    lat, lon = place(np.arange(0.0, 7001.0, 5.0))
    scale = math.cos(math.radians(lat.mean()))
    hops = np.hypot(np.diff(lat), np.diff(lon) * scale) * 111_195
    assert hops.max() < 8


@pytest.mark.parametrize("powertrain", ["Battery electric", "Plug-in hybrid"])
def test_page_runs_for_cars_with_and_without_a_gearbox(powertrain):
    app = AppTest.from_file(PAGE, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    names = {"Battery electric": "bev", "Plug-in hybrid": "phev"}
    app.button_group[1].set_value(names[powertrain]).run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.metric[0].value.endswith(" s")
