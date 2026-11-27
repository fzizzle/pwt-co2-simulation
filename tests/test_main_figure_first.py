"""Each page opens on its main figure; Home is one composed stage.

Task 4 of docs/superpowers/plans/2026-11-27-dashboard-polish.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from dashboard.charts import GAP_LABEL
from pwt.catalog import CATALOG

VIEWS = ROOT / "dashboard" / "views"
ENTRY = str(ROOT / "dashboard" / "Overview.py")
HOME = str(VIEWS / "0_Home.py")
OVERVIEW = str(VIEWS / "1_Overview.py")
COMPARE = str(VIEWS / "4_Compare.py")
MODEL = str(VIEWS / "6_Model.py")
TIMEOUT = 180


def run(page: str) -> AppTest:
    app = AppTest.from_file(page, default_timeout=TIMEOUT).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def order(app: AppTest) -> list[tuple[str, str]]:
    """Top-level elements of the main column, in render order, as (type, label or text)."""
    out = []
    for node in app.main.children.values():
        label = getattr(node, "label", None)
        if not isinstance(label, str):
            label = getattr(node, "value", "") if isinstance(getattr(node, "value", ""), str) else ""
        out.append((node.type, label))
    return out


def first(seq, pred) -> int:
    return next(i for i, item in enumerate(seq) if pred(item))


# --- Home ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def home():
    return run(HOME)


def _home_html(app) -> str:
    return " ".join(getattr(h, "value", "") or getattr(h, "body", "") for h in app.html)


def test_home_has_no_sequence_numbers(home):
    text = _home_html(home) + " ".join(m.value for m in home.markdown)
    assert not re.search(r">\s*0[1-9]\s*<", text)


def test_home_hero_has_no_card_border(home):
    hero = next(h for h in home.html if "pwt-hero" in (getattr(h, "value", "") or ""))
    style = hero.value.split(">", 1)[0]
    assert "border:" not in style.replace("border-radius", "")


def test_home_preview_is_the_chart_alone(home):
    html = _home_html(home)
    assert "highway cycle" not in html
    assert "WLTC Class 3" in html
    # The four values live on the chart, not in a row of repeated cards.
    assert "feasible on every step" not in html and "short on" not in html
    assert len(home.get("plotly_chart")) == 1


def test_entry_point_offers_three_task_links():
    app = run(ENTRY)
    links = app.get("page_link")
    assert len(links) == 3


def test_home_is_served_at_the_root_only():
    source = Path(ENTRY).read_text(encoding="utf-8")
    home_line = next(line for line in source.splitlines() if "0_Home.py" in line)
    assert "default=True" in home_line
    assert "url_path" not in home_line


# --- Overview -----------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def overview():
    return run(OVERVIEW)


def test_overview_chart_leads(overview):
    seq = order(overview)
    chart = first(seq, lambda e: e[0] == "plotly_chart")
    assert chart < first(seq, lambda e: e[0] == "dataframe")
    assert chart < first(seq, lambda e: e[0] == "warning")


def test_overview_measure_is_in_main_not_sidebar(overview):
    assert overview.radio(key="wb_measure_overview") is not None
    assert len(overview.sidebar.radio) == 0
    assert len(overview.sidebar.multiselect) == 0


def test_overview_keeps_the_nedc_phev_gap_mark(overview):
    matrix = overview.dataframe[0].value
    assert matrix.loc["Plug-in hybrid", "NEDC"].endswith(GAP_LABEL)
    captions = " ".join(c.value for c in overview.caption)
    assert GAP_LABEL in captions


# --- Model --------------------------------------------------------------------------------------


def test_model_chart_comes_before_its_tables():
    app = run(MODEL)
    seq = order(app)
    chart = first(seq, lambda e: e[0] == "plotly_chart")
    tables = first(seq, lambda e: e[0] == "expander" and e[1] == "Scenario tables")
    assert chart < tables
    assert not any(t == "dataframe" for t, _ in seq[:tables]), "a table sits outside the expander"


# --- Compare ------------------------------------------------------------------------------------


def test_compare_trace_before_parameter_differences():
    app = run(COMPARE)
    seq = order(app)
    chart = first(seq, lambda e: e[0] == "plotly_chart")
    params = first(seq, lambda e: e[0] == "subheader" and e[1] == "Parameter differences")
    assert chart < params
