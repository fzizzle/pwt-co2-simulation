"""Label-driven reader for the supplied CO2 workbooks.

Every workbook shares a shape but not a layout: columns A/B/C hold a sparse block of
labelled values, and columns E onward hold the per-step trace under headers in row 2. The
same quantity sits at a different row in nearly every file — total consumption is C47 in
petrol-Francorchamps, C48 in the hybrid, C45 in NEDC-petrol — so nothing here addresses a
cell by row number. Labels are matched instead, after normalisation.

Two layout quirks the reader has to absorb:

  * Column B is a unit *or* an alternative value. Files 10, 15 and 35 lay out a horizontal
    menu of engine efficiency curves across B/C/D, with row 30 naming them
    ("downsized" / "atkinson" / "old"), so B can hold a coefficient rather than "kg".
    Column C is the active value in every file. B counts as a unit only when it is a
    non-numeric string.
  * Trace headers vary. Only 12 of the 37 distinct headers appear in all 12 workbooks:
    `Time (s)` is absent from the Francorchamps EV files, `Distance (m)` from NEDC EV,
    `Gear` from all three EVs, and `Energy (Wh)` is spelled `Engergy (Wh)` in six files.
    The trace is therefore whatever columns that workbook actually has.
"""

from __future__ import annotations

import re
from pathlib import Path

import openpyxl
import pandas as pd

from pwt.catalog import entry_for
from pwt.schema import TOTAL_LABELS, Key, Run

#: Trace headers renamed to stable snake_case names. Anything not listed falls back to a
#: generic slug, so an unlisted column still appears rather than being silently dropped.
TRACE_ALIASES: dict[str, str] = {
    "Δ Time (s)": "delta_time_s",
    "Δ Distance (m)": "delta_distance_m",
    "Time (s)": "time_s",
    "Distance (m)": "distance_m",
    "Altitude (m)": "altitude_m",
    "Vehicle speed (kph)": "speed_kph",
    "Vehicle speed (m/s)": "speed_ms",
    "Gear": "gear",
    "Acceleration (m/s^2)": "acceleration_ms2",
    "Wheel angular speed (rad/s)": "wheel_speed_rads",
    "Engine angular speed (rad/s)": "engine_speed_rads",
    "Engine angular speed (rpm)": "engine_speed_rpm",
    "Slope (rad)": "slope_rad",
    "Resistive force (N)": "resistive_force_n",
    "Acceleration force (N)": "acceleration_force_n",
    "Total force (N)": "total_force_n",
    "Engine power (W)": "engine_power_w",
    "Engine power with drivetrain losses (W)": "engine_power_drivetrain_w",
    "Wheel power (W)": "wheel_power_w",
    "Engine torque (Nm)": "engine_torque_nm",
    "Engine torque with drivetrain losses (Nm)": "engine_torque_drivetrain_nm",
    "Total engine power (W)": "total_engine_power_w",
    "Total engine torque (Nm)": "total_engine_torque_nm",
    "Battery engine power (W)": "battery_engine_power_w",
    "Battery engine torque (Nm)": "battery_engine_torque_nm",
    "Engine efficiency": "engine_efficiency",
    "Efficiency (%)": "efficiency_pct",
    "Qfuel (g)": "qfuel_g",
    "Qfuel (l)": "qfuel_l",
    "Emission (g CO2)": "emission_g_co2",
    "CO2 (g)": "co2_g",
    "Energy (Wh)": "energy_wh",
    "Engergy (Wh)": "energy_wh",  # misspelled in six of the twelve workbooks
    "Energy to move the car (vehicle side)": "energy_to_move_car_wh",
    "BATT SOC state of charge": "batt_soc",
    "BATTV": "battv",
    "FACT": "fact",
}

#: Columns A/B/C are the labelled block; the trace starts at E. D is a spare alternatives
#: column in some files and is not part of either block.
_LABEL_COL, _UNIT_COL, _VALUE_COL = 1, 2, 3
_TRACE_FIRST_COL = 5
_HEADER_ROW = 2
_FIRST_DATA_ROW = 3

#: A trace row counts as a step when at least this fraction of its columns hold numbers.
#: Measured across all 12 supplied and 7 derived workbooks, real steps fill 96-100% of their
#: columns while the trailing summary and unit-annotation rows fill 22-50% (the 50% is the
#: electric NEDC sums row), so 0.75 sits clear of both.
_STEP_FILL_THRESHOLD = 0.75


def normalise(value: object) -> str:
    """Casefold, collapse whitespace, strip a trailing colon."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().rstrip(":").strip().casefold()


def _slug(header: str) -> str:
    """Generic fallback name for a header with no explicit alias."""
    s = re.sub(r"\s+", "_", str(header).strip().casefold())
    return re.sub(r"__+", "_", re.sub(r"[^a-z0-9_]", "", s)).strip("_") or "unnamed"


def _unit_of(cell: object) -> str:
    """Column B read as a unit.

    Returns "" when B holds a number, because in the hybrid workbooks that column carries an
    alternative coefficient rather than a unit. Keeping it out of the key means "a1" resolves
    to the same key in every file instead of ("a1", "-0.3867") in some.
    """
    if cell is None or isinstance(cell, (int, float)):
        return ""
    return normalise(cell)


def _read_labelled_block(ws) -> tuple[dict[Key, float], dict[Key, float]]:
    """Split the A/B/C block into (params, totals) by exact normalised label."""
    params: dict[Key, float] = {}
    totals: dict[Key, float] = {}
    for row in ws.iter_rows(
        min_row=_FIRST_DATA_ROW, min_col=_LABEL_COL, max_col=_VALUE_COL, values_only=True
    ):
        label_cell, unit_cell, value_cell = (row + (None, None, None))[:3]
        if label_cell is None or not isinstance(value_cell, (int, float)):
            continue
        label = normalise(label_cell)
        if not label:
            continue
        key: Key = (label, _unit_of(unit_cell))
        target = totals if label in TOTAL_LABELS else params
        # First occurrence wins; the workbooks never repeat a (label, unit) pair meaningfully.
        target.setdefault(key, float(value_cell))
    return params, totals


def _read_trace(ws) -> tuple[pd.DataFrame, int]:
    """The per-step block from column E, named by its row-2 headers.

    Returns the step rows and the number of trailing non-step rows skipped.
    """
    header_row = next(
        ws.iter_rows(
            min_row=_HEADER_ROW, max_row=_HEADER_ROW, min_col=_TRACE_FIRST_COL, values_only=True
        ),
        (),
    )

    names: list[str] = []
    keep: list[int] = []
    used: set[str] = set()
    for offset, header in enumerate(header_row):
        if header is None or not str(header).strip():
            continue
        name = TRACE_ALIASES.get(str(header).strip()) or _slug(header)
        if name in used:  # e.g. both spellings of Energy (Wh) in one file
            suffix = 2
            while f"{name}_{suffix}" in used:
                suffix += 1
            name = f"{name}_{suffix}"
        used.add(name)
        names.append(name)
        keep.append(offset)

    if not names:
        return pd.DataFrame(), 0

    def is_blank(value: object) -> bool:
        # Cells below the trace hold cached empty strings from formulas, not None, so an
        # `is None` check alone would keep dozens of empty rows.
        return value is None or (isinstance(value, str) and not value.strip())

    def is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    records: list[list[object]] = []
    dropped = 0
    width = max(keep) + 1
    for row in ws.iter_rows(
        min_row=_FIRST_DATA_ROW, min_col=_TRACE_FIRST_COL, values_only=True
    ):
        padded = row + (None,) * (width - len(row)) if len(row) < width else row
        values = [padded[i] for i in keep]
        filled = sum(is_number(v) for v in values)
        if not filled:
            continue  # blank tail, or a row of unit annotations like "wh" / "g" / "l"
        if filled < _STEP_FILL_THRESHOLD * len(values):
            # A trailing summary row: it repeats the run's cumulative totals under the Δ
            # headers rather than describing a step. The same figures are in `totals`, so
            # keeping it here would put a spurious point at the end of every plot.
            dropped += 1
            continue
        records.append([None if is_blank(v) else v for v in values])

    df = pd.DataFrame(records, columns=names)
    # Numeric where possible; a column that is genuinely text stays as-is.
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().any():
            df[col] = converted
    if "gear" in df.columns:
        df["gear"] = df["gear"].astype("Int64")
    return df.reset_index(drop=True), dropped


def read_run(path: str | Path) -> Run:
    """Read one workbook into a `Run`.

    Identity (powertrain, cycle, style) comes from the catalog, not the workbook title, which
    is wrong in three of the supplied files.
    """
    path = Path(path)
    workbook = openpyxl.load_workbook(path, data_only=True)
    try:
        ws = workbook[workbook.sheetnames[0]]
        params, totals = _read_labelled_block(ws)
        trace, dropped = _read_trace(ws)
        title = ws.cell(1, 1).value
    finally:
        workbook.close()

    entry = entry_for(path.name)
    return Run(
        source_file=path.name,
        powertrain=entry.powertrain if entry else None,
        cycle=entry.cycle if entry else None,
        style=entry.style if entry else None,
        title_cell=str(title) if title is not None else "",
        params=params,
        totals=totals,
        trace=trace,
        summary_rows_skipped=dropped,
    )


def read_block(path: str | Path) -> pd.DataFrame:
    """The A/B/C labelled block exactly as the sheet holds it.

    This is the rawest view the tool offers: original label and unit text, the cell's row
    number, and the value — plus how `read_run` classified the row and the normalised key it
    was filed under. Nothing is renamed or dropped, so a row the reader skipped (a label with
    no numeric value) still appears, with `value` empty.
    """
    path = Path(path)
    workbook = openpyxl.load_workbook(path, data_only=True)
    try:
        ws = workbook[workbook.sheetnames[0]]
        records = []
        for row_number, row in enumerate(
            ws.iter_rows(
                min_row=_FIRST_DATA_ROW, min_col=_LABEL_COL, max_col=_VALUE_COL,
                values_only=True,
            ),
            start=_FIRST_DATA_ROW,
        ):
            label_cell, unit_cell, value_cell = (row + (None, None, None))[:3]
            if label_cell is None or not str(label_cell).strip():
                continue
            label = normalise(label_cell)
            numeric = isinstance(value_cell, (int, float)) and not isinstance(value_cell, bool)
            records.append(
                {
                    "row": row_number,
                    "label": str(label_cell),
                    "unit": "" if unit_cell is None else str(unit_cell),
                    "value": float(value_cell) if numeric else None,
                    "kind": ("total" if label in TOTAL_LABELS else "parameter")
                    if numeric
                    else "skipped (no numeric value)",
                    "key_label": label,
                    "key_unit": _unit_of(unit_cell),
                }
            )
    finally:
        workbook.close()
    return pd.DataFrame(records)


def read_all() -> list[Run]:
    """Every catalogued run, in catalog order."""
    from pwt.catalog import CATALOG, course_file

    return [read_run(course_file(e.filename)) for e in CATALOG]
