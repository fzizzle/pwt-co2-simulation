"""The three pages must run, and must display the workbooks' own figures.

These use Streamlit's AppTest, which executes a page headlessly and exposes what it rendered.
They catch the two failure modes that matter: a page raising, and a page showing a number that
does not match the spreadsheet it came from.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from pwt.catalog import CATALOG

OVERVIEW = str(ROOT / "dashboard" / "Overview.py")
TRACE = str(ROOT / "dashboard" / "pages" / "2_Trace_Explorer.py")
COMPARE = str(ROOT / "dashboard" / "pages" / "3_Compare.py")

TIMEOUT = 120


def run(page: str) -> AppTest:
    app = AppTest.from_file(page, default_timeout=TIMEOUT).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def run_index(powertrain: str, cycle: str) -> int:
    """Position of a run in catalog order, which is how the pages index runs."""
    return next(
        i for i, e in enumerate(CATALOG) if e.powertrain == powertrain and e.cycle == cycle
    )


# --- every page renders ---------------------------------------------------------------------


@pytest.mark.parametrize("page", [OVERVIEW, TRACE, COMPARE])
def test_page_runs_without_exception(page):
    app = run(page)
    assert app.title, "page rendered no title"


# --- the overview shows the workbooks' own figures -------------------------------------------


def test_overview_matrix_matches_the_workbook():
    """Petrol Francorchamps eco must read 245.730 g CO2/km, as workbook 07 reports.

    Cells are formatted strings so a known gap can be labelled in place, so compare text.
    """
    app = run(OVERVIEW)
    matrix = app.dataframe[0].value
    assert matrix.loc["Petrol", "Francorchamps — eco"] == "245.730"
    assert matrix.loc["Battery electric", "Francorchamps — eco"] == "47.137"


def test_overview_fuel_consumption_matches_and_bev_is_blank():
    app = run(OVERVIEW)
    app.radio[0].set_value("consumption_l_per_100km").run()
    assert not app.exception, [e.value for e in app.exception]
    matrix = app.dataframe[0].value
    assert matrix.loc["Petrol", "Francorchamps — eco"] == "10.273"
    assert matrix.loc["Full hybrid", "Francorchamps — eco"] == "7.575"
    # A BEV reports no fuel consumption; the cell must be blank, not zero.
    assert matrix.loc["Battery electric", "Francorchamps — eco"] == "—"


def test_overview_flags_the_missing_nedc_phev_data():
    """The lecturer confirmed 34 NEDC PHYBRID has no fuel data; it must be labelled, not shown
    as a bare zero that reads like a result."""
    app = run(OVERVIEW)
    warnings = " ".join(w.value for w in app.warning)
    assert "Data missing — to be filled" in warnings
    assert "Plug-in hybrid" in warnings

    # and the cell itself carries the label, not just the banner
    matrix = app.dataframe[0].value
    assert matrix.loc["Plug-in hybrid", "NEDC"] == "0.000 — to be filled"


def test_overview_still_reports_the_negative_energy_rows():
    """The PHEV negative energy rows are a separate, still-descriptive note."""
    app = run(OVERVIEW)
    notes = " ".join(m.value for m in app.markdown)
    assert "negative value" in notes


def test_overview_survives_an_empty_selection():
    app = run(OVERVIEW)
    app.multiselect[0].set_value([]).run()
    assert not app.exception, [e.value for e in app.exception]
    assert any("at least one" in i.value for i in app.info)


# --- trace explorer -------------------------------------------------------------------------


def test_trace_explorer_renders_a_petrol_run():
    app = run(TRACE)
    app.selectbox(key="trace_run").set_value(run_index("petrol", "franco_eco")).run()
    assert not app.exception, [e.value for e in app.exception]
    trace = app.dataframe[0].value
    assert len(trace) == 32
    assert trace["speed_kph"].iloc[0] == pytest.approx(90.0)


def test_trace_explorer_handles_a_bev_with_no_gear_column():
    """The electric runs have no gear column; the page must say so, not raise."""
    app = run(TRACE)
    app.selectbox(key="trace_run").set_value(run_index("bev", "franco_eco")).run()
    assert not app.exception, [e.value for e in app.exception]
    captions = " ".join(c.value for c in app.caption)
    assert "no gear column" in captions


def test_trace_explorer_handles_the_zeroed_nedc_phev():
    app = run(TRACE)
    app.selectbox(key="trace_run").set_value(run_index("phev", "nedc")).run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.dataframe[0].value) > 100


# --- compare ---------------------------------------------------------------------------------


def test_compare_lists_differing_inputs():
    app = run(COMPARE)
    app.selectbox(key="cmp_left").set_value(run_index("petrol", "franco_eco")).run()
    app.selectbox(key="cmp_right").set_value(run_index("hybrid", "franco_eco")).run()
    assert not app.exception, [e.value for e in app.exception]
    figures = app.dataframe[0].value
    assert "Figure" in figures.columns
    # Petrol vs hybrid on the same lap differ in mass, so something must be listed.
    differences = app.dataframe[1].value
    assert len(differences) > 0


def test_compare_refuses_two_identical_runs():
    app = run(COMPARE)
    index = run_index("petrol", "franco_eco")
    app.selectbox(key="cmp_left").set_value(index).run()
    app.selectbox(key="cmp_right").set_value(index).run()
    assert not app.exception, [e.value for e in app.exception]
    assert any("same run" in i.value for i in app.info)


def test_compare_avoids_percentage_change_from_zero():
    """NEDC PHEV reports 0, so a percent change against it must be suppressed, not infinite."""
    app = run(COMPARE)
    app.selectbox(key="cmp_left").set_value(run_index("phev", "nedc")).run()
    app.selectbox(key="cmp_right").set_value(run_index("petrol", "nedc")).run()
    assert not app.exception, [e.value for e in app.exception]
    changes = app.dataframe[0].value["Change"].tolist()
    assert not any(isinstance(c, float) for c in changes)
    assert "inf" not in " ".join(str(c) for c in changes).lower()


def test_compare_renders_absent_parameters_as_a_dash_not_none():
    """A parameter present in only one workbook must not print the literal "None"."""
    app = run(COMPARE)
    app.selectbox(key="cmp_left").set_value(run_index("petrol", "franco_eco")).run()
    app.selectbox(key="cmp_right").set_value(run_index("hybrid", "franco_eco")).run()
    differences = app.dataframe[1].value
    for column in differences.columns[1:]:
        assert not (differences[column] == "None").any()
        assert pd.api.types.is_numeric_dtype(differences[column])


def test_compare_says_when_two_runs_share_a_trace():
    """Petrol and hybrid on the same lap have identical speed traces; the lines coincide."""
    app = run(COMPARE)
    app.selectbox(key="cmp_left").set_value(run_index("petrol", "franco_eco")).run()
    app.selectbox(key="cmp_right").set_value(run_index("hybrid", "franco_eco")).run()
    captions = " ".join(c.value for c in app.caption)
    assert "the two lines coincide" in captions


def test_overview_defines_every_cycle():
    """Each cycle gets a definition plus facts measured from the files, not quoted."""
    app = run(OVERVIEW)
    text = " ".join(m.value for m in app.markdown)
    assert "New European Driving Cycle" in text
    assert "Spa-Francorchamps" in text

    captions = " ".join(c.value for c in app.caption)
    assert "In these files:" in captions
    # NEDC is flat and spends a large share of its steps stationary; the lap is neither.
    assert "flat" in captions
    assert "elevation range" in captions


def test_nedc_distance_is_not_offered_as_an_axis():
    """NEDC records distance per step, so it does not run forward and must not be an x-axis."""
    app = run(TRACE)
    app.selectbox(key="trace_run").set_value(run_index("petrol", "nedc")).run()
    assert not app.exception, [e.value for e in app.exception]
    # AppTest exposes the formatted labels, not the underlying column names.
    axis_options = app.selectbox[1].options
    assert "Distance (m)" not in axis_options
    assert "Time (s)" in axis_options
    captions = " ".join(c.value for c in app.caption)
    assert "recorded per step in this workbook rather than cumulatively" in captions


def test_francorchamps_distance_is_offered_as_an_axis():
    app = run(TRACE)
    app.selectbox(key="trace_run").set_value(run_index("petrol", "franco_eco")).run()
    assert "Distance (m)" in app.selectbox[1].options


@pytest.mark.parametrize("page", [TRACE, COMPARE])
def test_missing_data_is_flagged_on_every_page_showing_that_run(page):
    """Selecting the incomplete run anywhere must surface the same notice."""
    app = run(page)
    key = "trace_run" if page == TRACE else "cmp_left"
    app.selectbox(key=key).set_value(run_index("phev", "nedc")).run()
    assert not app.exception, [e.value for e in app.exception]
    warnings = " ".join(w.value for w in app.warning)
    assert "to be filled" in warnings


def test_complete_runs_are_not_flagged():
    """The notice must not appear for runs whose data is present."""
    app = run(TRACE)
    app.selectbox(key="trace_run").set_value(run_index("petrol", "franco_eco")).run()
    warnings = " ".join(w.value for w in app.warning)
    assert "to be filled" not in warnings


def test_axis_exclusion_reason_distinguishes_empty_from_per_step():
    """Distance is per-step in NEDC petrol but simply empty in NEDC electric."""
    from dashboard.loaders import axis_exclusion_reason, trace_for

    petrol = trace_for.__wrapped__("petrol", "nedc")
    reason = axis_exclusion_reason(petrol, "distance_m")
    assert reason is not None and "per step" in reason

    bev = trace_for.__wrapped__("bev", "nedc")
    reason = axis_exclusion_reason(bev, "distance_m")
    assert reason is not None and "empty" in reason
    assert "per step" not in reason


def test_axis_exclusion_reason_is_none_when_the_column_works():
    """Francorchamps distance is cumulative, so there is nothing to explain."""
    from dashboard.loaders import axis_exclusion_reason, trace_for

    lap = trace_for.__wrapped__("petrol", "franco_eco")
    assert axis_exclusion_reason(lap, "distance_m") is None
    assert axis_exclusion_reason(lap, "not_a_column") is None


def test_compare_and_category_view_agree_on_what_differs():
    """Both pages must answer "what differs" identically — one implementation, not two."""
    from dashboard.layout import varying_parameters
    from dashboard.loaders import load_runs

    runs = load_runs.__wrapped__()
    pair = runs[
        ((runs["powertrain"] == "petrol") | (runs["powertrain"] == "hybrid"))
        & (runs["cycle"] == "franco_eco")
    ]
    expected = set(varying_parameters(pair)["Parameter"])

    app = run(COMPARE)
    app.selectbox(key="cmp_left").set_value(run_index("petrol", "franco_eco")).run()
    app.selectbox(key="cmp_right").set_value(run_index("hybrid", "franco_eco")).run()
    shown = set(app.dataframe[1].value["Parameter"])

    assert shown == expected
