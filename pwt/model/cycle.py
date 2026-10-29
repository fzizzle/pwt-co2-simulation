"""The imposed speed trace: what the car is asked to do, before any physics.

Index 0 is the initial state (sheet row 3); every later index is one step that ends there.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pwt.schema import Run

#: NEDC's urban part is the first 84 points (sheet rows 3-86), as `32` and `33` split it.
NEDC_URBAN_POINTS = 84


@dataclass(frozen=True, slots=True)
class Cycle:
    name: str
    kind: str  # "distance" | "time"
    v_kph: np.ndarray
    #: Cumulative distance (m) for a distance cycle, else None.
    s: np.ndarray | None = None
    #: Time (s) for a time cycle, else None.
    t: np.ndarray | None = None
    #: Altitude (m). Time cycles are flat.
    z: np.ndarray | None = None
    #: Phase label per point, for phase totals. None: one phase.
    phase: np.ndarray | None = None
    #: Gear per point, when the cycle comes with its own gear choice (`pwt.model.profile`).
    #: None: the convention's shift speeds decide.
    gear: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.v_kph)

    @classmethod
    def from_run(cls, run: Run, kind: str, name: str | None = None) -> "Cycle":
        trace = run.trace
        v = trace["speed_kph"].to_numpy(float)
        name = name or run.cycle or run.source_file
        if kind == "distance":
            return cls(
                name, kind, v,
                s=trace["distance_m"].to_numpy(float),
                z=trace["altitude_m"].to_numpy(float),
            )
        t = trace["time_s"].to_numpy(float)
        phase = None
        if len(t) == 105 and t[-1] == 1240:  # NEDC
            phase = np.where(np.arange(len(t)) < NEDC_URBAN_POINTS, "Urban", "Extra urban")
        elif len(t) == 1801:
            phase = cls.wltc_class3().phase
        return cls(name, kind, v, t=t, z=np.zeros_like(t), phase=phase)

    @classmethod
    def wltc_class3(cls) -> "Cycle":
        from pwt.derived import wltc_class3

        trace = wltc_class3()
        t = trace["time_s"].to_numpy(float)
        return cls(
            "wltc", "time", trace["speed_kph"].to_numpy(float), t=t, z=np.zeros_like(t),
            phase=trace["phase"].to_numpy(),
        )
