import numpy as np

from pwt.cornering import downforce_speed, grip_speed
from pwt.model import fleet
from pwt.model.profile import generate


def test_unchanged_grip_reproduces_the_lap():
    car = fleet.petrol()
    lap = generate("sport", car, corner_speed=grip_speed(1))
    assert np.array_equal(lap.v_kph, generate("sport", car).v_kph)


def test_no_downforce_reproduces_the_lap():
    car = fleet.petrol()
    lap = generate("sport", car, corner_speed=downforce_speed(0.8, 0.0, car.m_total))
    assert np.allclose(lap.v_kph, generate("sport", car).v_kph)


def test_more_downforce_never_slows_a_corner():
    speeds = [downforce_speed(0.8, scz, 1300)(0, 15.0) for scz in (0, 0.2, 0.5, 1.0)]
    assert speeds == sorted(speeds)
