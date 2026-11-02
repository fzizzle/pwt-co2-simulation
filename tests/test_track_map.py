"""The lap must land on the real circuit, and the Track map page must run."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.charts import gear_steps, speed_and_altitude, trace_lines
from dashboard.theme import DARK
from dashboard.track_charts import is_lap, mark_corners, metrics, resample
from pwt.trackmap import ANCHORS, LANDMARKS, outline, place

PAGE = str(ROOT / "dashboard" / "pages" / "8_Track_Map.py")
PAGES = ROOT / "dashboard" / "pages"


def sparse_lap(**columns) -> pd.DataFrame:
    return pd.DataFrame({"distance_m": [0.0, 3000.0, 7000.0], "speed_kph": [50.0, 150.0, 50.0],
                         "altitude_m": [400.0, 450.0, 400.0], **columns})


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


def test_sparse_lap_is_resampled_over_the_whole_circuit():
    lap = resample(sparse_lap(time_s=[0.0, 80.0, 200.0]))
    assert len(lap) == 1401 and lap["distance_m"].iloc[-1] == 7000
    assert lap["speed_kph"].iloc[300] == pytest.approx(100)


def test_generated_lap_is_left_alone():
    lap = pd.DataFrame({"distance_m": np.arange(0.0, 7001.0, 5.0), "speed_kph": 100.0})
    assert resample(lap).equals(lap)


def test_columns_a_run_lacks_are_not_offered():
    # The battery-electric workbooks have neither time nor emissions.
    lap = sparse_lap(emission_g_co2=[np.nan] * 3, delta_distance_m=[0.0, 3000.0, 4000.0])
    assert set(metrics(lap)) == {"Speed", "Altitude"}
    assert "time_s" not in resample(lap.assign(time_s=np.nan))


@pytest.mark.parametrize("cycle, expected", [("franco_eco", True), ("franco_sport_generated", True),
                                             ("nedc", False), ("wltc", False)])
def test_only_francorchamps_goes_on_the_map(cycle, expected):
    assert is_lap(cycle) is expected


@pytest.mark.parametrize("x_column", ["distance_m", "time_s", "step"])
def test_corners_land_at_their_distance_on_any_axis(x_column):
    lap = sparse_lap(time_s=[0.0, 80.0, 200.0], step=[0, 1, 2])
    fig = go.Figure()
    mark_corners(fig, lap, x_column, DARK)
    assert len(fig.layout.shapes) == len(LANDMARKS)
    at = next(iter(LANDMARKS))
    assert fig.layout.shapes[0].x0 == pytest.approx(np.interp(at, lap["distance_m"], lap[x_column]))


@pytest.mark.parametrize("steps, mode", [(32, "lines+markers"), (1401, "lines")])
def test_markers_are_dropped_where_they_would_hide_the_line(steps, mode):
    lap = pd.DataFrame({"distance_m": np.linspace(0, 7000, steps), "speed_kph": 100.0, "gear": 3})
    for fig in (speed_and_altitude(lap, "distance_m", DARK), gear_steps(lap, "distance_m", DARK),
                trace_lines(lap, ["speed_kph"], "distance_m", DARK)):
        assert fig.data[0].mode == mode


def test_trace_explorer_maps_laps_only():
    app = AppTest.from_file(str(PAGES / "3_Trace_Explorer.py"), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
    box = app.selectbox(key="trace_run")
    for i, option in enumerate(box.options):
        app.selectbox(key="trace_run").select_index(i).run()
        assert not app.exception, [e.value for e in app.exception]
        painted = any(b.label == "Paint the track with" for b in app.button_group)
        assert painted == ("Francorchamps" in option)


@pytest.mark.parametrize("page", ["Overview", "2_Category_View", "4_Compare"])
def test_other_lap_pages_run(page):
    path = ROOT / "dashboard" / "Overview.py" if page == "Overview" else PAGES / f"{page}.py"
    app = AppTest.from_file(str(path), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]
