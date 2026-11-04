"""Study B dashboard controls preserve numerical evidence and feasibility warnings."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from dashboard.sensitivity_charts import comparison_table, tornado
from dashboard.theme import DARK
from pwt.sensitivity import swings

ROOT = Path(__file__).resolve().parents[1]
PAGE = str(ROOT / "dashboard/views/9_CO2_Sensitivity.py")


def test_new_views_cover_ranked_data_and_selected_examples():
    from dashboard.sensitivity_charts import ranking_visual, variable_key, elasticity_panels
    from dashboard.theme import LIGHT
    from pwt.sensitivity_reporting import FACTOR_NAMES, ranking_text
    frame = pd.read_csv(ROOT / 'docs/study-b-results.csv')
    ranked = swings(frame)
    for _, selected in ranked.groupby(['powertrain', 'cycle']):
        ordered = selected.sort_values(['swing', 'factor'], ascending=[False, True])
        chart = ranking_visual(selected, DARK)
        assert list(chart.data[0].y) == ordered.factor.map(FACTOR_NAMES).tolist()
        assert list(chart.data[0].marker.symbol) == ['circle' if p else 'circle-open' for p in ordered.engine_check_pass]
        report = ranking_text(selected)
        positions = [report.index(FACTOR_NAMES[f]) for f in ordered.factor]
        assert positions == sorted(positions)
        mass = selected[selected.factor == 'mass'].iloc[0]
        assert f'{mass.elasticity:.2f}' in variable_key(selected)
        for pal in (LIGHT, DARK):
            fig = tornado(selected, mass.powertrain, pal)
            assert fig.data[1].marker.color != fig.data[2].marker.color
    for across in ('cars', 'cycles'):
        charts = [elasticity_panels(swings(frame, grid), across, DARK) for grid in ('co2_eu', 'co2_fr')]
        for chart in charts:
            assert len(chart.layout.annotations) == 4
            dots = [r for t in chart.data for r in t.customdata]
            assert len(dots) == 76
            assert {tuple(r[:3]) for r in dots} == set(ranked[['powertrain', 'cycle', 'factor']].itertuples(index=False, name=None))
            assert len({tuple(chart.layout[k].range) for k in ('xaxis', 'xaxis2', 'xaxis3', 'xaxis4')}) == 1
            for key in ('yaxis', 'yaxis2', 'yaxis3', 'yaxis4'):
                assert tuple(chart.layout[key].range) == (4.5, -0.5)
        assert [list(t.x) for t in charts[0].data] != [list(t.x) for t in charts[1].data]


def test_tie_badges_and_provisional_dots():
    from dashboard.sensitivity_charts import ranking_visual, elasticity_panels
    ranked = swings(pd.read_csv(ROOT / 'docs/study-b-results.csv'))
    bev = ranked[(ranked.powertrain == 'bev') & (ranked.cycle == 'wltc')]
    assert any('≈' in label for label in ranking_visual(bev, DARK).data[0].text)
    lookup = ranked.set_index(['powertrain', 'cycle', 'factor'])
    for across in ('cars', 'cycles'):
        for trace in elasticity_panels(ranked, across, DARK).data:
            for data, symbol in zip(trace.customdata, trace.marker.symbol):
                row = lookup.loc[tuple(data[:3])]
                assert data[3] == pytest.approx(row.elasticity)
                assert symbol == ('circle' if row.engine_check_pass else 'circle-open')


def test_comparison_views_ignore_car_cycle_selectors(app):
    before = [chart.proto.spec for chart in app.get('plotly_chart')][-2:]
    app.selectbox(key='study_b_powertrain').set_value('bev')
    app.selectbox(key='study_b_cycle').set_value('nedc').run()
    assert not app.exception
    assert [chart.proto.spec for chart in app.get('plotly_chart')][-2:] == before


@pytest.fixture
def app():
    page = AppTest.from_file(PAGE, default_timeout=30).run()
    assert not page.exception, [error.value for error in page.exception]
    return page


def test_default_page_shows_petrol_sport_and_provisional_warning(app):
    assert app.metric[0].value == "385.2 g/km"
    assert "Peak engine efficiency" in app.metric[1].value
    assert "77.82" in app.metric[2].value
    assert any("provisional" in warning.value for warning in app.warning)
    numbers = app.dataframe[0].value
    assert len(numbers) == 5
    assert not numbers["Passes engine check"].all()


def test_passing_filter_requires_both_endpoints_and_baseline(app):
    app.toggle(key="study_b_passing").set_value(True).run()
    assert not app.exception
    assert app.dataframe[0].value["Passes engine check"].all()
    app.selectbox(key="study_b_cycle").set_value("wltc").run()
    assert not app.exception
    assert app.metric[1].value == "No passing comparison"
    assert any("No complete comparison" in item.value for item in app.info)


def test_french_grid_and_bev_exclude_combustion_engine_variant(app):
    app.selectbox(key="study_b_powertrain").set_value("bev")
    app.selectbox(key="study_b_grid").set_value("co2_fr").run()
    assert not app.exception
    frame = pd.read_csv(ROOT / "docs/study-b-results.csv")
    baseline = frame[(frame.powertrain == "bev") & (frame.cycle == "franco_sport_generated")
                     & (frame.factor == "baseline")].iloc[0]
    assert app.metric[0].value == f"{baseline.co2_fr:.1f} g/km"
    assert len(app.dataframe[0].value) == 4
    assert "Peak engine efficiency" not in app.dataframe[0].value.Factor.tolist()
    assert any("motor, battery" in item.value for item in app.info)


def test_research_filters_and_unavailable_bev_laps_are_clear(app):
    app.selectbox(key="study_b_experiment").set_value("regenerated").run()
    assert not app.exception
    assert "Lap time (s)" in app.dataframe[1].value
    assert set(app.dataframe[1].value.Car) == {"Petrol"}
    app.selectbox(key="study_b_powertrain").set_value("bev").run()
    assert not app.exception
    assert any("does not include" in item.value for item in app.info)


def test_full_report_and_download_are_available(app):
    assert any("Findings for owner review" in item.value for item in app.markdown)
    assert any("petrol sport rankings are provisional" in item.value for item in app.markdown)
    assert app.selectbox(key="study_b_artifact").options


def test_running_page_recovers_when_cached_chart_module_lacks_new_helper(monkeypatch):
    from dashboard import sensitivity_charts

    # Reproduce a server that imported the chart module before research_table existed.
    monkeypatch.delattr(sensitivity_charts, "research_table")
    page = AppTest.from_file(PAGE, default_timeout=30).run()
    assert not page.exception, [error.value for error in page.exception]
    page.selectbox(key="study_b_experiment").set_value("regenerated").run()
    assert not page.exception
    assert "Lap time (s)" in page.dataframe[1].value


def test_chart_preserves_reversed_engine_endpoints_and_individual_shortfalls():
    frame = pd.read_csv(ROOT / "docs/study-b-results.csv")
    ranked = swings(frame)
    selected = ranked[(ranked.powertrain == "petrol") & (ranked.cycle == "franco_sport_generated")]
    fig = tornado(selected, "petrol", DARK)
    low, high = fig.data[1:]
    engine = selected.factor.tolist().index("engine")
    mass = selected.factor.tolist().index("mass")
    assert low.x[engine] > 0 > high.x[engine]
    assert high.marker.symbol[mass] == "diamond-open"
    assert low.marker.symbol[mass] == "circle"
    assert fig.data[0].marker.pattern.shape[mass] == "/"
    numbers = comparison_table(selected)
    assert numbers.loc[mass, "+10% short steps"] == selected.iloc[mass].short_steps_high
