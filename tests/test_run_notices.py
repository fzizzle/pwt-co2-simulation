"""Tests for shared workbook RUN_NOTICES: workbook-only facts, no derived figures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.layout import RUN_NOTICES

VIEWS = ROOT / "dashboard" / "views"
FORBIDDEN_DERIVED = ("14.3", "36 g", "5.96", "2.22", "250 g", "data/derived", "UN R101")


def _all_text(app: AppTest) -> str:
    parts = [
        *(w.value for w in app.warning),
        *(m.value for m in app.markdown),
        *(c.value for c in app.caption),
        *(i.value for i in app.info),
    ]
    for exp in app.expander:
        parts.extend(m.value for m in exp.markdown)
        parts.extend(c.value for c in exp.caption)
        parts.extend(w.value for w in exp.warning)
    return "\n".join(parts)


def test_run_notices_contain_no_derived_or_model_figures():
    """Shared workbook notices must state only workbook facts and point to the Model page."""
    short, detail = RUN_NOTICES[("phev", "nedc")]
    combined = f"{short}\n{detail}"
    for forbidden in FORBIDDEN_DERIVED:
        assert forbidden not in combined, f"Derived fragment {forbidden!r} found in RUN_NOTICES"
    assert "electricity not counted" in short.lower()
    assert "0 l/100 km" in short
    assert "0 g CO₂/km" in short
    assert "Model" in detail


@pytest.mark.parametrize(
    "view_name",
    ["1_Overview.py", "2_Category_View.py", "3_Trace_Explorer.py", "4_Compare.py", "5_Data.py"],
)
def test_workbook_pages_show_phev_nedc_notice_without_derived_numbers(view_name: str):
    """Every workbook page showing the PHEV NEDC run must omit model-computed numbers."""
    app = AppTest.from_file(str(VIEWS / view_name), default_timeout=120).run()
    assert not app.exception, [e.value for e in app.exception]

    if view_name == "2_Category_View.py":
        app.radio[0].set_value("Cycle").run()
        app.selectbox[0].set_value("nedc").run()
    elif view_name == "3_Trace_Explorer.py":
        from pwt.catalog import CATALOG

        idx = next(i for i, e in enumerate(CATALOG) if e.powertrain == "phev" and e.cycle == "nedc")
        app.selectbox(key="trace_run").set_value(idx).run()
    elif view_name == "4_Compare.py":
        from pwt.catalog import CATALOG

        idx = next(i for i, e in enumerate(CATALOG) if e.powertrain == "phev" and e.cycle == "nedc")
        app.selectbox(key="cmp_left").set_value(idx).run()

    assert not app.exception, [e.value for e in app.exception]
    warnings = " ".join(w.value for w in app.warning)
    assert "electricity not counted" in warnings.lower()
    text = _all_text(app)
    for forbidden in FORBIDDEN_DERIVED:
        assert forbidden not in text, f"{forbidden!r} leaked into {view_name}"
    assert "Model" in text
