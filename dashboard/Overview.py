"""The app's entry point: the menu, in two labelled groups.

Run with: `streamlit run dashboard/Overview.py`. The file keeps its old name so the hosted app's
entry point does not change; the pages themselves are in `views/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit puts the script's own directory on sys.path, not the repo root, so neither `pwt`
# nor `dashboard` is importable without this.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

PAGES = Path(__file__).resolve().parent / "views"

#: The workbooks' figures as reported, then what `pwt.model` computes.
MENU = {
    "The workbooks": [
        st.Page(PAGES / "1_Overview.py", title="Overview", url_path="overview",
                default=True),
        st.Page(PAGES / "2_Category_View.py", title="Category view", url_path="category-view"),
        st.Page(PAGES / "3_Trace_Explorer.py", title="Trace explorer", url_path="trace-explorer"),
        st.Page(PAGES / "4_Compare.py", title="Compare", url_path="compare"),
        st.Page(PAGES / "5_Data.py", title="Data", url_path="data"),
    ],
    "The model": [
        st.Page(PAGES / "6_Model.py", title="Model", url_path="model"),
        st.Page(PAGES / "7_Sizing.py", title="Sizing", url_path="sizing"),
        st.Page(PAGES / "8_Track_Map.py", title="Track map", url_path="track-map"),
        st.Page(PAGES / "9_Study_B.py", title="Study B", url_path="study-b"),
    ],
}

st.navigation(MENU).run()
