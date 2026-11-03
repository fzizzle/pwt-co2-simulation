"""Study B checkpoints, physical response and complete factor coverage."""

import numpy as np
import pytest

from pwt.sensitivity import EXPECTED_BASELINE, check_baseline, sensitivity, swings, variants
from pwt.sweep import CYCLES


@pytest.fixture(scope="module")
def frame():
    return sensitivity()


def test_baseline_matches_approved_checkpoint(frame):
    baseline = frame[frame.factor == "baseline"].set_index(["powertrain", "cycle"])
    for powertrain, expected in EXPECTED_BASELINE.items():
        for cycle, co2 in zip(CYCLES, expected):
            assert round(baseline.loc[(powertrain, cycle), "co2_eu"], 1) == co2


def test_every_expected_variant_and_cycle_is_present(frame):
    expected = {(p, f, s, c) for p, f, s in variants() for c in CYCLES}
    actual = list(frame[["powertrain", "factor", "scale", "cycle"]].itertuples(index=False, name=None))
    assert len(variants()) == 42
    assert len(actual) == len(set(actual)) == 168
    assert set(actual) == expected
    assert np.isfinite(frame.co2_eu).all()
    assert not ((frame.powertrain == "bev") & (frame.factor == "engine")).any()


def test_more_mass_increases_co2_for_every_car_and_cycle(frame):
    mass = frame[frame.factor == "mass"].pivot(index=["powertrain", "cycle"],
                                               columns="scale", values="co2_eu")
    baseline = frame[frame.factor == "baseline"].set_index(["powertrain", "cycle"]).co2_eu
    assert (mass[0.9] < baseline.reindex(mass.index)).all()
    assert (mass[1.1] > baseline.reindex(mass.index)).all()


def test_ranked_spans_preserve_efficiency_direction(frame):
    ranked = swings(frame)
    assert len(ranked) == 76
    assert np.allclose(ranked.swing, abs(ranked.co2_high - ranked.co2_low))
    engine = ranked[ranked.factor == "engine"]
    assert (engine.co2_high < engine.co2_low).all()
    assert (engine.delta_high < 0).all()
    for _, group in ranked.groupby(["powertrain", "cycle"]):
        assert group.swing.is_monotonic_decreasing
        assert list(group["rank"]) == list(range(1, len(group) + 1))


def test_baseline_drift_stops_publication(frame):
    changed = frame.copy()
    changed.loc[changed.factor == "baseline", "co2_eu"] += 1
    with pytest.raises(ValueError, match="Baseline changed"):
        check_baseline(changed)


def test_missing_endpoint_is_rejected(frame):
    missing = frame.drop(frame[frame.factor != "baseline"].index[0])
    with pytest.raises(ValueError, match="endpoints"):
        swings(missing)
