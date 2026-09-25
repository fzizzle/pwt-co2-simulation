"""The data contract shared by every producer and consumer of run data.

A `Run` is one workbook: its parameter block, its total rows, and its per-step trace. Values
are passed through exactly as the workbook reports them — nothing here converts units,
recomputes a figure, or substitutes a value for a missing or implausible one. Zeros and
negatives survive extraction unchanged, because this is a viewer for supplied data.

Keys into `params` and `totals` are `(label, unit)` pairs, both normalised (casefolded,
whitespace collapsed, trailing colon stripped). The unit is part of the key because it is
sometimes the only thing distinguishing two rows: petrol rows 48 and 49 are both labelled
"Total emission:" and differ only in reporting `g CO2` versus `g CO2/km`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

Key = tuple[str, str]

#: Exact normalised labels that belong in `totals`; everything else in the A/B/C block is a
#: parameter. Matching is exact rather than substring so that "battery energy content" (an
#: input) is not mistaken for "energy" (a result).
TOTAL_LABELS: frozenset[str] = frozenset(
    {
        "total consumption",
        "urban consumption",
        "extra urban consumption",
        "total emission",
        "emission",
        "urban emission",
        "extra urban emission",
        "energy",
        "energy to move the car",
        "total fuel energy",
        "total energy use",
        "total energy used",
        "urban energy use",
        "extra urban energy use",
    }
)

# Canonical accessors resolve across the workbooks' inconsistent labelling. First match wins.
_CONSUMPTION: tuple[Key, ...] = (("total consumption", "l/100km"),)
_CO2_PER_KM: tuple[Key, ...] = (
    ("total emission", "g co2/km"),
    ("emission", "g co2/km"),
)
_CO2_TOTAL: tuple[Key, ...] = (
    ("total emission", "g co2"),
    ("emission", "g co2"),
)
_ENERGY_PER_100KM: tuple[Key, ...] = (
    ("total energy used", "wh/100km"),  # Francorchamps EV
    ("total energy use", "wh/100km"),  # NEDC EV — same quantity, different label
)


@dataclass(slots=True)
class Run:
    """One workbook's worth of supplied data."""

    source_file: str
    powertrain: str | None
    cycle: str | None
    style: str | None
    title_cell: str
    params: dict[Key, float] = field(default_factory=dict)
    totals: dict[Key, float] = field(default_factory=dict)
    trace: "pd.DataFrame | None" = None
    #: Trailing rows skipped as summary/unit-annotation rather than steps. Recorded so the
    #: parsing decision is visible rather than hidden.
    summary_rows_skipped: int = 0

    # --- canonical views over `totals` ---------------------------------------------------
    # Each returns None when the workbook simply does not report that figure (a BEV has no
    # fuel consumption row). None means absent; 0.0 means the workbook reported zero.

    def _first(self, keys: tuple[Key, ...]) -> float | None:
        for key in keys:
            if key in self.totals:
                return self.totals[key]
        return None

    @property
    def consumption_l_per_100km(self) -> float | None:
        return self._first(_CONSUMPTION)

    @property
    def co2_g_per_km(self) -> float | None:
        return self._first(_CO2_PER_KM)

    @property
    def co2_g_total(self) -> float | None:
        return self._first(_CO2_TOTAL)

    @property
    def energy_wh_per_100km(self) -> float | None:
        return self._first(_ENERGY_PER_100KM)

    @property
    def label(self) -> str:
        """Short human label, e.g. "petrol · franco_eco"."""
        return f"{self.powertrain or '?'} · {self.cycle or '?'}"
