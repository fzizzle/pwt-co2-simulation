"""Flatten the supplied workbooks into parquet for fast loading.

Run from the repo root:

    python -m pwt.build

Writes `data/processed/runs.parquet` (one row per run, totals and params widened into
columns) and `data/processed/traces.parquet` (every run's steps, long-form). Both are derived
data and gitignored — the dashboard rebuilds them from the workbooks when they are absent, so
a fresh clone and the deployed app both work without this step.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pwt.catalog import CATALOG, ROOT, course_file
from pwt.schema import Run
from pwt.workbook import read_run

PROCESSED = ROOT / "data" / "processed"
RUNS_PARQUET = PROCESSED / "runs.parquet"
TRACES_PARQUET = PROCESSED / "traces.parquet"


def _column_name(kind: str, label: str, unit: str) -> str:
    """A flat column name for a (label, unit) key, e.g. "total:total emission [g co2/km]"."""
    return f"{kind}:{label}" + (f" [{unit}]" if unit else "")


def runs_frame(runs: list[Run]) -> pd.DataFrame:
    """One row per run: identity, canonical figures, then every total and parameter."""
    records = []
    for run in runs:
        record: dict[str, object] = {
            "powertrain": run.powertrain,
            "cycle": run.cycle,
            "style": run.style,
            "source_file": run.source_file,
            "title_cell": run.title_cell,
            "steps": 0 if run.trace is None else len(run.trace),
            "summary_rows_skipped": run.summary_rows_skipped,
            # Canonical figures, absent (None) where a workbook does not report them.
            "consumption_l_per_100km": run.consumption_l_per_100km,
            "co2_g_per_km": run.co2_g_per_km,
            "co2_g_total": run.co2_g_total,
            "energy_wh_per_100km": run.energy_wh_per_100km,
        }
        for (label, unit), value in run.totals.items():
            record[_column_name("total", label, unit)] = value
        for (label, unit), value in run.params.items():
            record[_column_name("param", label, unit)] = value
        records.append(record)
    return pd.DataFrame(records)


def traces_frame(runs: list[Run]) -> pd.DataFrame:
    """Every run's steps stacked, tagged with the run's identity."""
    frames = []
    for run in runs:
        if run.trace is None or run.trace.empty:
            continue
        frame = run.trace.copy()
        frame.insert(0, "step", range(len(frame)))
        frame.insert(0, "source_file", run.source_file)
        frame.insert(0, "cycle", run.cycle)
        frame.insert(0, "powertrain", run.powertrain)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build(out_dir: Path = PROCESSED) -> tuple[Path, Path]:
    runs = [read_run(course_file(e.filename)) for e in CATALOG]
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_path, traces_path = out_dir / RUNS_PARQUET.name, out_dir / TRACES_PARQUET.name
    runs_frame(runs).to_parquet(runs_path, index=False)
    traces_frame(runs).to_parquet(traces_path, index=False)
    return runs_path, traces_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PROCESSED, help="output directory")
    args = parser.parse_args()

    runs_path, traces_path = build(args.out)
    runs, traces = pd.read_parquet(runs_path), pd.read_parquet(traces_path)
    print(f"{runs_path.relative_to(ROOT)}: {len(runs)} runs, {len(runs.columns)} columns")
    print(f"{traces_path.relative_to(ROOT)}: {len(traces)} steps, {len(traces.columns)} columns")
    print()
    cols = ["powertrain", "cycle", "consumption_l_per_100km", "co2_g_per_km",
            "energy_wh_per_100km", "steps"]
    print(runs[cols].to_string(index=False))


if __name__ == "__main__":
    main()
