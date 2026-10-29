"""The supplied spreadsheet model, ported to Python.

    from pwt.model import simulate, from_workbook
    result = from_workbook(read_run(course_file("07 SPA Franco PETROL car ECO Driving.xlsx")))
    result.totals[("total consumption", "l/100km")]   # 10.273, as the sheet

`from_workbook` reproduces a workbook exactly: its parameters, its trace, its conventions.
`simulate` takes them separately, which is how anything in the model gets changed.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pwt.model.conventions import Conventions, conventions_for
from pwt.model.cycle import Cycle
from pwt.model.powertrains import electric, hybrid, petrol
from pwt.model.road_load import road_load
from pwt.model.totals import headline, totals
from pwt.model.vehicle import Vehicle
from pwt.schema import Run


@dataclass(slots=True)
class Result:
    vehicle: Vehicle
    cycle: Cycle
    conventions: Conventions
    steps: pd.DataFrame
    totals: dict
    #: The full hybrid's fictive end-of-cycle recharge line, if the convention has one.
    recharge: dict | None = None

    @property
    def headline(self) -> dict[str, float | None]:
        return headline(self.totals, self.vehicle.family)


def simulate(vehicle: Vehicle, cycle: Cycle, conv: Conventions, strategy=None) -> Result:
    frame = road_load(cycle, vehicle, conv)
    recharge = None
    if vehicle.family == "bev":
        steps = electric(frame, vehicle, conv)
    elif vehicle.family == "hybrid":
        steps, recharge = hybrid(frame, vehicle, conv, strategy)
    else:
        steps = petrol(frame, vehicle, conv)
    return Result(vehicle, cycle, conv, steps, totals(steps, vehicle, conv, recharge), recharge)


def from_workbook(run: Run, conv: Conventions | None = None) -> Result:
    """Reproduce one supplied or derived workbook."""
    conv = conv or conventions_for(run.source_file)
    return simulate(Vehicle.from_run(run), Cycle.from_run(run, conv.trace_kind), conv)


__all__ = ["Conventions", "Cycle", "Result", "Vehicle", "from_workbook", "simulate"]
