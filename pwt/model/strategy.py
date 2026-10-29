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
    while the battery is not over full.

    `efficiency_at="demand"` reads the engine's efficiency curve at the whole demand, as the
    sheets do, although the engine supplies only its share; `"engine"` reads it at the share.
    """

    def __init__(self, efficiency_at: str = "demand"):
        self.efficiency_at = efficiency_at

    def step(self, vehicle: Vehicle, conv: Conventions, soc: float, demand_w: float,
             dt: float, *, braking: bool, engine_rads: float = 0.0
             ) -> tuple[float, float, float, float]:
        rating = vehicle.p_motor_w
        if demand_w <= 0:
            share = (rating / abs(demand_w) if rating < abs(demand_w) else 1.0) if soc <= 1 else 0.0
        elif soc > conv.soc_min:
            share = 0.9 * (rating / demand_w) if rating < demand_w else 1.0
        else:
            share = 0.0
        energy = demand_w * dt / 3600
        engine_wh = share * energy if braking else (1 - share) * energy
        at = demand_w if self.efficiency_at == "demand" else (1 - share) * demand_w
        return share, engine_wh, at, 0.0


class SocBandStrategy:
    """Charge-sustaining: hold the battery in [low, high] instead of buying it back at the end.

    Below the band the engine runs at least at its best-efficiency load, x* = −A2 / 2A1 of
    P_max, capped by its full-load curve at the current speed, and the surplus over demand
    charges the battery, up to the motor's rating; when demand exceeds the full-load curve,
    the motor boosts while the battery is above `soc_min`. Above
    it the motor takes the demand up to its rating. Inside it, Nelis's rule. Unlike the
    sheets, the efficiency curve is read at the power the engine actually delivers.
    """

    def __init__(self, low: float = 0.5, high: float = 0.7):
        self.low, self.high = low, high
        self._nelis = NelisStrategy(efficiency_at="engine")

    def best_load_w(self, vehicle: Vehicle) -> float:
        return -vehicle.a2 / (2 * vehicle.a1) * vehicle.p_max_w

    def step(self, vehicle: Vehicle, conv: Conventions, soc: float, demand_w: float,
             dt: float, *, braking: bool, engine_rads: float = 0.0
             ) -> tuple[float, float, float, float]:
        from pwt.model.powertrains import full_load_w

        if demand_w <= 0:
            return self._nelis.step(vehicle, conv, soc, demand_w, dt, braking=braking)
        rating = vehicle.p_motor_w
        if soc < self.low:
            full = float(full_load_w(vehicle, engine_rads))
            if demand_w > full and soc > conv.soc_min:
                # Boost: the engine at full load, the motor covers the rest.
                share = min((demand_w - full) / demand_w, rating / demand_w)
                engine_w = (1 - share) * demand_w
                return share, engine_w * dt / 3600, engine_w, 0.0
            target = min(self.best_load_w(vehicle), full)
            engine_w = min(max(demand_w, target), demand_w + rating)
            charge_w = engine_w - demand_w
            return 0.0, engine_w * dt / 3600, engine_w, charge_w * dt / 3600
        if soc > self.high:
            share = min(1.0, rating / demand_w)
            engine_w = (1 - share) * demand_w
            return share, engine_w * dt / 3600, engine_w, 0.0
        return self._nelis.step(vehicle, conv, soc, demand_w, dt, braking=braking)
