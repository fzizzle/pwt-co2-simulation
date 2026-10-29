"""Which supplied workbook is which run.

Identity comes from this table, never from a workbook's title cell. Three of the supplied
titles contradict their filename and contents:

  * `13 SPA Franco PETROL car SPORT Driving.xlsx` — title reads "ECO"
  * `15 SPA Franco HYBRID engine SPORT Driving.xlsx` — title reads "ECO DRIVING"
  * `34 NEDC PHYBRID engine.xlsx` — title reads "FRANCORCHAMPS"

Trusting the title would file those runs under the wrong cycle and driving style, so the
catalog is the source of truth and the title is kept only for display.

Eleven of the 23 supplied files carry no run: `02`, `03`, `04`, `31`, `36` are empty cycle
templates, `05` is an engine-efficiency reference, and the PDFs/PPTX/DOCX are documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Repository root, derived from this file's location so it works from any working directory.
ROOT = Path(__file__).resolve().parent.parent
COURSE_FILES = ROOT / "data" / "course-files"

POWERTRAINS = ("petrol", "bev", "hybrid", "phev")
CYCLES = ("franco_eco", "franco_sport", "nedc")

#: Display names, kept here so the UI never hardcodes a label.
POWERTRAIN_NAMES = {
    "petrol": "Petrol",
    "bev": "Battery electric",
    "hybrid": "Full hybrid",
    "phev": "Plug-in hybrid",
}
CYCLE_NAMES = {
    "franco_eco": "Francorchamps — eco",
    "franco_sport": "Francorchamps — sport",
    "nedc": "NEDC",
}


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    filename: str
    powertrain: str
    cycle: str
    style: str  # "eco" | "sport" | "regulatory"


CATALOG: tuple[CatalogEntry, ...] = (
    # Francorchamps — eco driving
    CatalogEntry("07 SPA Franco PETROL car ECO Driving.xlsx", "petrol", "franco_eco", "eco"),
    CatalogEntry("06 SPA Franco ELECTRIC ECO Driving.xlsx", "bev", "franco_eco", "eco"),
    CatalogEntry("10 SPA Franco HYBRID engine ECO Driving.xlsx", "hybrid", "franco_eco", "eco"),
    CatalogEntry("09 SPA Franco PHYBRID engine ECO Driving.xlsx", "phev", "franco_eco", "eco"),
    # Francorchamps — sport driving
    CatalogEntry(
        "13 SPA Franco PETROL car SPORT Driving.xlsx", "petrol", "franco_sport", "sport"
    ),
    CatalogEntry("12 SPA Franco ELECTRIC SPORT Driving.xlsx", "bev", "franco_sport", "sport"),
    CatalogEntry(
        "15 SPA Franco HYBRID engine SPORT Driving.xlsx", "hybrid", "franco_sport", "sport"
    ),
    CatalogEntry(
        "14 SPA Franco PHYBRID engine SPORT Driving.xlsx", "phev", "franco_sport", "sport"
    ),
    # NEDC
    CatalogEntry("33 NEDC PETROL Car.xlsx", "petrol", "nedc", "regulatory"),
    CatalogEntry("32 NEDC ELECTRIC.xlsx", "bev", "nedc", "regulatory"),
    CatalogEntry("35 NEDC HYBRID engine.xlsx", "hybrid", "nedc", "regulatory"),
    CatalogEntry("34 NEDC PHYBRID engine.xlsx", "phev", "nedc", "regulatory"),
)

_BY_FILENAME = {e.filename: e for e in CATALOG}


def course_file(filename: str) -> Path:
    """Absolute path to a supplied course file."""
    return COURSE_FILES / filename


def entry_for(filename: str) -> CatalogEntry | None:
    """The catalog entry for a filename, or None if the file carries no run."""
    return _BY_FILENAME.get(Path(filename).name)


def find(*, powertrain: str, cycle: str) -> CatalogEntry:
    """The single entry for a (powertrain, cycle) pair."""
    for entry in CATALOG:
        if entry.powertrain == powertrain and entry.cycle == cycle:
            return entry
    raise KeyError(f"no catalogued run for powertrain={powertrain!r} cycle={cycle!r}")
