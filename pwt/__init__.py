"""Core readers for the supplied PWT CO2 workbooks.

Nothing in this package imports Streamlit — it is a plain library so the extractor can be
tested without a browser and reused by the project's Python model later.
"""

from pwt.catalog import CATALOG, CYCLES, POWERTRAINS, CatalogEntry, course_file, find
from pwt.schema import Run
from pwt.workbook import read_all, read_run

__all__ = [
    "CATALOG",
    "CYCLES",
    "POWERTRAINS",
    "CatalogEntry",
    "Run",
    "course_file",
    "find",
    "read_all",
    "read_run",
]
