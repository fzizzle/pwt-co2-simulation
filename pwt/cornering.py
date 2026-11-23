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
RADIUS_METHODS = ("inferred", "outline")
#: Half-window (m along the outline) used to find the tightest vertex near each mapped corner.
OUTLINE_SEARCH_WINDOW_M = 120.0


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


def _outline_corner_matches(window_m: float = OUTLINE_SEARCH_WINDOW_M) -> list[dict]:
    """Estimate each sport template corner's radius from the circuit outline.

    Maps each corner distance onto the GeoJSON outline through `pwt.trackmap.ANCHORS` and
    takes the minimum 3-vertex circumradius within +/-`window_m`.
    """
    import numpy as np

    from pwt.model.profile import track
    from pwt.trackmap import ANCHORS, EARTH_RADIUS_M, LANDMARKS, outline

    ol = outline()
    lon = ol["lon"].to_numpy()
    lat = ol["lat"].to_numpy()
    s_ol = ol["s"].to_numpy()
    scale = math.cos(math.radians(float(lat.mean())))
    x = np.radians(lon - lon[0]) * scale * EARTH_RADIUS_M
    y = np.radians(lat - lat[0]) * EARTH_RADIUS_M

    n = len(x) - 1  # closed loop: last vertex repeats the first
    total_len = float(s_ol[-1])
    vtx_radii = np.array([
        _circumradius((x[(i - 1) % n], y[(i - 1) % n]), (x[i], y[i]), (x[(i + 1) % n], y[(i + 1) % n]))
        for i in range(n)
    ])

    model_a, real_a = np.array(ANCHORS).T
    sport = track("sport")
    rows = []
    for dist, speed_ms in sorted(sport.corners.items()):
        s_mapped = float(np.interp(dist, model_a, real_a))
        diff = np.abs(s_ol[:n] - s_mapped)
        dist_along = np.minimum(diff, total_len - diff)
        idx = np.where(dist_along <= window_m)[0]
        if len(idx) == 0:
            best = int(np.argmin(dist_along))
        else:
            best = int(idx[np.argmin(vtx_radii[idx])])
        radius_m = float(vtx_radii[best])
        rows.append({
            "distance_m": float(dist),
            "landmark": LANDMARKS.get(int(dist), ""),
            "template_speed_kph": speed_ms * 3.6,
            "inferred_radius_m": speed_ms * speed_ms / (MU0 * G),
            "outline_s_m": float(s_ol[best]),
            "outline_radius_m": radius_m,
            "implied_mu_outline": speed_ms * speed_ms / (G * radius_m),
            "outline_speed_at_mu0_kph": math.sqrt(MU0 * G * radius_m) * 3.6,
        })
    return rows


def outline_corner_radii(window_m: float = OUTLINE_SEARCH_WINDOW_M) -> dict[float, float]:
    """Corner distance (m) -> estimated radius (m) from the circuit outline."""
    return {row["distance_m"]: row["outline_radius_m"] for row in _outline_corner_matches(window_m)}


def corner_table(mu0: float = MU0, window_m: float = OUTLINE_SEARCH_WINDOW_M):
    """Per-corner comparison of inferred radii, outline radii and implied grip."""
    import pandas as pd

    rows = _outline_corner_matches(window_m)
    if mu0 != MU0:
        for row in rows:
            v_ms = row["template_speed_kph"] / 3.6
            row["inferred_radius_m"] = v_ms * v_ms / (mu0 * G)
            row["outline_speed_at_mu0_kph"] = math.sqrt(mu0 * G * row["outline_radius_m"]) * 3.6
    return pd.DataFrame(rows)


def _radii_for(radius_method: str) -> dict[float, float] | None:
    if radius_method not in RADIUS_METHODS:
        raise ValueError(f"Unknown radius_method {radius_method!r}; choose from {RADIUS_METHODS}")
    return outline_corner_radii() if radius_method == "outline" else None


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
            for car, d in frame[frame.variant == variant].groupby("powertrain", sort=False):
                ax.plot(d[x], d[column], marker="o", label=POWERTRAIN_NAMES[car])
            ax.set_xlabel(xlabel)
            ax.set_ylabel(label)
        axes[0].legend()
        fig.tight_layout()
        fig.savefig(DOCS / name, dpi=130)
        plt.close(fig)

    if comparison is not None and not comparison.empty:
        methods = list(comparison["radius_method"].unique())
        fig, axes = plt.subplots(1, len(methods), figsize=(4.5 * len(methods), 3.6), sharey=True)
        if len(methods) == 1:
            axes = [axes]
        titles = {"inferred": "Inferred radii (default)", "outline": "Outline radii"}
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


def main() -> None:
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description="Generate Study C tables and figures.")
    parser.add_argument(
        "--radius-method",
        choices=("all", *RADIUS_METHODS),
        default="all",
        help="Which radius method to run (default: all, writing default inferred + outline files).",
    )
    args = parser.parse_args()

    corners = corner_table()
    corners.to_csv(DOCS / "study-c-corners.csv", index=False)

    if args.radius_method in ("all", "inferred"):
        inferred = results("inferred")
        inferred.to_csv(DOCS / "study-c-results.csv", index=False)
    else:
        inferred = None

    if args.radius_method in ("all", "outline"):
        outline_frame = results("outline")
        outline_frame.to_csv(DOCS / "study-c-results-outline.csv", index=False)

    methods = RADIUS_METHODS if args.radius_method == "all" else (args.radius_method,)
    comparison = pd.concat(
        [spoiler_vs_tyres(radius_method=m, match_by="lap_time") for m in methods],
        ignore_index=True,
    )
    comparison.to_csv(DOCS / "study-c-comparison.csv", index=False)

    plot_frame = inferred if inferred is not None else outline_frame
    figures(plot_frame, comparison)
    print(plot_frame.round(2).to_string())


if __name__ == "__main__":
    main()
