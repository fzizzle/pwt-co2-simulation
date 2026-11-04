"""Study C dashboard page shows the saved results, the plan's baseline and feasibility warnings."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.cornering_charts import baseline_row, comparison_table, line_chart, rows_for
from dashboard.theme import DARK
from pwt.catalog import POWERTRAIN_NAMES

ROOT = Path(__file__).resolve().parents[1]
PAGE = str(ROOT / "dashboard/views/10_Cornering_Speed.py")
RESULTS = ROOT / "docs/study-c-results.csv"


@pytest.fixture
def app():
    page = AppTest.from_file(PAGE, default_timeout=30).run()
    assert not page.exception, [error.value for error in page.exception]
    return page


def test_default_page_shows_the_plans_petrol_baseline(app):
    assert app.metric[0].value == "235.1 s"
    assert app.metric[1].value == "385.2 g CO₂/km"
    assert "Cornering speed" in app.title[0].value or "Study C" in app.title[0].value


def test_provisional_warning_follows_short_steps(app):
    results = pd.read_csv(RESULTS)
    shown = any("provisional" in warning.value for warning in app.warning)
    petrol = results[(results.powertrain == "petrol") & (results.variant == "grip")]
    assert shown == bool((petrol.short_steps > 0).any())


@pytest.mark.parametrize("powertrain", list(POWERTRAIN_NAMES))
@pytest.mark.parametrize("variant", ["grip", "spoiler"])
def test_every_car_and_change_reruns(app, powertrain, variant):
    app.selectbox(key="study_c_powertrain").set_value(powertrain)
    app.selectbox(key="study_c_variant").set_value(variant).run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 5


def test_missing_results_gives_an_error_not_a_crash(monkeypatch, tmp_path):
    import shutil

    docs = tmp_path / "docs"
    shutil.copytree(ROOT / "docs", docs)
    (docs / "study-c-results.csv").unlink()
    source = Path(PAGE).read_text(encoding="utf-8").replace(
        'DOCS = ROOT / "docs"', f'DOCS = Path(r"{docs}")')
    page = tmp_path / "page.py"
    page.write_text(source.replace("ROOT = Path(__file__).resolve().parents[2]",
                                   f'ROOT = Path(r"{ROOT}")'), encoding="utf-8")
    run = AppTest.from_file(str(page), default_timeout=30).run()
    assert not run.exception
    assert any("missing" in error.value for error in run.error)


def test_saved_results_have_no_gaps_in_co2():
    results = pd.read_csv(RESULTS)
    assert not results.co2_eu.isna().any()
    assert not results.co2_fr.isna().any()
    assert set(results.powertrain) == set(POWERTRAIN_NAMES)
    assert (results.groupby(["powertrain", "variant"]).size() == 5).all()


def test_baseline_reproduces_the_plan():
    petrol = baseline_row(pd.read_csv(RESULTS), "petrol")
    assert round(petrol.lap_time_s, 1) == 235.1
    assert round(petrol.co2_eu, 1) == 385.2


def test_more_grip_shortens_the_lap_and_more_spoiler_lengthens_it():
    results = pd.read_csv(RESULTS)
    grip = rows_for(results, "petrol", "grip")
    spoiler = rows_for(results, "petrol", "spoiler")
    assert grip.lap_time_s.is_monotonic_decreasing
    assert spoiler.lap_time_s.is_monotonic_increasing


def test_chart_and_table_mark_infeasible_rows():
    rows = rows_for(pd.read_csv(RESULTS), "petrol", "grip").copy()
    rows.loc[0, "short_steps"] = 3
    fig = line_chart(rows, "grip", "lap_time_s", "Lap time (s)", "petrol", DARK)
    assert fig.data[0].marker.symbol[0] == "circle-open"
    assert fig.data[0].marker.symbol[1] == "circle"
    assert comparison_table(rows, "grip", "co2_eu")["Provisional"].tolist()[:2] == [True, False]
