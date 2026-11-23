"""Lap geometry in north-up slide coordinates."""

from dataclasses import dataclass
from functools import cache
from math import cos, radians, sin

import contourpy
import numpy as np

from pwt.sweep import cycles
from pwt.trackmap import place


CORNERS = {
    "start": 0, "la_source": 220, "eau_rouge": 1010, "les_combes": 2200,
    "pouhon": 3600, "stavelot": 4740, "bus_stop": 6540, "finish": 6990,
}
CORNER_NAMES: dict[str, str] = {
    "start": "Start / finish", "la_source": "La Source", "eau_rouge": "Eau Rouge",
    "les_combes": "Les Combes", "pouhon": "Pouhon", "stavelot": "Stavelot",
    "bus_stop": "Bus Stop", "finish": "Start / finish",
}
KEEP_OUT = [(1400, 20, 1600, 180), (60, 300, 900, 580)]


@dataclass(frozen=True)
class Lap:
    xy: np.ndarray
    s: np.ndarray
    v: np.ndarray
    z: np.ndarray


@cache
def lap() -> Lap:
    cycle = cycles()["franco_sport_generated"]
    lat, lon = place(cycle.s)
    xy = np.column_stack((lon * cos(radians(lat.mean())), -lat))
    for _ in range(2):
        xy = sum(np.roll(xy, shift, axis=0) for shift in range(-4, 5)) / 9
    xy = (xy - xy.min(axis=0)) / np.ptp(xy[:, 0])
    return Lap(xy, np.asarray(cycle.s), np.asarray(cycle.v_kph), np.asarray(cycle.z))


def index_at(s_m: float) -> int:
    s = lap().s
    return min(int(s.searchsorted(s_m)), len(s) - 1)


def zoomed(s_m: float, zoom: float, fx: float, fy: float) -> np.ndarray:
    xy = lap().xy
    return (xy - xy[index_at(s_m)]) * (1600 * zoom) + [fx, fy]


@cache
def relief() -> list[tuple[float, list[np.ndarray]]]:
    track = lap()
    samples = track.xy[::4]
    height = track.xy[:, 1].max()
    x = np.linspace(-0.6, 1.6, 260)
    y = np.linspace(-0.6, height + 0.6, int(260 * (height + 1.2) / 2.2))
    # Interpolate one grid row at a time to bound temporary storage.
    dx2 = (x[:, None] - samples[:, 0]) ** 2
    field = np.empty((len(y), len(x)))
    for row, ordinate in enumerate(y):
        distance2 = dx2 + (ordinate - samples[:, 1]) ** 2 + 1e-6
        weights = distance2 ** -1.5
        field[row] = (weights * track.z[::4]).sum(axis=1) / weights.sum(axis=1)
    for _ in range(12):
        field = (field + np.roll(field, 1, 0) + np.roll(field, -1, 0)
                 + np.roll(field, 1, 1) + np.roll(field, -1, 1)) / 5
    generator = contourpy.contour_generator(x, y, field)
    return [(float(level), generator.lines(level)) for level in range(370, 476, 2)]


def _inside(points, box, pad=0):
    x, y = points.T
    left, top, right, bottom = box
    return np.count_nonzero((left - pad < x) & (x < right + pad)
                            & (top - pad < y) & (y < bottom + pad))


def opener_frame(s_m: float, zoom: float) -> tuple[float, float]:
    centered = zoomed(s_m, zoom, 0, 0)
    best = float("inf")
    for fy in range(300, 701, 25):
        for fx in range(950, 1301, 25):
            points = centered + [fx, fy]
            score = (5 * _inside(points, KEEP_OUT[0], 30) + 3 * _inside(points, KEEP_OUT[1])
                     + abs(fx - 1100) / 50 + abs(fy - 450) / 50)
            if score < best:
                best, origin = score, (fx, fy)
    return origin


def minimap_points() -> np.ndarray:
    xy = lap().xy
    size = np.array([62, 100])
    scale = np.min(size / np.ptp(xy, axis=0))
    return [1452, 44] + (size - np.ptp(xy, axis=0) * scale) / 2 + xy * scale


def label_spot(points: np.ndarray, dot: tuple[float, float], text: str) -> tuple[float, float]:
    centroid = points.mean(axis=0)
    half_box = np.array([5.25 * len(text) + 3, 10])
    candidates = []
    for angle in range(0, 360, 15):
        direction = np.array([cos(radians(angle)), sin(radians(angle))])
        for radius in (16, 20, 26, 32):
            center = dot + radius * direction
            clearance = (np.abs(points - center) - half_box).max(axis=1).min()
            score = (clearance <= 2, radius, -np.linalg.norm(center - centroid))
            candidates.append((score, center))
    center = min(candidates, key=lambda candidate: candidate[0])[1]
    return float(center[0]), float(center[1])
