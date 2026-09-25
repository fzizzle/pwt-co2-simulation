"""The Data page must render every dataset, and its download must match what is shown."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.loaders import params_long, totals_long
from pwt.build import runs_frame
from pwt.catalog import CATALOG, course_file
from pwt.workbook import read_block, read_run

DATA = str(ROOT / "dashboard" / "pages" / "4_Data.py")
DATASETS = ["Runs", "Totals", "Parameters", "Traces", "Workbook cells"]


def run(dataset: str | None = None) -> AppTest:
    app = AppTest.from_file(DATA, default_timeout=180).run()
    assert not app.exception, [e.value for e in app.exception]
    if dataset is not None:
        app.radio[0].set_value(dataset).run()
        assert not app.exception, [e.value for e in app.exception]
    return app


@pytest.mark.parametrize("dataset", DATASETS)
def test_every_dataset_renders_rows(dataset):
    app = run(dataset)
    assert app.dataframe, f"{dataset} rendered no table"
    assert len(app.dataframe[0].value) > 0


def test_runs_dataset_covers_all_twelve():
    app = run("Runs")
    assert len(app.dataframe[0].value) == 12


def test_filters_narrow_the_table():
    app = run("Totals")
    before = len(app.dataframe[0].value)
    app.multiselect[0].set_value(["petrol"]).run()  # powertrains
    assert not app.exception, [e.value for e in app.exception]
    after = len(app.dataframe[0].value)
    assert 0 < after < before


def test_empty_selection_explains_itself():
    app = run("Totals")
    app.multiselect[0].set_value([]).run()
    assert not app.exception, [e.value for e in app.exception]
    assert any("Nothing matches" in i.value for i in app.info)


def test_display_names_not_internal_codes():
    app = run("Totals")
    table = app.dataframe[0].value
    assert "Petrol" in set(table["powertrain"])
    assert "petrol" not in set(table["powertrain"])


# --- the raw block is genuinely raw ------------------------------------------------------------


def test_workbook_cells_keep_original_label_text():
    """The rawest view must not show the reader's normalised keys in place of the sheet's text."""
    block = read_block(course_file("07 SPA Franco PETROL car ECO Driving.xlsx"))
    labels = set(block["label"])
    assert "Total consumption:" in labels  # original, colon and capital intact
    assert "Wheel diameter" in labels
    row = block[block["label"] == "Total consumption:"].iloc[0]
    assert row["key_label"] == "total consumption"  # normalised key shown alongside
    assert row["kind"] == "total"
    assert row["value"] == pytest.approx(10.2730, rel=1e-4)


def test_workbook_cells_expose_the_hybrid_column_b_quirk():
    """In file 10 column B holds a coefficient, not a unit; the raw view must show both."""
    block = read_block(course_file("10 SPA Franco HYBRID engine ECO Driving.xlsx"))
    row = block[block["label"] == "A1"].iloc[0]
    assert row["unit"] == "-0.3867"  # what the cell literally contains
    assert row["key_unit"] == ""  # what it was keyed under, numeric B ignored
    assert row["value"] == pytest.approx(-1.0778, rel=1e-3)  # column C, the active curve


def test_workbook_cells_carry_row_numbers_for_every_catalogued_file():
    for entry in CATALOG:
        block = read_block(course_file(entry.filename))
        assert not block.empty, entry.filename
        assert block["row"].is_monotonic_increasing
        assert block["row"].min() >= 3


# --- long views ---------------------------------------------------------------------------------


def test_long_views_split_quantity_from_unit():
    runs = runs_frame([read_run(course_file(e.filename)) for e in CATALOG])
    totals = totals_long(runs)
    assert {"quantity", "unit", "value"} <= set(totals.columns)
    # The two same-labelled emission rows survive as separate rows, told apart by unit.
    emissions = totals[
        (totals["quantity"] == "total emission") & (totals["source_file"].str.startswith("07"))
    ]
    assert set(emissions["unit"]) == {"g co2", "g co2/km"}

    params = params_long(runs)
    gear = params[(params["parameter"] == "gear ratio 1")]
    assert not gear.empty
    assert set(gear["unit"]) == {""}  # no unit in the sheet, and none invented
