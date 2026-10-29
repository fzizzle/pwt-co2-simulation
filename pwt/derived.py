"""Workbooks the group builds from the supplied ones.

The supplied files stop at NEDC and Francorchamps, and the NEDC plug-in hybrid only covers a
charge-depleting run. Everything here is made by taking one supplied NEDC workbook as a
template, keeping its parameter block and its per-step formulas, and changing only what the
derived run needs: the speed trace, the starting state of charge, the shift speeds. Formulas
are copied from the template row by row, so a derived workbook computes exactly what Nelis's
sheet would, and LibreOffice recalculates it so the cached values are there for `read_run`.

The check that this is faithful: rebuilding each NEDC template on its own trace reproduces its
supplied totals (`tests/test_derived.py`).

Nothing here writes to `data/course-files/`. Output goes to `data/derived/`.

    python -m pwt.derived      # rebuild every derived workbook (needs LibreOffice)
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.formula.translate import Translator
from openpyxl.utils import column_index_from_string, get_column_letter

from pwt.catalog import ROOT, course_file
from pwt.schema import Run
from pwt.workbook import read_run

DERIVED_DIR = ROOT / "data" / "derived"
WLTC_FILE = "36 WLTP empty.xlsx"

#: The template's step rows. Every NEDC template holds its trace in rows 3-107, with row 3 the
#: initial state and anything below 107 (the hybrid's end-of-cycle recharge line, the sums)
#: written relative to that last row.
_FIRST_ROW, _TEMPLATE_LAST_ROW = 3, 107
#: Row 5 is a plain step row in every template; its formulas are the pattern filled down.
_PROTOTYPE_ROW = 5
#: NEDC's urban part is rows 3-86 and extra-urban 87-107; block formulas that split on these
#: rows only make sense on the template's own trace.
_NEDC_SPLIT_ROWS = {86, 87}

#: Shift speeds the assignment sheet calibrates ("approximately 36, 57, 82, 108 kph"), as the
#: Francorchamps and NEDC hybrid files implement them. NEDC petrol uses NEDC's prescribed
#: 18/38/50/70 instead, which does not carry over to another cycle.
SHIFT_KPH = (35, 57, 82, 115)

_REF = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")


@dataclass(frozen=True, slots=True)
class DerivedSpec:
    filename: str
    template: str
    powertrain: str
    cycle: str
    style: str
    title: str
    #: "wltc3" replaces the template's trace; None keeps it.
    trace: str | None = None
    #: Starting state of charge, for the hybrids. None keeps the template's.
    initial_soc: float | None = None
    shift_kph: tuple[int, ...] | None = None
    #: "cd" (charge-depleting) or "cs" (charge-sustaining), for plug-in hybrids.
    mode: str | None = None


SPECS: tuple[DerivedSpec, ...] = (
    DerivedSpec(
        "WLTC3 PETROL.xlsx", "33 NEDC PETROL Car.xlsx", "petrol", "wltc", "regulatory",
        "WLTC CLASS 3 — GASOLINE", trace="wltc3", shift_kph=SHIFT_KPH,
    ),
    DerivedSpec(
        "WLTC3 ELECTRIC.xlsx", "32 NEDC ELECTRIC.xlsx", "bev", "wltc", "regulatory",
        "WLTC CLASS 3 — ELECTRIC", trace="wltc3",
    ),
    DerivedSpec(
        "WLTC3 HYBRID.xlsx", "35 NEDC HYBRID engine.xlsx", "hybrid", "wltc", "regulatory",
        "WLTC CLASS 3 — HYBRID NON PLUG IN", trace="wltc3",
    ),
    DerivedSpec(
        "WLTC3 PHYBRID CD.xlsx", "34 NEDC PHYBRID engine.xlsx", "phev", "wltc", "regulatory",
        "WLTC CLASS 3 — HYBRID PLUG IN, CHARGE-DEPLETING", trace="wltc3", mode="cd",
    ),
    DerivedSpec(
        "WLTC3 PHYBRID CS.xlsx", "34 NEDC PHYBRID engine.xlsx", "phev", "wltc", "regulatory",
        "WLTC CLASS 3 — HYBRID PLUG IN, CHARGE-SUSTAINING", trace="wltc3", initial_soc=0.23,
        mode="cs",
    ),
    DerivedSpec(
        "NEDC PHYBRID CD.xlsx", "34 NEDC PHYBRID engine.xlsx", "phev", "nedc", "regulatory",
        "NEDC — HYBRID PLUG IN, CHARGE-DEPLETING", mode="cd",
    ),
    DerivedSpec(
        "NEDC PHYBRID CS.xlsx", "34 NEDC PHYBRID engine.xlsx", "phev", "nedc", "regulatory",
        "NEDC — HYBRID PLUG IN, CHARGE-SUSTAINING", initial_soc=0.23, mode="cs",
    ),
)

#: The 23 % threshold in 34's FACT column, below which the engine takes over. A run started
#: there holds the battery around it: the charge-sustaining case.
PHEV_ENGINE_SOC = 0.23

#: Grid factors from the assignment sheet (EEA), g CO2 per kWh drawn from the battery. No
#: charger loss is added, so these understate the grid side slightly.
GRID_G_PER_KWH = {"EU": 250.0, "FR": 73.0}


# --- the WLTC trace -----------------------------------------------------------------------


def wltc_class3() -> pd.DataFrame:
    """WLTC Class 3 (version 5) from the supplied file: time, speed and phase, 1801 rows."""
    workbook = openpyxl.load_workbook(course_file(WLTC_FILE), read_only=True, data_only=True)
    try:
        ws = workbook["WLTC_class_3"]
        rows = [
            {"phase": phase, "time_s": time, "speed_kph": speed}
            for phase, time, _, speed in ws.iter_rows(
                min_row=8, min_col=2, max_col=5, values_only=True
            )
            if phase is not None
        ]
    finally:
        workbook.close()
    trace = pd.DataFrame(rows)
    # The file names the second phase "Middle"; the regulation calls it Medium.
    trace["phase"] = trace["phase"].replace({"Middle": "Medium"})
    return trace


def wltc_phase_distances_m() -> dict[str, float]:
    """The file's own phase distances (m), as a reference for the built workbooks."""
    workbook = openpyxl.load_workbook(course_file(WLTC_FILE), read_only=True, data_only=True)
    try:
        ws = workbook["WLTC_class_3"]
        names = ("Low", "Medium", "High", "Extra-high")
        return {
            name: float(ws.cell(8 + i, 11).value) for i, name in enumerate(names)
        }
    finally:
        workbook.close()


# --- building -----------------------------------------------------------------------------


def _remap_rows(formula: str, mapping) -> str:
    """Rewrite references to trace columns (E onward) through `mapping(row) -> row`.

    References to the parameter block (columns A-D) are left alone.
    """

    def sub(m: re.Match) -> str:
        col_abs, col, row_abs, row = m.groups()
        if column_index_from_string(col) < 5:
            return m.group(0)
        return f"{col_abs}{col}{row_abs}{mapping(int(row))}"

    return _REF.sub(sub, formula)


def _trace_rows(formula: str) -> set[int]:
    return {
        int(row)
        for _, col, _, row in _REF.findall(formula)
        if column_index_from_string(col) >= 5
    }


def _is_formula(value: object) -> bool:
    return isinstance(value, str) and value.startswith("=")


def _gear_formula(speed_cell: str, shifts: tuple[int, ...]) -> str:
    """The workbooks' nested-IF gear choice, for arbitrary shift speeds."""
    inner = str(len(shifts) + 1)  # n shift speeds, n + 1 gears
    for gear in range(len(shifts) - 1, 0, -1):
        inner = f"IF({speed_cell}<={shifts[gear]},{gear + 1},{inner})"
    return f"=IF({speed_cell}=0,0,IF({speed_cell}<={shifts[0]},1,{inner}))"


def _headers(ws) -> dict[str, int]:
    return {
        str(ws.cell(2, c).value).strip(): c
        for c in range(5, ws.max_column + 1)
        if ws.cell(2, c).value is not None
    }


def _phase_rows(trace: pd.DataFrame) -> dict[str, tuple[int, int]]:
    """Sheet rows spanned by each phase. Row 3 is t=0, which belongs to no step's energy."""
    spans: dict[str, tuple[int, int]] = {}
    for i, phase in enumerate(trace["phase"]):
        row = _FIRST_ROW + i
        first, _ = spans.get(phase, (row, row))
        spans[phase] = (first, row)
    return spans


def build_workbook(spec: DerivedSpec, out_path: Path) -> None:
    """Write `spec`'s workbook, formulas only. `recalculate` fills in the values."""
    workbook = openpyxl.load_workbook(course_file(spec.template))
    ws = workbook[workbook.sheetnames[0]]
    headers = _headers(ws)
    width = ws.max_column

    template_rows = {
        r: [ws.cell(r, c).value for c in range(5, width + 1)]
        for r in range(_FIRST_ROW, ws.max_row + 1)
    }
    prototype = template_rows[_PROTOTYPE_ROW]
    # Block rows (A-D) are read before the sheet is cleared.
    block = {
        r: [ws.cell(r, c).value for c in range(1, 5)] for r in range(_FIRST_ROW, ws.max_row + 1)
    }

    if spec.trace == "wltc3":
        trace = wltc_class3()
        steps = list(zip(trace["time_s"], trace["speed_kph"]))
    else:
        trace = None
        steps = None  # keep the template's own inputs
    n_steps = len(steps) if steps else _TEMPLATE_LAST_ROW - _FIRST_ROW + 1
    last = _FIRST_ROW + n_steps - 1
    shift = last - _TEMPLATE_LAST_ROW

    def tail_map(row: int) -> int:
        return row + shift if row >= _TEMPLATE_LAST_ROW else row

    # Clear the trace area and the block.
    for r in range(_FIRST_ROW, ws.max_row + 1):
        for c in range(1, width + 1):
            ws.cell(r, c).value = None

    input_cols = {
        headers["Time (s)"]: "time",
        headers["Vehicle speed (kph)"]: "speed",
        headers["Altitude (m)"]: "zero",
        headers["Slope (rad)"]: "zero",
    }
    gear_col = headers.get("Gear")
    soc_col = headers.get("BATT SOC state of charge")

    for i in range(n_steps):
        row = _FIRST_ROW + i
        for offset, proto in enumerate(prototype):
            col = 5 + offset
            letter = get_column_letter(col)
            original = template_rows[row][offset] if steps is None else None
            if col in input_cols:
                if steps is None:
                    value = original
                else:
                    kind = input_cols[col]
                    value = 0 if kind == "zero" else steps[i][0 if kind == "time" else 1]
            elif row == _FIRST_ROW:
                # The initial state: keep the template's own-row formulas, zero the rest (some
                # templates point row 3 at a mid-cycle row of the Francorchamps file).
                initial = template_rows[_FIRST_ROW][offset]
                if _is_formula(initial) and _trace_rows(initial) - {_FIRST_ROW}:
                    value = 0
                else:
                    value = initial
            elif steps is None and _is_formula(proto) and not _is_formula(original):
                # The template hard-codes a few cells over their formula (zeros where the
                # formula gives zero anyway, and one dead torque cell); keep them as supplied.
                value = original
            elif _is_formula(proto):
                value = Translator(proto, origin=f"{letter}{_PROTOTYPE_ROW}").translate_formula(
                    f"{letter}{row}"
                )
            else:
                value = proto
            if col == gear_col and spec.shift_kph and row > _FIRST_ROW:
                speed_letter = get_column_letter(headers["Vehicle speed (kph)"])
                value = _gear_formula(f"{speed_letter}{row}", spec.shift_kph)
            if col == soc_col and row == _FIRST_ROW and spec.initial_soc is not None:
                value = spec.initial_soc
            ws.cell(row, col).value = value

    # Rows after the trace (the hybrid's recharge line, the sums), moved to follow the new end.
    for r, values in template_rows.items():
        if r <= _TEMPLATE_LAST_ROW:
            continue
        for offset, value in enumerate(values):
            if _is_formula(value):
                value = _remap_rows(value, tail_map)
            ws.cell(r + shift, 5 + offset).value = value

    # The parameter block: keep it, re-point totals at the new rows, and drop the urban /
    # extra-urban split when the trace is no longer NEDC's.
    out_row = _FIRST_ROW
    for r, values in block.items():
        label, unit, value, alt = values
        if _is_formula(value):
            rows = _trace_rows(value)
            if spec.trace and rows & _NEDC_SPLIT_ROWS:
                continue
            value = _remap_rows(value, tail_map)
        for c, v in zip(range(1, 5), (label, unit, value, alt)):
            ws.cell(r, c).value = v
        out_row = max(out_row, r)

    ws.cell(1, 1).value = f"{spec.title} (built from {spec.template})"
    _append_totals(ws, spec, headers, last, out_row + 2, trace)
    workbook.save(out_path)


def _append_totals(ws, spec, headers, last, row, trace) -> None:
    """Phase totals and the battery side, which the templates do not report."""

    def col(name: str) -> str | None:
        c = headers.get(name)
        return get_column_letter(c) if c else None

    dist = col("Δ Distance (m)") or col("Distance (m)")  # NEDC petrol's "Distance" is per step
    fuel = col("Qfuel (l)")
    co2 = col("Emission (g CO2)")
    energy = col("Engergy (Wh)") or col("Energy (Wh)")
    soc = col("BATT SOC state of charge")
    lines: list[tuple[str, str, str]] = []

    km = lambda a, b: f"(SUM({dist}{a}:{dist}{b})/1000)"  # noqa: E731

    if trace is not None:
        for phase, (a, b) in _phase_rows(trace).items():
            name = phase.lower()
            lines.append((f"{phase} distance", "m", f"=SUM({dist}{a}:{dist}{b})"))
            if fuel:
                lines.append((f"{name} consumption", "l/100km",
                              f"=100*SUM({fuel}{a}:{fuel}{b})/{km(a, b)}"))
            if spec.powertrain == "bev":
                lines.append((f"{name} energy use", "Wh/100km",
                              f"=100*SUM({energy}{a}:{energy}{b})/{km(a, b)}"))
            lines.append((f"{name} emission", "g CO2/km",
                          f"=SUM({co2}{a}:{co2}{b})/{km(a, b)}"))

    if soc:
        start, end = f"{soc}{_FIRST_ROW}", f"{soc}{last}"
        lines += [
            ("Final state of charge", "", f"={end}"),
            ("Battery energy used", "Wh", f"=($C$45*({start}-{end}))"),
            ("Battery energy used", "Wh/100km",
             f"=100*$C$45*({start}-{end})/{km(_FIRST_ROW, last)}"),
        ]
        if spec.powertrain == "phev":
            for region, factor in GRID_G_PER_KWH.items():
                lines.append((
                    f"Grid emission {region}", "g CO2/km",
                    f"={factor / 1000}*$C$45*({start}-{end})/{km(_FIRST_ROW, last)}",
                ))

    ws.cell(row, 1).value = "Added by pwt.derived"
    for i, (label, unit, formula) in enumerate(lines, start=row + 1):
        ws.cell(i, 1).value = label
        ws.cell(i, 2).value = unit
        ws.cell(i, 3).value = formula


def recalculate(sources: list[Path], out_dir: Path) -> None:
    """Have LibreOffice compute every formula and write the values back."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise RuntimeError("LibreOffice (soffice) is needed to recalculate the workbooks")
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                soffice, f"-env:UserInstallation=file://{profile}", "--headless", "--calc",
                "--convert-to", "xlsx", "--outdir", str(out_dir), *map(str, sources),
            ],
            check=True,
            capture_output=True,
        )


def build(specs: tuple[DerivedSpec, ...] = SPECS, out_dir: Path = DERIVED_DIR) -> list[Path]:
    with tempfile.TemporaryDirectory() as tmp:
        staged = []
        for spec in specs:
            path = Path(tmp) / spec.filename
            build_workbook(spec, path)
            staged.append(path)
        recalculate(staged, out_dir)
    return [out_dir / spec.filename for spec in specs]


def read_derived(spec: DerivedSpec, directory: Path = DERIVED_DIR) -> Run:
    """A derived workbook as a `Run`, with identity from its spec."""
    run = read_run(directory / spec.filename)
    run.powertrain, run.cycle, run.style = spec.powertrain, spec.cycle, spec.style
    return run


# --- variants: one supplied workbook, some parameter cells changed ------------------------


@dataclass(slots=True)
class Variant:
    template: str
    edits: dict[str, object] = field(default_factory=dict)


def run_variants(variants: dict[str, Variant]) -> dict[str, Run]:
    """Recalculate supplied workbooks with some cells changed, and read them back.

    The way to measure what a parameter is worth inside Nelis's own sheet, before the Python
    model exists.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        staged = []
        for name, variant in variants.items():
            workbook = openpyxl.load_workbook(course_file(variant.template))
            ws = workbook[workbook.sheetnames[0]]
            for cell, value in variant.edits.items():
                ws[cell].value = value
            path = tmp / f"{name}.xlsx"
            workbook.save(path)
            staged.append(path)
        recalculate(staged, tmp / "out")
        return {name: read_run(tmp / "out" / f"{name}.xlsx") for name in variants}


def main() -> None:
    for path in build():
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
