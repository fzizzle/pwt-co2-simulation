"""Speed profiles for the Francorchamps lap, generated from the assignment sheet's rules.

The supplied laps impose their speeds: 32 points, with acceleration and braking points
placed by hand. On the sport lap they ask the 74 kW petrol engine for up to 127 kW. This
module builds the profile the assignment describes instead:

* the corners are boundary conditions: the speed each template (`03` sport, `04` eco)
  gives them, except 16 and 17, which the sheet says to take as straights;
* out of each corner the car accelerates — eco at 0-100 km/h in 20 s, capped at 90 km/h,
  or less where the engine cannot manage that rate; sport as hard as the engine can in its
  best gear;
* into each corner it brakes, at 0.4 g (eco) or 0.6 g (sport);
* the speed at each point is the lower of the forward (acceleration) and backward
  (braking) passes — the "iterations to find the max speed point and braking point".
  Both passes run over two laps so the lap closes on itself.

The gear at each point is the speed-rule gear, shifted down while the engine cannot deliver
the step's demand: what a driver does, and what the sheets' speed-only rule does not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import openpyxl

from pwt.catalog import course_file
from pwt.model.conventions import FRANCO_SHIFTS
from pwt.model.cycle import Cycle
from pwt.model.powertrains import full_load_w
from pwt.model.road_load import gears
from pwt.model.vehicle import Vehicle

TEMPLATES = {
    "eco": "04 Francorchamps cycle empty ECO driving.xlsx",
    "sport": "03 Francorchamps cycle empty SPORT driving.xlsx",
}
#: "Consider rapid corners 16 and 17 like straight lines."
STRAIGHT_CORNERS = {"16", "17"}
G = 9.81
REDLINE_RPM = 6000.0
#: Share of the full-load curve the forward pass plans to use, so the model's own check
#: (made at the end-of-step speed) finds no shortfall from discretisation.
FULL_LOAD_MARGIN = 0.98


@dataclass(frozen=True, slots=True)
class Rules:
    brake_ms2: float
    accel_ms2: float | None  # None: as much as the engine gives
    vmax_ms: float


RULES = {
    "eco": Rules(brake_ms2=0.4 * G, accel_ms2=100 / 3.6 / 20, vmax_ms=90 / 3.6),
    "sport": Rules(brake_ms2=0.6 * G, accel_ms2=None, vmax_ms=np.inf),
}


@dataclass(frozen=True, slots=True)
class Track:
    distance: np.ndarray  # template points, m
    altitude: np.ndarray
    corners: dict[float, float]  # distance (m) -> corner speed (m/s)
    template_speed_kph: np.ndarray
    template_time_s: float


def track(mode: str) -> Track:
    """The lap's points, altitudes and corner speeds from the template for `mode`."""
    workbook = openpyxl.load_workbook(course_file(TEMPLATES[mode]), data_only=True)
    try:
        ws = workbook.active
        rows = [
            [ws.cell(r, c).value for c in range(2, 8)]
            for r in range(4, 36)
        ]
    finally:
        workbook.close()
    corners = {}
    for label, dist, _alt, kph, _ms, _t in rows:
        name = str(label).strip()
        if re.fullmatch(r"\d+(-\d+)?", name) and name not in STRAIGHT_CORNERS:
            corners[float(dist)] = kph / 3.6
    return Track(
        distance=np.array([r[1] for r in rows], float),
        altitude=np.array([r[2] for r in rows], float),
        corners=corners,
        template_speed_kph=np.array([r[3] for r in rows], float),
        template_time_s=float(rows[-1][5]),
    )


def _resistance(vehicle: Vehicle, v, slope):
    m = vehicle.m_total
    return (m * vehicle.g * vehicle.f_roll + m * vehicle.g * np.sin(slope)
            + 0.5 * vehicle.rho_air * vehicle.scx * v * v)


def _engine_rads(vehicle: Vehicle, v, gear):
    return vehicle.ratios[gear - 1] * v / (vehicle.wheel_diameter_m / 2)


def _max_accel(vehicle: Vehicle, v0: float, v1: float, slope: float) -> float:
    """Best acceleration from v0 to v1 over the gears under the redline at v1.

    Judged as the model judges a step: engine speed and aero at the end speed, wheel power
    at the mean speed.
    """
    best = -np.inf
    mean_v = max((v0 + v1) / 2, 1.0)
    for gear in range(1, len(vehicle.ratios) + 1):
        omega = _engine_rads(vehicle, v1, gear)
        if omega * 60 / (2 * np.pi) > REDLINE_RPM:
            continue
        force = FULL_LOAD_MARGIN * full_load_w(vehicle, omega) * vehicle.eta_drivetrain / mean_v
        m_eff = vehicle.effective_mass(vehicle.ratios[gear - 1], "outside")
        best = max(best, (force - _resistance(vehicle, v1, slope)) / m_eff)
    return best


def _accelerate(vehicle: Vehicle, rules: Rules, v0: float, slope: float, ds: float) -> float:
    """The speed after `ds`: the rule's rate where it has one, never more than the engine
    gives (the eco rate is too much for the climb out of Eau Rouge). Iterated so the end
    speed the engine is judged at is consistent."""
    v1 = v0
    for _ in range(4):
        a = _max_accel(vehicle, v0, v1, slope)
        if rules.accel_ms2 is not None:
            a = min(a, rules.accel_ms2)
        v1 = np.sqrt(max(v0 * v0 + 2 * a * ds, 0.0))
    return v1


def generate(mode: str, vehicle: Vehicle, ds: float = 5.0, corner_speed=None) -> Cycle:
    """The `mode` lap ("eco" or "sport") as `vehicle` can drive it, every `ds` metres.

    `corner_speed(distance_m, speed_ms)`, if given, replaces each template corner speed, so
    a tyre or downforce study can feed its own in.
    """
    rules = RULES[mode]
    lap = track(mode)
    s = np.arange(0.0, lap.distance[-1] + ds / 2, ds)
    z = np.interp(s, lap.distance, lap.altitude)
    n = len(s)
    slope = np.zeros(n)
    slope[1:] = np.arctan(np.diff(z) / ds)

    cap = np.full(n, rules.vmax_ms)
    for dist, speed in lap.corners.items():
        i = int(round(dist / ds))
        cap[i] = min(cap[i], corner_speed(dist, speed) if corner_speed else speed)

    # The lap is closed: the last grid point is the first. Both passes run over the m unique
    # points twice, so each lap's start inherits its end; the second lap is kept.
    m = n - 1
    cap_u = np.minimum(cap[:m], np.r_[cap[m], cap[1:m]])
    slope_u = np.r_[slope[m], slope[1:m]]  # slope of the step arriving at each point
    fwd = np.empty(2 * m)
    fwd[0] = min(cap_u[0], lap.template_speed_kph[0] / 3.6)
    for k in range(1, 2 * m):
        i = k % m
        fwd[k] = min(cap_u[i], _accelerate(vehicle, rules, fwd[k - 1], slope_u[i], ds))
    bwd = np.empty(2 * m)
    bwd[-1] = cap_u[m - 1]
    for k in range(2 * m - 2, -1, -1):
        i = k % m
        bwd[k] = min(cap_u[i], np.sqrt(bwd[k + 1] ** 2 + 2 * rules.brake_ms2 * ds))
    v = np.minimum(fwd[m:], bwd[m:])
    v = np.r_[v, v[0]]

    return Cycle(
        f"francorchamps_{mode}_generated", "distance", v * 3.6, s=s, z=z,
        gear=choose_gears(vehicle, v, s, slope),
    )


def choose_gears(vehicle: Vehicle, v: np.ndarray, s: np.ndarray, slope: np.ndarray):
    """The speed-rule gear, shifted down while the engine cannot deliver the step."""
    gear = gears(v * 3.6, FRANCO_SHIFTS)
    out = gear.copy()
    for i in range(1, len(v)):
        mean_v = (v[i] + v[i - 1]) / 2
        dt = (s[i] - s[i - 1]) / mean_v
        a = (v[i] - v[i - 1]) / dt
        for k in range(gear[i], 0, -1):
            omega = _engine_rads(vehicle, v[i], k)
            if omega * 60 / (2 * np.pi) > REDLINE_RPM:
                break
            m_eff = vehicle.effective_mass(vehicle.ratios[k - 1], "outside")
            demand = (m_eff * a + _resistance(vehicle, v[i], slope[i])) * mean_v
            demand /= vehicle.eta_drivetrain
            out[i] = k
            if demand <= full_load_w(vehicle, omega):
                break
    return out


def lap_time_s(cycle: Cycle) -> float:
    v = cycle.v_kph / 3.6
    return float(np.sum(np.diff(cycle.s) / ((v[1:] + v[:-1]) / 2)))
