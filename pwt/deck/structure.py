"""Slide order, author-editable fields and positions along the Spa lap."""

from dataclasses import dataclass

# keep in sync with track.CORNERS
CORNERS = {
    "start": 0, "la_source": 220, "eau_rouge": 1010, "les_combes": 2200,
    "pouhon": 3600, "stavelot": 4740, "bus_stop": 6540, "finish": 6990,
}

SECTIONS: dict[str, tuple[str, str, float]] = {
    "sim": ("la_source", "01", 3.2),
    "cmp": ("eau_rouge", "02", 2.8),
    "A": ("les_combes", "03 · Study A", 3.0),
    "B": ("pouhon", "04 · Study B", 2.6),
    "C": ("stavelot", "05 · Study C", 3.0),
    "lim": ("bus_stop", "06", 3.4),
}


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
        _content(f"{study}-1", "slot", "figure"),
        _content(f"{study}-2", "slot", "figure"),
        _content(f"{study}-3", "slot", "figure"),
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
