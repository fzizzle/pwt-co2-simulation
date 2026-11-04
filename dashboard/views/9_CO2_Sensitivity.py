"""Study B report, interactive sensitivity results and research extensions."""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.layout import configure, download
from dashboard import sensitivity_charts as _sensitivity_charts

# A running Streamlit process may retain an imported helper after the page updates.
# Recover the same way dashboard.loaders handles newly added workbook helpers.
if any(not hasattr(_sensitivity_charts, name)
       for name in ("comparison_table", "leaders", "research_table", "tornado", "ranking_visual", "variable_key", "elasticity_panels")):
    _sensitivity_charts = importlib.reload(_sensitivity_charts)

from dashboard.sensitivity_charts import (comparison_table, leaders, research_table, tornado,
                                          ranking_visual, variable_key, elasticity_panels)
from pwt.catalog import POWERTRAIN_NAMES
from pwt.sensitivity import swings
from pwt.sweep import CYCLES

DOCS = ROOT / "docs"
pal = configure("CO₂ sensitivity")


@st.cache_data(show_spinner=False)
def read_table(filename: str, modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(DOCS / filename)


def table(name: str) -> pd.DataFrame:
    filename = f"study-b-{name}.csv"
    path = DOCS / filename
    return read_table(filename, path.stat().st_mtime_ns)


def render_report(text: str) -> None:
    """Render local report figures inline; downloads provide its referenced artifacts."""
    parts = re.split(r"!\[([^\]]*)\]\(([^)]+)\)", text)
    for index in range(0, len(parts), 3):
        # Repo-relative documents are downloads below, not URLs on the Streamlit server.
        markdown = re.sub(r"\[([^\]]+)\]\((?!https?://)[^)]+\)", r"\1", parts[index])
        st.markdown(markdown)
        if index+2 < len(parts):
            path = (DOCS / parts[index+2]).resolve()
            if path.parent == DOCS.resolve() and path.is_file():
                st.image(str(path), caption=parts[index+1], width="stretch")


st.title("Study B · CO₂ sensitivity")
st.markdown("Change one vehicle factor at a time and see which moves emissions most. "
            "The original study uses the same driving trace for every car.")
st.caption("Owner-review draft · Assignment vehicles · Storage losses included · Saved study results")

try:
    results = table("results")
except FileNotFoundError:
    st.error("The saved Study B results are missing. Restore the study files before opening this page.")
    st.stop()

left, middle, right = st.columns(3)
powertrain = left.selectbox("Car", list(POWERTRAIN_NAMES), format_func=POWERTRAIN_NAMES.get,
                           key="study_b_powertrain")
cycle = middle.selectbox("Driving cycle", list(CYCLES), index=3, format_func=CYCLES.get,
                         key="study_b_cycle")
grid = right.selectbox("Electricity grid", ["co2_eu", "co2_fr"],
                       format_func=lambda value: "EU · 250 g CO₂/kWh" if value == "co2_eu" else "France · 73 g CO₂/kWh",
                       key="study_b_grid")

try:
    ranked = swings(results, grid)
except ValueError as error:
    st.error(f"The study results failed validation: {error}")
    st.stop()
selected = ranked[(ranked.powertrain == powertrain) & (ranked.cycle == cycle)]
baseline = results[(results.powertrain == powertrain) & (results.cycle == cycle) & (results.factor == "baseline")].iloc[0]

explore, compare, research, report_tab = st.tabs(["Explore sensitivities", "Compare elasticities", "Research checks", "Full report & downloads"])
with explore:
    st.subheader(f"{POWERTRAIN_NAMES[powertrain]} · {CYCLES[cycle]}")
    passing_only = st.toggle("Only comparisons passing the engine-power check", key="study_b_passing")
    visible = selected[selected.engine_check_pass] if passing_only else selected
    a, b, c = st.columns(3)
    a.metric("Baseline emissions", f"{baseline[grid]:.1f} g/km")
    b.metric("Largest response", leaders(visible))
    c.metric("Largest endpoint span", "—" if visible.empty else f"{visible.swing.max():.2f} g/km")
    if baseline.short_steps:
        st.warning(f"The baseline cannot follow this trace on {int(baseline.short_steps)} steps "
                   f"(shortfall up to {baseline.short_kw:.2f} kW). All comparisons are provisional.")
    elif not selected.engine_check_pass.all():
        st.warning("Some changed cars cannot follow the requested trace. Their comparisons are marked as provisional.")
    if powertrain == "bev":
        st.info("The BEV has no combustion-engine check. Passing flags do not certify motor, battery or thermal capability.")
    if powertrain == "phev" and cycle in ("nedc", "wltc"):
        st.caption("PHEV regulatory results weight charge-depleting and charge-sustaining runs using R101. "
                   "The engine check uses the charge-sustaining run.")
    if visible.empty:
        st.info("No complete comparison passes: the baseline and both endpoints must pass. "
                "Turn off the filter to inspect the provisional results.")
        st.markdown(variable_key(selected))
    else:
        chart_column, key_column = st.columns([3, 2])
        with chart_column:
            st.plotly_chart(tornado(visible, powertrain, pal), width="stretch", theme=None)
        with key_column:
            st.markdown(variable_key(selected))
        st.caption("Labels show absolute g CO₂/km. Blue circles: parameter −10%; orange diamonds: +10%. "
                   "Hollow markers fail the engine check. Hatched bars have a failing baseline or endpoint.")
        st.plotly_chart(ranking_visual(visible, pal), width="stretch", theme=None)
        st.caption("≈ means the gap is less than 2% of the largest span in that tie group. "
                   "† means provisional. This is a reporting convention, not statistical confidence.")
        numbers = comparison_table(visible)
        st.dataframe(numbers, width="stretch", hide_index=True)
        download(numbers, "pwt-study-b-selected.csv", "Download this comparison")
    with st.expander("How to read the study", expanded=False):
        st.markdown("Each factor is changed alone by ±10%. The span is the absolute difference between "
                    "the two endpoint emissions; longer bars mean a larger response. Signed elasticity "
                    "expresses percent CO₂ change per percent parameter change over this interval. "
                    "Nonlinearity and control thresholds can make that number depend on the interval.")
        st.markdown("**Approved assumptions:** change car-body mass alone; keep driver, battery and machine "
                    "mass fixed; scale peak engine efficiency without changing curve shape; keep the "
                    "baseline petrol lap and hybrid strategies fixed. The electric car has no engine variant.")
        st.markdown("Mass affects acceleration, rolling and climbing work. Drag force grows with speed "
                    "squared. Engine efficiency changes fuel conversion; gear ratios affect rotating "
                    "inertia and engine capability, and also the BEV motor's rpm-dependent efficiency.")
        st.markdown("Equal ±10% changes are not equally achievable or equally costly. A ranking of "
                    "model responses does not establish the best engineering investment.")

with compare:
    st.caption("Model output · Saved study results · Hollow dots mean provisional (†): "
               "the baseline or an endpoint fails the engine check. The BEV engine row is empty.")
    st.subheader("Elasticity by car, per driving cycle")
    st.plotly_chart(elasticity_panels(ranked, "cars", pal), width="stretch", theme=None)
    download(research_table(ranked), f"pwt-study-b-across-cars-{grid}.csv", "Download across-car data")
    st.subheader("Elasticity by driving cycle, per car")
    st.plotly_chart(elasticity_panels(ranked, "cycles", pal), width="stretch", theme=None)
    download(research_table(ranked), f"pwt-study-b-across-cycles-{grid}.csv", "Download across-cycle data")

with research:
    st.subheader("Test the assumptions behind the ranking")
    st.caption("These exploratory checks keep the original study separate. Tables are filtered by "
               "your car and cycle; they retain both EU and French accounting columns.")
    experiments = {
        "intermediate": ("Intermediate points", "All factors add ±5%; gearing also adds ±2.5% and ±7.5%. "
                         "Include the baseline when checking sampled minima; samples do not establish a continuous optimum."),
        "assumptions": ("Mass and engine assumptions", "Total-mass variants change body mass enough to reach ±10% "
                        "total mass. Shape-only engine variants keep eta_max; complete curves also change it. "
                        "The supplied workbook menus are verified to agree."),
        "ranges": ("Technology-inspired ranges", "Road-load ranges draw on DOE/EPA studies. Body-mass mapping and "
                   "engine increments are assumptions; gear increments are exploratory. These are not vehicle-specific "
                   "achievable limits or a cost ranking. Sources and detailed ranges are in the full report."),
        "regenerated": ("Per-vehicle generated laps", "Each petrol/hybrid variant gets its own lap, so speed and "
                        "time now differ. The generator uses engine-only acceleration limits for hybrids; it has "
                        "no BEV motor/battery capability model. Check residual shortfalls, not just consumption."),
        "interactions": ("Two-factor interactions", "A 3×3 grid combines mass with drag/gears, plus engine efficiency "
                         "for hybrids, on WLTC and sport. Interaction equals joint CO₂ minus the two individual "
                         "results plus baseline. Passing requires all four terms to pass the engine check."),
    }
    experiment = st.selectbox("Research check", list(experiments), format_func=lambda value: experiments[value][0],
                              key="study_b_experiment")
    st.markdown(experiments[experiment][1])
    try:
        data = table(experiment)
        rows = data[(data.powertrain == powertrain) & (data.cycle == cycle)]
        if rows.empty:
            st.info("This experiment does not include the selected car/cycle. "
                    "Regenerated laps cover petrol/hybrids on Spa; interactions cover WLTC and sport.")
        else:
            if experiment == "regenerated":
                baseline_lap = rows[rows.factor == "baseline"].iloc[0]
                st.metric("Regenerated baseline lap time", f"{baseline_lap.lap_time_s:.1f} s")
            research_numbers = research_table(rows)
            st.dataframe(research_numbers, width="stretch", hide_index=True)
            download(research_numbers, f"pwt-study-b-{experiment}-selected.csv", "Download these research rows")
    except FileNotFoundError:
        st.info("This research table is unavailable in the saved study files.")

with report_tab:
    st.subheader("Report, slides and evidence")
    st.markdown("The written report uses the **EU grid** for its main results, with a separate French-grid "
                "comparison. It includes all cars and cycles regardless of the selections above.")
    report_path = DOCS / "study-b-sensitivity.md"
    if report_path.exists():
        with st.expander("Read the full Study B report"):
            render_report(report_path.read_text(encoding="utf-8"))
    files = sorted(path for path in DOCS.glob("study-b-*") if path.suffix in (".md", ".csv", ".pdf", ".pptx"))
    files.append(DOCS / "sources.md")
    artifact = st.selectbox("Download a study artifact", files, format_func=lambda path: path.name,
                            key="study_b_artifact")
    st.download_button("Download selected artifact", artifact.read_bytes(), file_name=artifact.name,
                       key="study_b_download")
    st.caption("Interpretation and slides remain an owner-review draft. Engine checks are not full vehicle-feasibility checks.")
