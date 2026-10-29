"""The Category view page shows every run in one category together."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

CATEGORY_VIEW = str(ROOT / "dashboard" / "pages" / "2_Category_View.py")


def run(axis_name: str | None = None, choice: str | None = None) -> AppTest:
    app = AppTest.from_file(CATEGORY_VIEW, default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    if axis_name is not None:
        app.radio[0].set_value(axis_name).run()
        assert not app.exception, [e.value for e in app.exception]
    if choice is not None:
        app.selectbox[0].set_value(choice).run()
        assert not app.exception, [e.value for e in app.exception]
    return app


def test_page_renders():
    app = run()
    assert app.title[0].value == "Category view"


def test_powertrain_category_shows_three_runs():
    app = run("Powertrain", "petrol")
    text = " ".join(m.value for m in app.markdown) + " ".join(c.value for c in app.caption)
    assert "3 runs" in text


def test_cycle_category_shows_four_runs():
    app = run("Cycle", "nedc")
    text = " ".join(m.value for m in app.markdown) + " ".join(c.value for c in app.caption)
    assert "4 runs" in text


def test_all_sport_is_reachable_through_the_cycle_category():
    """"All the sport" is the Francorchamps sport cycle category."""
    app = run("Cycle", "franco_sport")
    table = app.dataframe[0].value
    assert len(table) == 4
    assert "Petrol" in set(table["Run"])
    assert "Plug-in hybrid" in set(table["Run"])


def test_totals_table_carries_every_canonical_figure():
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value
    for heading in ("CO₂ per km (g CO₂/km)", "Fuel consumption (l/100 km)"):
        assert heading in table.columns


def test_petrol_category_shows_the_workbook_figures():
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value.set_index("Run")
    assert table.loc["Francorchamps — eco", "CO₂ per km (g CO₂/km)"] == "245.730"
    assert table.loc["NEDC", "CO₂ per km (g CO₂/km)"] == "158.288"


def test_incomplete_run_is_flagged_in_its_categories():
    """The NEDC plug-in hybrid gap must show in both categories that contain it."""
    for axis_name, choice in (("Cycle", "nedc"), ("Powertrain", "phev")):
        app = run(axis_name, choice)
        warnings = " ".join(w.value for w in app.warning)
        assert "electricity not counted" in warnings, f"{axis_name}={choice}"


def test_varying_parameters_are_listed():
    app = run("Powertrain", "petrol")
    names = set(app.dataframe[1].value["Parameter"])
    assert any(n.startswith("total mass") for n in names)


def test_axis_falls_back_when_the_category_shares_no_distance():
    """The BEV category shares no usable distance or time column, so it plots against step."""
    app = run("Powertrain", "bev")
    assert not app.exception, [e.value for e in app.exception]
    axis = app.selectbox[3]
    assert axis.options == ["Step"]


def test_powertrain_category_separates_members_by_dash():
    """All three petrol runs share one colour, so dash must tell them apart."""
    from dashboard import charts
    from dashboard.loaders import trace_for
    from dashboard.theme import DARK

    frames = [trace_for.__wrapped__("petrol", c)
              for c in ("franco_eco", "franco_sport", "nedc")]
    colours = [DARK.for_powertrain("petrol")] * 3
    fig = charts.overlay_traces(
        frames, ["eco", "sport", "NEDC"], colours, "speed_kph", "step", DARK,
        dashes=list(charts.DASH_CYCLE[:3]),
    )
    assert len({t.line.color for t in fig.data}) == 1, "colour must stay bound to powertrain"
    assert len({t.line.dash for t in fig.data}) == 3, "members must be distinguishable"


def test_figures_table_shows_a_dash_not_none_for_an_unreported_figure():
    """Petrol runs report no electrical energy; the cell must be blank, not the word None."""
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value
    column = "Electrical energy (Wh/100 km)"
    values = set(table[column].astype(str))
    assert "None" not in values
    assert values == {"—"}


def test_figures_table_marks_the_known_gap():
    """The NEDC plug-in hybrid has no fuel data; its zeros must not read as results."""
    app = run("Cycle", "nedc")
    table = app.dataframe[0].value.set_index("Run")
    assert table.loc["Plug-in hybrid", "CO₂ per km (g CO₂/km)"] == "0.000 — electricity not counted"
    # a complete run in the same table is untouched
    assert table.loc["Petrol", "CO₂ per km (g CO₂/km)"] == "158.288"


def test_figures_table_formats_to_three_decimals():
    app = run("Powertrain", "petrol")
    table = app.dataframe[0].value.set_index("Run")
    assert table.loc["Francorchamps — eco", "CO₂ per km (g CO₂/km)"] == "245.730"


def test_varying_table_explains_its_blanks():
    app = run("Cycle", "nedc")
    captions = " ".join(c.value for c in app.caption)
    assert "absent from" in captions


def test_page_requests_dashes_only_for_a_powertrain_category(monkeypatch):
    """Guards the call site: AppTest cannot see a figure, so capture the argument."""
    from dashboard import charts

    captured: list[object] = []
    original = charts.overlay_traces

    def spy(*args, **kwargs):
        captured.append(kwargs.get("dashes"))
        return original(*args, **kwargs)

    monkeypatch.setattr(charts, "overlay_traces", spy)

    run("Powertrain", "petrol")
    assert captured and captured[-1] is not None, "a powertrain category needs dashes"
    assert len(set(captured[-1])) == 3

    captured.clear()
    run("Cycle", "nedc")
    assert captured and captured[-1] is None, "a cycle category is separated by colour"
