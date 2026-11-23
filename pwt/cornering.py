"""Study C: corner speeds from tyre grip and spoiler downforce."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

G = 9.81
MU0 = 0.7            # course sheet "11 Good trajectory speed": gamma = 0.7 g
LD = 4.0             # ASSUMPTION (unsourced): spoiler lift-to-drag ratio (added SCz / added SCx)
KG_PER_SCZ = 40.0    # ASSUMPTION (linear scaling unsourced): added mass, kg per m2 of SCz
GRIPS = (0.9, 1.0, 1.1, 1.2, 1.3)   # ASSUMPTION: the grid is the owner's to change
SCZS = (0.0, 0.1, 0.2, 0.3, 0.4)    # PROVISIONAL: m2, bracketed by road/track-day wings
LAP = "franco_sport_generated"
DOCS = Path(__file__).resolve().parent.parent / "docs"
#: "inferred": R = v^2/(mu0 g) from the template speed. "outline": circle fitted to the circuit
#: outline. "line": the fitted radius plus half a track width (the driver's line).
RADIUS_METHODS = ("inferred", "outline", "line")
#: The outline is resampled at this even spacing (m) before any radius is measured.
OUTLINE_SPACING_M = 5.0
#: Half-window (m along the outline) of the least-squares circle fitted about each apex.
FIT_HALF_WINDOW_M = 40.0
#: Half-windows (m) fitted to show how much each radius depends on the window.
FIT_HALF_WINDOWS_M = (25.0, 40.0, 60.0)
#: Half-window (m) around each mapped corner in which the apex is searched for.
OUTLINE_SEARCH_WINDOW_M = 120.0
#: ASSUMPTION: half the track width (m). The driver's line radius is the fitted centreline
#: radius plus this. Not measured for each corner (see docs/sources.md).
TRACK_HALF_WIDTH_M = 5.0


def grip_speed(factor: float, *, radii: dict[float, float] | None = None, mu0: float = MU0):
    """Corner speed for `factor` times the reference grip.

    With `radii=None` (default), scales each template speed by sqrt(factor), which is
    equivalent to inferring R = v^2 / (mu0 * g). With `radii`, computes sqrt(factor * mu0 * g * R).
    """
    if radii is None:
        return lambda s, v: v * math.sqrt(factor)
    return lambda s, v: math.sqrt(factor * mu0 * G * radii[s])


def downforce_speed(
    mu0: float,
    scz: float,
    mass: float,
    rho: float = 1.2,
    *,
    radii: dict[float, float] | None = None,
):
    """Corner speed with aerodynamic downforce area `scz` (m2).

    With `radii=None` (default), infers R = v^2 / (mu0 * g) from each template corner speed.
    With `radii`, uses `radii[s]` (e.g. estimated from the track outline).
    """
    def corner(s, v):
        radius = (v * v / (mu0 * G)) if radii is None else radii[s]
        spare = 1.0 - mu0 * rho * scz * radius / (2.0 * mass)
        if spare <= 0:
            return float("inf")  # downforce alone holds the car: no corner limit
        return math.sqrt(mu0 * G * radius / spare)
    return corner


def _circumradius(p0, p1, p2) -> float:
    """Radius of the circle passing through three 2-D points (m), or inf if collinear."""
    a = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    b = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    c = math.hypot(p2[0] - p0[0], p2[1] - p0[1])
    cross = abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]))
    if cross <= 1e-9:
        return math.inf
    return a * b * c / (2.0 * cross)


def fit_circle(x, y) -> tuple[float, float, float]:
    """Least-squares circle through points (x, y): centre x, centre y and radius (m).

    Algebraic (Kasa) fit: solves x² + y² = 2·a·x + 2·b·y + c for a, b and c, then
    R = sqrt(c + a² + b²).
    """
    import numpy as np

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    design = np.c_[2.0 * x, 2.0 * y, np.ones_like(x)]
    (a, b, c), *_ = np.linalg.lstsq(design, x * x + y * y, rcond=None)
    return float(a), float(b), math.sqrt(c + a * a + b * b)


def _catmull_rom_closed(x, y, per_segment: int = 40):
    """Points along a centripetal Catmull-Rom curve through every vertex of a closed polyline.

    The last point of `x`, `y` repeats the first. A straight-line resample puts every point on
    a chord, so a circle fitted to a short stretch of a coarse outline comes out too small;
    the curve passes through the same vertices without that bias, and the centripetal form
    does not overshoot where the vertex spacing changes sharply.
    """
    import numpy as np

    p = np.c_[np.asarray(x, float), np.asarray(y, float)][:-1]
    n = len(p)
    u = np.linspace(0.0, 1.0, per_segment, endpoint=False)[:, None]
    out = []
    for i in range(n):
        p0, p1, p2, p3 = p[(i - 1) % n], p[i], p[(i + 1) % n], p[(i + 2) % n]
        t0 = 0.0
        t1 = t0 + max(np.hypot(*(p1 - p0)), 1e-9) ** 0.5
        t2 = t1 + max(np.hypot(*(p2 - p1)), 1e-9) ** 0.5
        t3 = t2 + max(np.hypot(*(p3 - p2)), 1e-9) ** 0.5
        t = t1 + u * (t2 - t1)
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    dense = np.vstack(out + [p[:1]])
    return dense[:, 0], dense[:, 1]


def resample_closed(x, y, spacing_m: float = OUTLINE_SPACING_M):
    """Resample a closed polyline at an even spacing: distance, x and y (m).

    The points follow a centripetal Catmull-Rom curve through the vertices
    (`_catmull_rom_closed`). The last point of `x`, `y` repeats the first; the result does not
    repeat it.
    """
    import numpy as np

    x, y = _catmull_rom_closed(x, y)
    s = np.r_[0.0, np.cumsum(np.hypot(np.diff(x), np.diff(y)))]
    count = int(round(s[-1] / spacing_m))
    s_even = np.linspace(0.0, s[-1], count, endpoint=False)
    return s_even, np.interp(s_even, s, x), np.interp(s_even, s, y)


def _along(s, centre: float, length: float):
    """Signed distance along a closed loop of `length` from `centre` to each `s` (m)."""
    return (s - centre + length / 2.0) % length - length / 2.0


def _fitted_radius(s, x, y, length: float, centre: float, half_window_m: float) -> float:
    """Radius of the circle fitted to the resampled points within ±`half_window_m` of `centre`."""
    import numpy as np

    near = np.abs(_along(s, centre, length)) <= half_window_m
    return fit_circle(x[near], y[near])[2]


def _turning(x, y, half_window_m: float, spacing_m: float):
    """Absolute heading change (rad) within ±`half_window_m` of each resampled point."""
    import numpy as np

    heading = np.arctan2(np.roll(y, -1) - y, np.roll(x, -1) - x)
    step = (np.roll(heading, -1) - heading + np.pi) % (2.0 * np.pi) - np.pi
    k = int(round(half_window_m / spacing_m))
    total = np.convolve(np.r_[step[-k:], step, step[:k]], np.ones(2 * k), mode="valid")
    return np.abs(total[: len(x)])


def _outline_xy():
    """The circuit outline in local metres: distance along it, x and y, closed loop."""
    import numpy as np

    from pwt.trackmap import EARTH_RADIUS_M, outline

    ol = outline()
    lon = ol["lon"].to_numpy()
    lat = ol["lat"].to_numpy()
    scale = math.cos(math.radians(float(lat.mean())))
    x = np.radians(lon - lon[0]) * scale * EARTH_RADIUS_M
    y = np.radians(lat - lat[0]) * EARTH_RADIUS_M
    return ol["s"].to_numpy(), x, y


def outline_stats() -> dict[str, float]:
    """Summary of the track outline's vertex density (`data/track/spa-francorchamps.geojson`)."""
    import numpy as np

    from pwt.trackmap import outline

    track = outline()
    steps = np.diff(track["s"].to_numpy())
    return {
        "vertices": len(track) - 1,
        "length_m": float(track["s"].iloc[-1]),
        "spacing_min_m": float(steps.min()),
        "spacing_median_m": float(np.median(steps)),
        "spacing_mean_m": float(steps.mean()),
        "spacing_max_m": float(steps.max()),
    }


def _min_vertex_radius(s_ol, x, y, centre: float, window_m: float) -> float:
    """The old method, kept as a comparison: the smallest 3-vertex circumradius near `centre`."""
    import numpy as np

    n = len(x) - 1  # closed loop: the last vertex repeats the first
    near = np.where(np.abs(_along(s_ol[:n], centre, float(s_ol[-1]))) <= window_m)[0]
    return min(
        _circumradius((x[(i - 1) % n], y[(i - 1) % n]), (x[i], y[i]), (x[(i + 1) % n], y[(i + 1) % n]))
        for i in near
    )


def _outline_corner_matches(
    half_window_m: float = FIT_HALF_WINDOW_M,
    search_window_m: float = OUTLINE_SEARCH_WINDOW_M,
    mu0: float = MU0,
) -> list[dict]:
    """Estimate each sport template corner's radius from the circuit outline.

    1. Resample the outline every `OUTLINE_SPACING_M`.
    2. Map the corner's model distance onto the outline through `pwt.trackmap.ANCHORS`.
    3. Take as apex the point, within ±`search_window_m`, that turns most within
       ±`half_window_m`.
    4. Fit one circle by least squares to the points within ±`half_window_m` of the apex.

    The driver's line radius adds `TRACK_HALF_WIDTH_M`. The grip band spans the fits at every
    half-window in `FIT_HALF_WINDOWS_M` and the driver's line.
    """
    import numpy as np

    from pwt.model.profile import track
    from pwt.trackmap import ANCHORS, LANDMARKS

    s_ol, x_ol, y_ol = _outline_xy()
    length = float(s_ol[-1])
    s, x, y = resample_closed(x_ol, y_ol, OUTLINE_SPACING_M)
    # The curve is a little longer than the straight-line outline that ANCHORS refer to.
    s = s * length / (s[1] * len(s))
    turning = _turning(x, y, half_window_m, OUTLINE_SPACING_M)

    model_a, real_a = np.array(ANCHORS).T
    rows = []
    for dist, speed_ms in sorted(track("sport").corners.items()):
        mapped = float(np.interp(dist, model_a, real_a))
        offset = _along(s, mapped, length)
        near = np.where(np.abs(offset) <= search_window_m)[0]
        apex = int(near[np.argmax(turning[near])])
        radius = _fitted_radius(s, x, y, length, s[apex], half_window_m)
        line = radius + TRACK_HALF_WIDTH_M
        spread = [_fitted_radius(s, x, y, length, s[apex], h) for h in FIT_HALF_WINDOWS_M]
        v2 = speed_ms * speed_ms
        rows.append({
            "distance_m": float(dist),
            "landmark": LANDMARKS.get(int(dist), ""),
            "template_speed_kph": speed_ms * 3.6,
            "inferred_radius_m": v2 / (mu0 * G),
            "apex_s_m": float(s[apex]),
            "apex_offset_m": float(offset[apex]),
            "apex_at_search_edge": bool(abs(offset[apex]) > search_window_m - OUTLINE_SPACING_M),
            "turn_deg": math.degrees(float(turning[apex])),
            "outline_radius_m": radius,
            "line_radius_m": line,
            "radius_low_m": min(spread),
            "radius_high_m": max(spread),
            "min_3pt_radius_m": _min_vertex_radius(s_ol, x_ol, y_ol, mapped, search_window_m),
            "implied_mu_outline": v2 / (G * radius),
            "implied_mu_line": v2 / (G * line),
            "implied_mu_low": v2 / (G * max(max(spread), line)),
            "implied_mu_high": v2 / (G * min(spread)),
            "outline_speed_at_mu0_kph": math.sqrt(mu0 * G * radius) * 3.6,
            "line_speed_at_mu0_kph": math.sqrt(mu0 * G * line) * 3.6,
        })
    return rows


def outline_corner_radii(line: bool = False, half_window_m: float = FIT_HALF_WINDOW_M) -> dict[float, float]:
    """Corner distance (m) -> radius (m) fitted to the outline, or of the driver's line."""
    key = "line_radius_m" if line else "outline_radius_m"
    return {row["distance_m"]: row[key] for row in _outline_corner_matches(half_window_m)}


def corner_table(mu0: float = MU0, half_window_m: float = FIT_HALF_WINDOW_M):
    """Per-corner comparison of inferred, fitted and driver's-line radii, with implied grip."""
    import pandas as pd

    return pd.DataFrame(_outline_corner_matches(half_window_m, mu0=mu0))


def one_grip_fits_every_corner(table) -> bool:
    """True if one grip value lies inside every corner's band (`implied_mu_low` to `_high`)."""
    return bool(table.implied_mu_low.max() <= table.implied_mu_high.min())


def _radii_for(radius_method: str) -> dict[float, float] | None:
    if radius_method not in RADIUS_METHODS:
        raise ValueError(f"Unknown radius_method {radius_method!r}; choose from {RADIUS_METHODS}")
    if radius_method == "inferred":
        return None
    return outline_corner_radii(line=radius_method == "line")


# --- the study runner: python -m pwt.cornering ------------------------------------------------
#
# Every value marked ASSUMPTION or PROVISIONAL is for the owner to review in
# docs/study-c-cornering.md and docs/sources.md.


def spoiler_car(car, scz: float, *, ld: float = LD, kg_per_scz: float = KG_PER_SCZ):
    """`car` with a spoiler of downforce area `scz` (m2): more drag and more mass."""
    return replace(
        car,
        cx=car.cx + scz / ld / car.frontal_area,
        m_vehicle=car.m_vehicle + kg_per_scz * scz,
    )


def _fleet_cars():
    from pwt.model import fleet
    from pwt.sweep import START_SOC

    petrol = fleet.petrol()
    return petrol, {
        "petrol": petrol,
        "bev": fleet.electric(),
        "hybrid": fleet.hybrid(START_SOC["hybrid"]),
        "phev": fleet.plugin(START_SOC["phev"]),
    }


def results(
    radius_method: str = "inferred",
    *,
    grips=GRIPS,
    sczs=SCZS,
    mu0: float = MU0,
    ld: float = LD,
    kg_per_scz: float = KG_PER_SCZ,
):
    """One row per car and variant on the sport lap, with the lap time and the settings.

    Each lap is generated by the petrol car, as `pwt.sweep.cycles` does, and driven by every
    car. The spoiler variants use the spoiler petrol car for the lap and the spoiler version
    of each car in `sweep`. `radius_method` selects `"inferred"` (default, R = v^2/(mu0 g))
    or `"outline"` (radii estimated from `data/track/spa-francorchamps.geojson`).
    """
    import pandas as pd

    from pwt.model.profile import generate, lap_time_s
    from pwt.sweep import sweep

    radii = _radii_for(radius_method)
    petrol, cars = _fleet_cars()
    frames = []

    def record(variant, value, lap, cars_in):
        frame = sweep({(name, variant, value): c for name, c in cars_in.items()}, {LAP: lap})
        frame = frame.drop(columns=["v1", "v2"])
        frame.insert(2, "variant", variant)
        frame.insert(3, "grip_factor", value if variant == "grip" else 1.0)
        frame.insert(4, "scz_m2", value if variant == "spoiler" else 0.0)
        frame["added_scx_m2"] = frame.scz_m2 / ld
        frame["added_kg"] = frame.scz_m2 * kg_per_scz
        frame["lap_time_s"] = lap_time_s(lap)
        frames.append(frame)

    for g in grips:
        lap = generate("sport", petrol, corner_speed=grip_speed(g, radii=radii, mu0=mu0))
        record("grip", g, lap, cars)
    for scz in sczs:
        sp = spoiler_car(petrol, scz, ld=ld, kg_per_scz=kg_per_scz)
        lap = generate("sport", sp, corner_speed=downforce_speed(mu0, scz, sp.m_total, radii=radii))
        record(
            "spoiler",
            scz,
            lap,
            {n: spoiler_car(c, scz, ld=ld, kg_per_scz=kg_per_scz) for n, c in cars.items()},
        )
    return pd.concat(frames, ignore_index=True)


def _match_by_lap_time(
    spoiler_lap,
    _spoiler_corner_fn,
    petrol_car,
    grip_corner_factory,
    *,
    tol_s: float = 0.005,
    lo: float = 0.5,
    hi: float = 2.0,
) -> float:
    """Find the tyre grip factor whose sport lap matches `spoiler_lap` in lap time."""
    from pwt.model.profile import generate, lap_time_s

    target_s = lap_time_s(spoiler_lap)

    def time_for(factor: float) -> float:
        return lap_time_s(generate("sport", petrol_car, corner_speed=grip_corner_factory(factor)))

    t_lo = time_for(lo)
    while t_lo < target_s and lo > 0.1:
        lo *= 0.5
        t_lo = time_for(lo)
    t_hi = time_for(hi)
    while t_hi > target_s and hi < 16.0:
        hi *= 2.0
        t_hi = time_for(hi)

    for _ in range(35):
        mid = 0.5 * (lo + hi)
        t_mid = time_for(mid)
        if abs(t_mid - target_s) <= tol_s:
            return mid
        if t_mid > target_s:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


#: Matching rules for `spoiler_vs_tyres`.
#: Each rule takes `(spoiler_lap, spoiler_corner_fn, petrol_car, grip_corner_factory)` and
#: returns the matched tyre `grip_factor`. Additional rules (e.g. average corner-speed gain
#: or one reference corner) can be registered here without changing `spoiler_vs_tyres`.
MATCH_RULES = {
    "lap_time": _match_by_lap_time,
}


def spoiler_vs_tyres(
    sczs=None,
    *,
    radius_method: str = "inferred",
    match_by: str = "lap_time",
    mu0: float = MU0,
    ld: float = LD,
    kg_per_scz: float = KG_PER_SCZ,
):
    """Compare each spoiler size with the tyre grip factor matched under `match_by`."""
    import pandas as pd

    from pwt.model.profile import generate, lap_time_s
    from pwt.sweep import sweep

    if match_by not in MATCH_RULES:
        raise ValueError(f"Unknown match_by {match_by!r}; choose from {tuple(MATCH_RULES)}")
    radii = _radii_for(radius_method)
    matcher = MATCH_RULES[match_by]
    petrol, cars = _fleet_cars()
    sizes = [s for s in SCZS if s > 0] if sczs is None else list(sczs)
    grip_factory = lambda g: grip_speed(g, radii=radii, mu0=mu0)

    rows = []
    for scz in sizes:
        sp_petrol = spoiler_car(petrol, scz, ld=ld, kg_per_scz=kg_per_scz)
        sp_corner = downforce_speed(mu0, scz, sp_petrol.m_total, radii=radii)
        sp_lap = generate("sport", sp_petrol, corner_speed=sp_corner)
        sp_time = lap_time_s(sp_lap)
        sp_sweep = sweep(
            {(n,): spoiler_car(c, scz, ld=ld, kg_per_scz=kg_per_scz) for n, c in cars.items()},
            {LAP: sp_lap},
        ).set_index("powertrain")

        grip_factor = matcher(sp_lap, sp_corner, petrol, grip_factory)
        ty_lap = generate("sport", petrol, corner_speed=grip_factory(grip_factor))
        ty_time = lap_time_s(ty_lap)
        ty_sweep = sweep({(n,): c for n, c in cars.items()}, {LAP: ty_lap}).set_index("powertrain")

        for powertrain in cars:
            sp_row = sp_sweep.loc[powertrain]
            ty_row = ty_sweep.loc[powertrain]
            rows.append({
                "radius_method": radius_method,
                "match_rule": match_by,
                "powertrain": powertrain,
                "scz_m2": float(scz),
                "spoiler_lap_time_s": sp_time,
                "matched_grip_factor": float(grip_factor),
                "matched_lap_time_s": ty_time,
                "lap_time_diff_s": sp_time - ty_time,
                "spoiler_co2_eu": float(sp_row["co2_eu"]),
                "tyres_co2_eu": float(ty_row["co2_eu"]),
                "delta_co2_eu": float(sp_row["co2_eu"] - ty_row["co2_eu"]),
                "spoiler_co2_fr": float(sp_row["co2_fr"]),
                "tyres_co2_fr": float(ty_row["co2_fr"]),
                "delta_co2_fr": float(sp_row["co2_fr"] - ty_row["co2_fr"]),
                "spoiler_short_steps": int(sp_row["short_steps"]),
                "spoiler_short_kw": float(sp_row["short_kw"]),
                "tyres_short_steps": int(ty_row["short_steps"]),
                "tyres_short_kw": float(ty_row["short_kw"]),
            })
    return pd.DataFrame(rows)


def figures(frame, comparison=None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from pwt.catalog import POWERTRAIN_NAMES

    for column, label, name in (("lap_time_s", "Lap time (s)", "study-c-lap-time.png"),
                                ("co2_eu", "EU CO2 (g CO2/km)", "study-c-co2.png")):
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
        for ax, variant, x, xlabel in (
            (axes[0], "grip", "grip_factor", "Grip factor (tyres)"),
            (axes[1], "spoiler", "scz_m2", "Spoiler SCz (m2)"),
        ):
            part = frame[frame.variant == variant]
            if column == "lap_time_s":
                # Every car drives the one lap the petrol car generates, so lap time is shared.
                lap = part[part.powertrain == "petrol"].sort_values(x)
                ax.plot(lap[x], lap[column], marker="o", color="#333333",
                        label="Every car (one shared lap)")
            else:
                for car, d in part.groupby("powertrain", sort=False):
                    ax.plot(d[x], d[column], marker="o", label=POWERTRAIN_NAMES[car])
            ax.set_xlabel(xlabel)
            ax.set_ylabel(label)
        if column == "lap_time_s":
            axes[0].legend(loc="upper right")
        else:
            # The CO2 panels are empty between the plug-in hybrid and the electric car.
            axes[0].legend(loc="center", bbox_to_anchor=(0.5, 0.28), fontsize="small")
        fig.tight_layout()
        fig.savefig(DOCS / name, dpi=130)
        plt.close(fig)

    if comparison is not None and not comparison.empty:
        methods = list(comparison["radius_method"].unique())
        fig, axes = plt.subplots(1, len(methods), figsize=(4.5 * len(methods), 3.6), sharey=True)
        if len(methods) == 1:
            axes = [axes]
        titles = {"inferred": "Inferred radii (default)", "outline": "Fitted outline radii",
                  "line": "Driver's line radii"}
        for ax, method in zip(axes, methods):
            part = comparison[comparison.radius_method == method]
            for car, d in part.groupby("powertrain", sort=False):
                ax.plot(d["scz_m2"], d["delta_co2_eu"], marker="o", label=POWERTRAIN_NAMES[car])
            ax.axhline(0.0, color="#666666", lw=0.8, ls="--")
            ax.set_title(titles.get(method, method), fontsize=10)
            ax.set_xlabel("Spoiler SCz (m2)")
        axes[0].set_ylabel("Spoiler minus tyres at same lap time (g CO2/km)")
        axes[0].legend()
        fig.tight_layout()
        fig.savefig(DOCS / "study-c-comparison.png", dpi=130)
        plt.close(fig)


RESULT_FILES = {
    "inferred": "study-c-results.csv",
    "outline": "study-c-results-outline.csv",
    "line": "study-c-results-line.csv",
}


def main() -> None:
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description="Generate Study C tables and figures.")
    parser.add_argument(
        "--radius-method",
        choices=("all", *RADIUS_METHODS),
        default="all",
        help="Which radius method to run (default: all). Each method writes its own results "
             "file and replaces only its own rows in study-c-comparison.csv.",
    )
    args = parser.parse_args()
    methods = RADIUS_METHODS if args.radius_method == "all" else (args.radius_method,)

    corner_table().to_csv(DOCS / "study-c-corners.csv", index=False)

    frames = {}
    for method in methods:
        frames[method] = results(method)
        frames[method].to_csv(DOCS / RESULT_FILES[method], index=False)

    comparison = pd.concat(
        [spoiler_vs_tyres(radius_method=m, match_by="lap_time") for m in methods],
        ignore_index=True,
    )
    path = DOCS / "study-c-comparison.csv"
    if args.radius_method != "all" and path.exists():
        kept = pd.read_csv(path)
        kept = kept[~kept.radius_method.isin(methods)]
        comparison = pd.concat([kept, comparison], ignore_index=True)
        order = {m: i for i, m in enumerate(RADIUS_METHODS)}
        comparison = comparison.sort_values(
            ["radius_method", "scz_m2"], key=lambda c: c.map(order) if c.name == "radius_method" else c,
            kind="stable",
        ).reset_index(drop=True)
    comparison.to_csv(path, index=False)

    if "inferred" in frames:
        figures(frames["inferred"], comparison)
    print(next(iter(frames.values())).round(2).to_string())


if __name__ == "__main__":
    main()
