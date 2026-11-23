import numpy as np
import pytest

from pwt.deck import track


def test_north_up_and_clockwise():
    xy = track.lap().xy
    assert xy[track.index_at(220), 1] < xy[track.index_at(0), 1]
    x, y = xy.T
    assert np.sum(y * np.roll(x, -1) - x * np.roll(y, -1)) < 0
    assert np.ptp(x) == pytest.approx(1)


def test_relief_levels():
    contours = dict(track.relief())
    assert list(contours) == list(range(370, 476, 2))
    for level in (380, 460):
        points = np.concatenate(contours[level])
        assert any(np.min(np.linalg.norm(points - p, axis=1)) < 0.03 for p in track.lap().xy)


@pytest.mark.parametrize("corner,zoom", [
    ("la_source", 3.2), ("eau_rouge", 2.8), ("les_combes", 3.0),
    ("pouhon", 2.6), ("stavelot", 3.0), ("bus_stop", 3.4), ("finish", 2.4),
])
def test_opener_frames_clear(corner, zoom):
    s = track.CORNERS[corner]
    fx, fy = track.opener_frame(s, zoom)
    points = track.zoomed(s, zoom, fx, fy)
    np.testing.assert_allclose(points[track.index_at(s)], [fx, fy])
    x, y = points.T
    assert not np.any((1390 <= x) & (x <= 1610) & (10 <= y) & (y <= 190))
    assert np.mean((60 <= x) & (x <= 900) & (300 <= y) & (y <= 580)) < 0.05


def test_label_clear_for_every_slide():
    from pwt.deck.structure import lap_position, SLIDES

    points = track.minimap_points()
    for i in range(1, len(SLIDES)):
        dot = points[track.index_at(lap_position(i))]
        text = str(i + 1)
        center = track.label_spot(points, dot, text)
        gaps = np.abs(points - center) - [5.25 * len(text) + 3, 10]
        assert np.all(gaps.max(axis=1) > 2), text


def test_minimap_fits_box():
    points = track.minimap_points()
    assert np.all(points >= [1452, 44])
    assert np.all(points <= [1514, 144])
