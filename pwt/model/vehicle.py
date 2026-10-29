"""A vehicle's parameters, read from a workbook's labelled block."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pwt.schema import Run


@dataclass(frozen=True, slots=True)
class Vehicle:
    family: str  # "ice" | "bev" | "hybrid"
    wheel_diameter_m: float
    ratios: tuple[float, ...]
    m_vehicle: float
    m_driver: float
    g: float
    frontal_area: float
    cx: float
    rho_air: float
    f_roll: float
    eta_drivetrain: float  # fraction, not %
    m_machine: float = 0.0
    m_battery: float = 0.0
    # engine
    eta_max: float = 0.0
    a1: float = 0.0
    a2: float = 0.0
    a3: float = 0.0
    p_max_w: float = 0.0
    fuel_density: float = 0.0  # kg/m³, i.e. g/l
    idle_rpm: float = 800.0
    # battery and motor
    battery_wh: float = 0.0
    p_motor_w: float = 0.0
    #: Motor efficiency η(N) = a N² + b N + c, in %.
    motor_eff: tuple[float, float, float] | None = None
    soc0: float = 1.0
    #: Full-load engine power: linear to `full_load_knee_rpm`, flat to the rated speed, at
    #: `p_rated_w`. The sheets have no rated power, only `p_max_w` scaling the efficiency
    #: curve, so it defaults to that; the assignment sheet's engine is 74 kW.
    full_load_knee_rpm: float = 5000.0
    p_rated_w: float | None = None
    notes: tuple[str, ...] = field(default=())

    @property
    def m_total(self) -> float:
        return self.m_vehicle + self.m_driver + self.m_machine + self.m_battery

    @property
    def scx(self) -> float:
        return self.frontal_area * self.cx

    def effective_mass(self, gear_ratio: float, convention: str) -> float:
        """Translating plus rotating mass in a gear: k = 1.04 + 0.0025 i²."""
        k = 1.04 + 0.0025 * gear_ratio**2
        if convention == "total":
            return self.m_total * k
        return self.m_driver + self.m_machine + self.m_battery + self.m_vehicle * k

    def efficiency(self, p_engine_w):
        """The sheets' engine efficiency curve, η_max (A1 x² + A2 x + A3), x = P / P_max."""
        x = p_engine_w / self.p_max_w
        return (self.a1 * x * x + self.a2 * x + self.a3) * self.eta_max

    @property
    def idle_rads(self) -> float:
        return self.idle_rpm * 2 * math.pi / 60

    @classmethod
    def from_run(cls, run: Run) -> "Vehicle":
        by_label = {label: value for (label, _unit), value in run.params.items()}

        def p(label: str, default: float | None = None) -> float:
            if label in by_label:
                return by_label[label]
            if default is None:
                raise KeyError(f"{run.source_file}: no parameter {label!r}")
            return default

        common = dict(
            wheel_diameter_m=p("wheel diameter"),
            m_vehicle=p("vehicle mass"),
            m_driver=p("driver mass"),
            g=p("gravity"),
            cx=p("cx"),
            rho_air=p("air density"),
            eta_drivetrain=p("drivetrain efficiency") / 100,
        )
        if "battery energy content" in by_label:  # battery electric
            return cls(
                family="bev",
                ratios=(p("gear ratio"),),
                m_battery=p("battery mass included"),
                frontal_area=p("frontal surface"),
                f_roll=p("coefficient of friction tire"),
                battery_wh=p("battery energy content") * 1000,
                motor_eff=(p("a"), p("b"), p("c")),
                **common,
            )
        engine = dict(
            ratios=tuple(p(f"gear ratio {k}") for k in range(1, 6)),
            frontal_area=p("surface"),
            f_roll=p("road friction coefficient"),
            eta_max=p("engine max efficiency"),
            a1=p("a1"),
            a2=p("a2"),
            a3=p("a3"),
            p_max_w=p("maximum power in watts"),
            fuel_density=p("fuel density"),
            idle_rpm=p("motor idle speed"),
        )
        if "batt energy content" in by_label:  # full or plug-in hybrid
            soc = run.trace["batt_soc"].dropna()
            return cls(
                family="hybrid",
                m_machine=p("electric machine mass"),
                m_battery=p("battery mass"),
                battery_wh=p("batt energy content"),
                p_motor_w=p("p electric motor"),
                soc0=float(soc.iloc[0]),
                **engine,
                **common,
            )
        return cls(family="ice", **engine, **common)
