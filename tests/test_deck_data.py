import pytest

from pwt.deck.data import CYCLE_KEYS, baseline, cell, fill


def test_baseline_reproduces():
    expected = {
        "petrol": [134.1, 145.1, 217.5, 385.2],
        "bev": [38.0, 45.8, 56.5, 132.2],
        "hybrid": [123.7, 128.8, 218.8, 395.2],
        "phev": [67.9, 73.6, 113.0, 293.0],
    }
    assert CYCLE_KEYS == ("nedc", "wltc", "franco_eco_generated", "franco_sport_generated")
    frame = baseline()
    assert len(frame) == 16
    assert frame.co2_eu.notna().all()
    for pt, values in expected.items():
        assert [round(cell(pt, cycle).co2_eu, 1) for cycle in CYCLE_KEYS] == values


def test_short_steps_flags():
    frame = baseline()
    short = frame.loc[frame.short_steps > 0, ["powertrain", "cycle"]]
    assert set(short.itertuples(index=False, name=None)) == {
        ("petrol", "wltc"), ("phev", "nedc"), ("phev", "wltc")
    }


def test_fill_formats_tags():
    assert fill("{co2.petrol.wltc}") == "145.1 g CO2/km"
    assert fill("{co2.bev.sport}") == "132.2 g CO2/km"
    assert fill("{fuel.petrol.nedc}") == f"{cell('petrol', 'nedc').fuel_l_100km:.1f} l/100 km"
    eco = cell("bev", "franco_eco_generated")
    assert fill("{elec.bev.eco}") == f"{eco.battery_kwh_100km:.1f} kWh/100 km"


def test_unknown_tag_fails():
    with pytest.raises(KeyError, match=r"co2\.diesel\.wltc"):
        fill("{co2.diesel.wltc}")


def test_text_without_tags_unchanged():
    assert fill("plain {not a tag") == "plain {not a tag"
