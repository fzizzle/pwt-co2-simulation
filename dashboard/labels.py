"""Display names, units and number formats: one lookup for every page.

The data keeps its stable snake_case names (`speed_kph`, `title_cell`); the reader sees the names
below. Values are never converted here. A workbook page shows Wh/100 km where the workbook
does; only the text changes, so `speed_kph` is labelled "km/h".
"""

from __future__ import annotations

import math

import pandas as pd

#: Per-step columns: name and unit as the reader sees them. Names follow the workbooks' own
#: headers, so the table matches the spreadsheet a reader may have open beside it.
COLUMNS: dict[str, tuple[str, str]] = {
    "step": ("Step", ""),
    "delta_time_s": ("Time step", "s"),
    "delta_distance_m": ("Distance step", "m"),
    "time_s": ("Time", "s"),
    "distance_m": ("Distance", "m"),
    "altitude_m": ("Altitude", "m"),
    "speed_kph": ("Speed", "km/h"),
    "speed_ms": ("Speed", "m/s"),
    "mean_speed_ms": ("Mean speed over the step", "m/s"),
    "gear": ("Gear", ""),
    "phase": ("Phase", ""),
    "acceleration_ms2": ("Acceleration", "m/s²"),
    "wheel_speed_rads": ("Wheel speed", "rad/s"),
    "engine_speed_rads": ("Engine speed", "rad/s"),
    "engine_speed_rpm": ("Engine speed", "rpm"),
    "slope_rad": ("Slope", "rad"),
    "resistive_force_n": ("Resistive force", "N"),
    "acceleration_force_n": ("Acceleration force", "N"),
    "total_force_n": ("Total force", "N"),
    "engine_power_w": ("Engine power", "W"),
    "engine_power_drivetrain_w": ("Engine power with drivetrain losses", "W"),
    "wheel_power_w": ("Wheel power", "W"),
    "engine_torque_nm": ("Engine torque", "N·m"),
    "engine_torque_drivetrain_nm": ("Engine torque with drivetrain losses", "N·m"),
    "total_engine_power_w": ("Total engine power", "W"),
    "total_engine_torque_nm": ("Total engine torque", "N·m"),
    "battery_engine_power_w": ("Battery engine power", "W"),
    "battery_engine_torque_nm": ("Battery engine torque", "N·m"),
    "engine_efficiency": ("Engine efficiency", ""),
    "efficiency_pct": ("Motor efficiency", "%"),
    "qfuel_g": ("Fuel", "g"),
    "qfuel_l": ("Fuel", "l"),
    "emission_g_co2": ("CO₂ emitted", "g"),
    "co2_g": ("CO₂ from the grid", "g"),
    "energy_wh": ("Energy", "Wh"),
    "energy_to_move_car_wh": ("Energy to move the car", "Wh"),
    "batt_soc": ("Battery charge", "fraction"),
    "battv": ("Energy demand this step", "Wh"),
    "fact": ("Engine's share of demand", ""),
    "shortfall_w": ("Short of the engine's full-load curve", "W"),
    # identity columns on the Data page
    "powertrain": ("Powertrain", ""),
    "cycle": ("Cycle", ""),
    "style": ("Driving style", ""),
    "source_file": ("Workbook", ""),
    "title_cell": ("Title on the sheet", ""),
    "steps": ("Steps", ""),
    "summary_rows_skipped": ("Summary rows left out", ""),
    "quantity": ("Figure", ""),
    "parameter": ("Parameter", ""),
    "unit": ("Unit", ""),
    "value": ("Value", ""),
    "row": ("Sheet row", ""),
    "label": ("Label on the sheet", ""),
    "kind": ("Read as", ""),
    "key_label": ("Matched label", ""),
    "key_unit": ("Matched unit", ""),
}

#: The workbooks' own unit spellings, as the reader sees them.
_UNITS = {
    "l/100km": "l/100 km", "wh/100km": "Wh/100 km", "wh": "Wh", "kwh": "kWh", "w": "W",
    "g co2/km": "g CO₂/km", "g co2": "g CO₂", "kg": "kg", "m": "m", "m^2": "m²",
    "kg/m^3": "kg/m³", "m/s^2": "m/s²", "rad/s": "rad/s", "%": "%",
}

#: Parameter rows whose sheet label is a bare symbol.
_PARAMETERS = {
    "a1": "Engine efficiency curve, A1",
    "a2": "Engine efficiency curve, A2",
    "a3": "Engine efficiency curve, A3",
    "a": "Motor efficiency curve, a",
    "b": "Motor efficiency curve, b",
    "c": "Motor efficiency curve, c",
    "cx": "Drag coefficient Cx",
    "scx [m^2]": "Drag area S·Cx [m^2]",
    "maximum power in watts": "Maximum engine power [w]",
    "batt energy content [wh]": "Battery energy content [wh]",
    "p electric motor [w]": "Electric motor power [w]",
}


def unit(text: str) -> str:
    return _UNITS.get(text.strip().casefold(), text)


def column(code: str, *, with_unit: bool = True) -> str:
    """'speed_kph' → 'Speed (km/h)'. A column not listed keeps its code, so nothing hides."""
    if code.startswith("param:"):
        return parameter(code.removeprefix("param:"))
    if code.startswith("total:"):
        return sheet_label(code.removeprefix("total:"))
    name, u = COLUMNS.get(code, (code, ""))
    return f"{name} ({u})" if with_unit and u else name


def sheet_label(text: str) -> str:
    """A normalised sheet label, 'total consumption [l/100km]' → 'Total consumption (l/100 km)'."""
    if "[" in text and text.endswith("]"):
        name, u = text[:-1].split("[", 1)
        return f"{_capital(name.strip())} ({unit(u)})"
    return _capital(text)


def parameter(text: str) -> str:
    return sheet_label(_PARAMETERS.get(text, text))


def _capital(text: str) -> str:
    return text[:1].upper() + text[1:]


def number(value: object) -> str:
    """A reported figure at sensible precision: 245.7, 1,720, 10.27, 0.635. Missing → '—'.

    Four significant figures up to 1,000, whole numbers above; never scientific notation for
    anything a reader would see in a workbook, so 85,000 W stays 85,000 W.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA:
        return "—"
    if not isinstance(value, (int, float)):
        return str(value)
    v = float(value)
    if v == 0:
        return "0"
    size = abs(v)
    if size >= 1000 or v == round(v):
        return f"{v:,.0f}"
    if size >= 1e-3:
        decimals = max(1, 3 - math.floor(math.log10(size)))
        return f"{v:,.{decimals}f}".rstrip("0").rstrip(".")
    mantissa, exponent = f"{v:.2e}".split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa} × 10{_superscript(int(exponent))}"


def figure(value: object) -> str:
    """A reported result: one decimal at most above 10, so 245.730 reads 245.7."""
    if isinstance(value, (int, float)) and not (isinstance(value, float) and math.isnan(value)):
        v = float(value)
        if v != 0 and abs(v) >= 10:
            return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.1f}"
        if v != 0 and abs(v) >= 1:
            return f"{v:,.2f}"
    return number(value)


def _superscript(n: int) -> str:
    return str(n).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))


def readable(frame: pd.DataFrame, fmt=number) -> "pd.io.formats.style.Styler | pd.DataFrame":
    """A table for st.dataframe: plain column names, sensible digits, '—' for every blank.

    Numbers stay numbers underneath, so sorting still works. Large frames skip the styling,
    which Streamlit refuses past about 260,000 cells, and only get their names changed.
    """
    shown = frame.rename(columns=lambda c: column(c) if isinstance(c, str) else c)
    if shown.size > 200_000:
        return shown
    numeric = list(shown.select_dtypes("number").columns)
    others = [c for c in shown.columns if c not in numeric]
    return shown.style.format(fmt, subset=numeric, na_rep="—").format(na_rep="—", subset=others)
