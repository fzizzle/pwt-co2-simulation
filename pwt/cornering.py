"""Study C: corner speeds from tyre grip and spoiler downforce."""

import math

G = 9.81


def grip_speed(factor: float):
    """Scale every corner speed for `factor` times the grip."""
    return lambda s, v: v * math.sqrt(factor)


def downforce_speed(mu0: float, scz: float, mass: float, rho: float = 1.2):
    def corner(s, v):
        radius = v * v / (mu0 * G)
        spare = 1 - mu0 * rho * scz * radius / (2 * mass)
        if spare <= 0:
            return float("inf")  # downforce alone holds the car: no corner limit
        return math.sqrt(mu0 * G * radius / spare)
    return corner
