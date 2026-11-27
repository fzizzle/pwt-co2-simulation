"""Accuracy tests for the Data page: workbook-scoped notices and no derived PHEV numbers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

DATA = str(ROOT / "dashboard" / "views" / "5_Data.py")
DERIVED_FRAGMENTS = ("14.3", "36 g", "5.96", "2.22", "data/derived", "UN R101")


def _all_rendered_text(app: AppTest) -> str:
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


def test_workbook_cells_default_petrol_has_no_phev_warning():
    """Default Workbook cells view shows a petrol workbook and must not warn about PHEV NEDC."""
    app = AppTest.from_file(DATA, default_timeout=120).run()
    app.radio[0].set_value("Workbook cells").run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.warning, f"Unexpected warning on petrol workbook: {[w.value for w in app.warning]}"
    # Independent sidebar filters must not be applied/shown in Workbook cells mode.
    filter_labels = [m.label for m in app.multiselect]
    assert "Powertrains" not in filter_labels
    assert "Cycles" not in filter_labels


def test_workbook_cells_phev_nedc_shows_warning_without_derived_numbers():
    """Selecting 34 NEDC PHYBRID shows its notice and does not quote model-derived numbers."""
    app = AppTest.from_file(DATA, default_timeout=120).run()
    app.radio[0].set_value("Workbook cells").run()
    app.selectbox[0].set_value("34 NEDC PHYBRID engine.xlsx").run()
    assert not app.exception, [e.value for e in app.exception]
    warnings = " ".join(w.value for w in app.warning)
    assert "electricity not counted" in warnings
    assert "Plug-in hybrid" in warnings
    full_text = _all_rendered_text(app)
    for forbidden in DERIVED_FRAGMENTS:
        assert forbidden not in full_text, f"Derived fragment {forbidden!r} leaked into Data notice"


def test_workbook_cells_warning_ignores_prior_sidebar_filters():
    """Excluding PHEV in another dataset must not hide the warning in Workbook cells mode."""
    app = AppTest.from_file(DATA, default_timeout=120).run()
    app.radio[0].set_value("Totals").run()
    app.multiselect[0].set_value(["petrol"]).run()
    assert not app.warning
    app.radio[0].set_value("Workbook cells").run()
    app.selectbox[0].set_value("34 NEDC PHYBRID engine.xlsx").run()
    assert not app.exception, [e.value for e in app.exception]
    assert any("electricity not counted" in w.value for w in app.warning)


def test_filtered_modes_show_clean_notice_only_when_phev_nedc_included():
    """In filtered dataset modes, the notice tracks the filter and omits derived PHEV figures."""
    app = AppTest.from_file(DATA, default_timeout=120).run()
    app.radio[0].set_value("Totals").run()
    # Default includes all runs -> PHEV NEDC warning appears without derived numbers.
    assert any("electricity not counted" in w.value for w in app.warning)
    full_text = _all_rendered_text(app)
    for forbidden in DERIVED_FRAGMENTS:
        assert forbidden not in full_text, f"Derived fragment {forbidden!r} leaked into Data notice"
    # Filtering out PHEV removes the warning.
    app.multiselect[0].set_value(["petrol"]).run()
    assert not app.exception, [e.value for e in app.exception]
    assert not app.warning


def test_intro_scoped_to_workbook_datasets():
    """Intro text must not claim coverage of model/study pages."""
    app = AppTest.from_file(DATA, default_timeout=120).run()
    intro = " ".join(m.value for m in app.markdown)
    assert "Every dataset behind the other pages" not in intro
