"""How a hybrid splits each step's demand between motor and engine.

`step` returns (motor share, engine energy in Wh, the power the engine efficiency curve is
read at, Wh the engine puts into the battery on top of the demand).
"""

from __future__ import annotations

from pwt.model.conventions import Conventions
from pwt.model.vehicle import Vehicle


class NelisStrategy:
    """The supplied sheets' FACT column.

    Traction: the motor takes everything it can, derated to 90 % of its rating once demand
    exceeds it, while the battery is above `soc_min`. Braking: it recovers up to its rating
    while the battery is not over full. The efficiency curve is read at the whole demand, not
    the engine's share — as the sheets do.
    """

    def step(self, vehicle: Vehicle, conv: Conventions, soc: float, demand_w: float,
             dt: float, *, braking: bool) -> tuple[float, float, float, float]:
        rating = vehicle.p_motor_w
        if demand_w <= 0:
            share = (rating / abs(demand_w) if rating < abs(demand_w) else 1.0) if soc <= 1 else 0.0
        elif soc > conv.soc_min:
            share = 0.9 * (rating / demand_w) if rating < demand_w else 1.0
        else:
            share = 0.0
        energy = demand_w * dt / 3600
        engine_wh = share * energy if braking else (1 - share) * energy
        return share, engine_wh, demand_w, 0.0
