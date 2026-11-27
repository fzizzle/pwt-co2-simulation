"""Slide order, author-editable fields and positions along the Spa lap."""

from dataclasses import dataclass

from pwt.deck.track import CORNERS

SECTIONS: dict[str, tuple[str, str, float]] = {
    "sim": ("la_source", "01", 3.2),
    "cmp": ("eau_rouge", "02", 2.8),
    "A": ("les_combes", "03 · Study A", 3.0),
    "B": ("pouhon", "04 · Study B", 2.6),
    "C": ("stavelot", "05 · Study C", 3.0),
    "lim": ("bus_stop", "06", 3.4),
}


#: Study A's dataflow chart: (field, kind, column, row). Kinds: "data" (input or output,
#: a parallelogram), "process" (a box), "file" (a saved CSV, a cylinder), "result" (output
#: shown on a later slide). Columns 0–4 run left to right, rows 0–2 top to bottom.
DATAFLOW_NODES: tuple[tuple[str, str, int, int], ...] = (
    ("cars", "data", 0, 0), ("fix", "process", 1, 0), ("grid", "process", 2, 0),
    ("sim", "process", 3, 0), ("runs", "file", 4, 0),
    ("cycles", "data", 3, 1), ("filter", "process", 4, 1),
    ("argmin", "process", 4, 2), ("sizes", "result", 3, 2),
    ("sweep", "process", 0, 2), ("storage", "file", 1, 2), ("gap", "result", 2, 2),
)
#: Arrows (from, to), each labelled by its own field `edge.<from>.<to>`.
DATAFLOW_EDGES: tuple[tuple[str, str], ...] = (
    ("cars", "fix"), ("fix", "grid"), ("grid", "sim"), ("cycles", "sim"), ("sim", "runs"),
    ("runs", "filter"), ("filter", "argmin"), ("argmin", "sizes"),
    ("cars", "sweep"), ("sweep", "storage"), ("storage", "gap"),
)
DATAFLOW_FIELDS: tuple[str, ...] = (
    *(f"node.{n[0]}" for n in DATAFLOW_NODES),
    *(f"edge.{a}.{b}" for a, b in DATAFLOW_EDGES),
)


#: A study's closing slide: three conclusions, three open questions, three model limits.
#: `pointN` and `openN` take `statement | example or reason`; `limitN` is one short line.
WRAPUP_FIELDS: tuple[str, ...] = (
    *(f"point{i}" for i in range(1, 4)),
    *(f"open{i}" for i in range(1, 4)),
    *(f"limit{i}" for i in range(1, 4)),
)


@dataclass(frozen=True)
class SlideSpec:
    id: str
    layout: str
    section: str
    fields: tuple[str, ...]


def _opener(section: str) -> SlideSpec:
    return SlideSpec(section, "opener", section, ("title", "notes"))


def _content(slide_id: str, layout: str, *fields: str) -> SlideSpec:
    section = slide_id.split("-", 1)[0]
    return SlideSpec(slide_id, layout, section, ("label", "headline", *fields, "notes"))


SLIDES: tuple[SlideSpec, ...] = (
    SlideSpec("title", "title", "", ("title", "subtitle", "byline", "notes")),
    _opener("sim"),
    _content("sim-model", "flow", "step1", "step2", "step3", "step4", "step5", "step6"),
    _content("sim-cars", "cars", "spec.petrol", "spec.hybrid", "spec.phev", "spec.bev"),
    _content("sim-changed", "tiles", "tile1", "tile2", "tile3", "tile4"),
    _opener("cmp"),
    _content("cmp-all", "grouped"),
    _content("cmp-wltc", "single"),
    *(slide for study in ("A", "B", "C") for slide in (
        _opener(study),
        # Study A's owner asked for a method overview and a glossary before the charts.
        # The glossary comes first, so the method slide's terms are defined before use.
        *((_content("A-terms", "terms", *(f"term{i}" for i in range(1, 7))),
           _content("A-steps", "dataflow", *DATAFLOW_FIELDS))
          if study == "A" else ()),
        _content(f"{study}-1", "slot", "figure"),
        _content(f"{study}-2", "slot", "figure"),
        _content(f"{study}-3", "slot", "figure"),
        # Each study closes on its conclusions, open questions and model limits.
        _content(f"{study}-end", "wrapup", *WRAPUP_FIELDS),
    )),
    _opener("lim"),
    _content("lim-rows", "rows", "row1", "row2", "row3"),
    SlideSpec("questions", "closing", "", ("title", "subtitle", "notes")),
)


def lap_position(i: int) -> float | None:
    """Interpolate between consecutive opener slides and the finish line, in metres."""
    if not 0 <= i < len(SLIDES):
        raise IndexError(i)
    if i == 0:
        return None
    anchors = [(j, CORNERS[SECTIONS[s.section][0]]) for j, s in enumerate(SLIDES)
               if s.layout == "opener"]
    anchors.append((len(SLIDES) - 1, CORNERS["finish"]))
    for (first, start), (last, end) in zip(anchors, anchors[1:]):
        if i <= last:
            return start + (end - start) * (i - first) / (last - first)
    raise AssertionError("Missing finish anchor")
