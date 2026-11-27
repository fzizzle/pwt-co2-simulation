"""Tests for persistent workbook filters, measure, and run selections across pages with reset."""

from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENTRY = str(ROOT / "dashboard" / "Overview.py")


def test_measure_and_filters_persist_from_overview_to_data_and_back():
    """UX finding 6: selecting Fuel consumption and filters on Overview must survive visiting Data."""
    app = AppTest.from_file(ENTRY, default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]

    # Visit Overview, choose Fuel consumption, filter to Petrol + NEDC.
    app.switch_page("views/1_Overview.py").run()
    assert not app.exception, [e.value for e in app.exception]
    app.radio[0].set_value("consumption_l_per_100km").run()
    app.multiselect[0].set_value(["petrol"]).run()
    app.multiselect[1].set_value(["nedc"]).run()
    assert not app.exception, [e.value for e in app.exception]

    # Visit Data: sidebar Powertrains and Driving cycles filters must carry over.
    app.switch_page("views/5_Data.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.multiselect(key="wb_filter_powertrains_data").value == ["petrol"]
    assert app.multiselect(key="wb_filter_cycles_data").value == ["nedc"]
    assert len(app.dataframe[0].value) == 1

    # Return to Overview: measure AND filters must still be intact.
    app.switch_page("views/1_Overview.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.radio[0].value == "consumption_l_per_100km"
    assert app.multiselect(key="wb_filter_powertrains_overview").value == ["petrol"]
    assert app.multiselect(key="wb_filter_cycles_overview").value == ["nedc"]


def test_measure_persists_between_overview_and_category_view():
    app = AppTest.from_file(ENTRY, default_timeout=120).run()
    app.switch_page("views/1_Overview.py").run()
    app.radio[0].set_value("energy_wh_per_100km").run()

    app.switch_page("views/2_Category_View.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key="wb_measure_category").value == "energy_wh_per_100km"

    # Changing measure on Category view carries back to Overview.
    app.selectbox(key="wb_measure_category").set_value("consumption_l_per_100km").run()
    app.switch_page("views/1_Overview.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.radio[0].value == "consumption_l_per_100km"


def test_trace_and_compare_run_selections_persist_across_navigation():
    from pwt.catalog import CATALOG

    phev_nedc = next(
        i for i, e in enumerate(CATALOG) if e.powertrain == "phev" and e.cycle == "nedc"
    )
    bev_sport = next(
        i for i, e in enumerate(CATALOG) if e.powertrain == "bev" and e.cycle == "franco_sport"
    )

    app = AppTest.from_file(ENTRY, default_timeout=120).run()
    app.switch_page("views/3_Trace_Explorer.py").run()
    app.selectbox(key="trace_run").set_value(phev_nedc).run()

    app.switch_page("views/4_Compare.py").run()
    app.selectbox(key="cmp_left").set_value(bev_sport).run()

    app.switch_page("views/3_Trace_Explorer.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key="trace_run").value == phev_nedc

    app.switch_page("views/4_Compare.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.selectbox(key="cmp_left").value == bev_sport


def test_reset_button_restores_all_workbook_selections():
    app = AppTest.from_file(ENTRY, default_timeout=120).run()
    app.switch_page("views/1_Overview.py").run()
    app.radio[0].set_value("consumption_l_per_100km").run()
    app.multiselect[0].set_value(["petrol"]).run()
    app.multiselect[1].set_value(["nedc"]).run()

    reset_btn = app.button(key="wb_reset_btn_overview")
    reset_btn.click().run()
    assert not app.exception, [e.value for e in app.exception]
    assert app.radio[0].value == "co2_g_per_km"
    assert len(app.multiselect[0].value) == 4
    assert len(app.multiselect[1].value) == 3

    # Verify reset persists when navigating to Data too.
    app.switch_page("views/5_Data.py").run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.multiselect(key="wb_filter_powertrains_data").value) == 4
    assert len(app.multiselect(key="wb_filter_cycles_data").value) == 3
