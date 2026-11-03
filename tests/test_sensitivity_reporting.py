"""Review regressions: fresh prose/slides, honest rankings and alternate assumptions."""

from dataclasses import replace

import pandas as pd
import pytest

from pwt.sensitivity import BASE, sensitivity, swings
from pwt.sensitivity_extensions import (
    GEAR_SCALES, assumption_variants, interactions, intermediate_variants, total_mass, workbook_curves,
)
from pwt.sensitivity_reporting import ranking_text, result_facts, slides


@pytest.fixture(scope="module")
def frame():
    return sensitivity()


def test_quoted_results_and_titles_follow_variant_changes_without_baseline_change(frame):
    original = result_facts(frame, swings(frame))
    changed = frame.copy()
    row = ((changed.powertrain == "petrol") & (changed.cycle == "wltc")
           & (changed.factor == "engine") & (changed.scale == 1.1))
    changed.loc[row, "co2_eu"] += 6.7
    fresh = result_facts(changed, swings(changed))
    expected = swings(changed).query("powertrain == 'petrol' and cycle == 'wltc' and factor == 'engine'").iloc[0]
    assert f"petrol {expected.swing:.1f}" in fresh["combustion"]
    assert fresh["combustion"] != original["combustion"]
    row = ((changed.powertrain == "petrol") & (changed.cycle == "wltc")
           & (changed.factor == "mass") & (changed.scale == 1.1))
    changed.loc[row, "co2_eu"] += 100
    assert "petrol Car mass" in result_facts(changed, swings(changed))["combustion_title"]


def test_near_ties_do_not_chain_and_flagged_comparisons_remain_visible():
    group = pd.DataFrame({"factor": ["mass", "drag", "rolling"], "swing": [10.0, 9.85, 9.7],
                          "engine_check_pass": [True, False, True]})
    assert ranking_text(group) == "Car mass ≈ Drag coefficient † > Rolling resistance"
    assert ranking_text(group[group.engine_check_pass]) == "Car mass > Rolling resistance"
    assert "No comparison" in ranking_text(group.iloc[:0])


def test_mass_definition_and_intermediate_samples_preserve_other_inputs():
    for vehicle in BASE.values():
        for scale in (0.9, 1.1):
            changed = total_mass(vehicle, scale)
            assert changed.m_total == pytest.approx(vehicle.m_total * scale)
            assert replace(changed, m_vehicle=vehicle.m_vehicle) == vehicle
    grid = intermediate_variants()
    for powertrain in BASE:
        assert {s for p, f, s in grid if p == powertrain and f == "gears"} == set(GEAR_SCALES)
        assert (powertrain, "mass", 0.95) in grid and (powertrain, "mass", 1.05) in grid


def test_curve_shape_is_separated_from_peak_multiplier():
    curves = workbook_curves()
    variants = assumption_variants(curves)
    shape = variants[("hybrid", "shape_only", "old")]
    complete = variants[("hybrid", "workbook_curve", "old")]
    assert shape.eta_max == BASE["hybrid"].eta_max
    assert complete.eta_max == pytest.approx(0.25)
    assert shape.a1 == complete.a1 != BASE["hybrid"].a1
    assert replace(shape, a1=BASE["hybrid"].a1, a2=BASE["hybrid"].a2, a3=BASE["hybrid"].a3) == BASE["hybrid"]


def test_interactions_measure_nonadditivity_and_check_all_four_terms():
    rows = []
    for mass in (0.9, 1.0, 1.1):
        for drag in (0.9, 1.0, 1.1):
            rows.append({"powertrain": "petrol", "cycle": "wltc", "second_factor": "drag",
                         "mass_scale": mass, "other_scale": drag,
                         "co2_eu": 100+10*(mass-1)+20*(drag-1)+30*(mass-1)*(drag-1),
                         "short_steps": int(mass == 0.9 and drag == 1.0)})
    table = interactions(pd.DataFrame(rows)).set_index(["mass_scale", "other_scale"])
    assert table.loc[(1.1, 1.1), "interaction_g_km"] == pytest.approx(0.3)
    assert table.loc[(1.1, 1.1), "engine_check_pass"]
    # The joint point passes, but its mass-only comparison fails.
    assert not table.loc[(0.9, 1.1), "engine_check_pass"]
    assert table.loc[(1.0, 1.1), "interaction_g_km"] == pytest.approx(0)


def test_slides_use_updated_results_and_keep_draft_status(tmp_path, frame):
    from PIL import Image
    from pptx import Presentation

    for name in ("combustion", "electric", "plugin"):
        Image.new("RGB", (1300, 530), "white").save(tmp_path / f"study-b-{name}.png")
    changed = frame.copy()
    row = ((changed.powertrain == "petrol") & (changed.cycle == "wltc")
           & (changed.factor == "engine") & (changed.scale == 1.1))
    changed.loc[row, "co2_eu"] += 4
    ranked = swings(changed)
    slides(tmp_path, changed, ranked)
    deck = Presentation(tmp_path / "study-b-slides.pptx")
    texts = "\n".join(s.text for slide in deck.slides for s in slide.shapes if s.has_text_frame)
    assert result_facts(changed, ranked)["combustion"] in texts
    assert "Owner review draft" in texts
    assert len(deck.slides) == 5
    assert all(s.left >= 0 and s.top >= 0 and s.left+s.width <= deck.slide_width
               and s.top+s.height <= deck.slide_height for slide in deck.slides for s in slide.shapes)
