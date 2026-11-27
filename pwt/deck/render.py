"""Assemble editable slides in the mockup's 1600 by 900 design coordinates."""

from pathlib import Path

import numpy as np
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.util import Pt
from pptx.oxml.xmlchemy import OxmlElement

from pwt.catalog import POWERTRAIN_NAMES
from pwt.deck import art, data, figures, fonts, track
from pwt.deck.structure import (DATAFLOW_EDGES, DATAFLOW_NODES, SLIDES, SECTIONS,
                                lap_position)
from pwt.sweep import cycles

PLACEHOLDERS = {
    "headline": "Your headline",
    "slot.headline": "Owner's headline",
    "spec": "key specs",
    "tile": ("number", "one line"),
    "row": ("limit", "why it matters", "next step"),
    "term": ("term", "what it means"),
    "point": ("Study {} owner's conclusion", "a real-world example"),
    "open": ("Study {} owner's open question", "why it matters"),
    "limit": "a limit of the model",
    "figure": ("chart or figure from the study", "Study {} owner's slides"),
    "questions.subtitle": "then, if time allows: the live demo",
}


#: Problems found while fitting author text; `python -m pwt.deck` prints them.
WARNINGS: list[str] = []


def _split(text: str, lines: int, size: float, weight: int, spacing: float) -> list[str]:
    """Break `text` at spaces into at most `lines` rows, as evenly wide as possible."""
    words = text.split()
    if lines < 2 or len(words) < 2:
        return [text]
    best = None
    for cut in range(1, len(words)):
        rows = [" ".join(words[:cut]), " ".join(words[cut:])]
        widest = max(fonts.text_width(r, size, weight, spacing=spacing) for r in rows)
        if best is None or widest < best[0]:
            best = (widest, rows)
    return best[1]


def wrap(text: str, size: float, width: float, weight: int = 400) -> list[str]:
    """Greedy word wrap of `text` into rows no wider than `width`."""
    rows: list[str] = []
    for word in text.split():
        if rows and fonts.text_width(rows[-1] + " " + word, size, weight) <= width:
            rows[-1] += " " + word
        else:
            rows.append(word)
    return rows or [""]


def fit(text: str, size: float, max_width: float, min_size: float, lines: int,
        weight: int, spacing: float) -> tuple[list[str], float]:
    """Shrink, then wrap: the rows and font size (px) that set `text` within `max_width`."""
    width = lambda t, s: fonts.text_width(t, s, weight, spacing=spacing * s / size)
    if width(text, size) <= max_width:
        return [text], size
    if width(text, min_size) <= max_width:
        return [text], max(min_size, size * max_width / width(text, size))
    rows = _split(text, lines, size, weight, spacing)
    for s in (size, *(size - k for k in range(1, int(size - min_size) + 1))):
        if max(width(r, s) for r in rows) <= max_width:
            return rows, s
    return rows, min_size


def u(x):
    return round(x * 7620)


def rgb(color):
    return RGBColor.from_string(color.lstrip("#"))


class Canvas:
    def __init__(self, slide, theme, fields, slide_id="", out_dir=None):
        self.slide = slide
        self.theme = theme
        self.out_dir = out_dir
        self.slide_id = slide_id
        self.shapes = slide.shapes
        self.palette = art.THEMES[theme]
        self.fields = fields

    def color(self, key):
        return rgb(self.palette.get(key, key))

    def text(
        self,
        x,
        y,
        value,
        size,
        color="fg",
        weight=400,
        center=False,
        placeholder=None,
        spacing=0,
    ):
        # SVG positions text by baseline. Impress positions its Inter line box by top.
        width = 2 * min(x, 1600 - x) if center else max(100, 1600 - x)
        box = self.shapes.add_textbox(
            u(x + 0.7 - (width / 2 if center else 0)),
            u(y - size * 0.994),
            u(width),
            u(size * 1.55),
        )
        frame = box.text_frame
        frame.auto_size = MSO_AUTO_SIZE.NONE
        frame.word_wrap = False
        frame.margin_left = frame.margin_right = frame.margin_top = (
            frame.margin_bottom
        ) = 0
        p = frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER if center else PP_ALIGN.LEFT
        r = p.add_run()
        r.text = value
        r.font.name = fonts.FAMILIES[weight]
        r.font.bold = weight >= 700
        r.font.size = Pt(size * 0.6)
        r.font.color.rgb = self.color(color)
        if spacing:
            r._r.get_or_add_rPr().set("spc", str(round(spacing * 60)))
        if placeholder:
            box.name = f"placeholder:{placeholder}"
            r.font.italic = True
            r.font.color.rgb = RGBColor(
                *(
                    round(0.75 * a + 0.25 * b)
                    for a, b in zip(self.color("muted"), self.color("bg"))
                )
            )
        return box

    def field(self, field, x, y, size, default=None, max_width=None, min_size=None,
              lines=1, **style):
        """One author field. Written text that is too wide for `max_width` first shrinks
        (down to `min_size`), then wraps onto up to `lines` lines stacked upwards from the
        baseline `y`; anything still too wide is reported in WARNINGS."""
        value = self.fields.get(field)
        text = value or default or PLACEHOLDERS.get(field, field)
        self.rows = 1
        if not value or not max_width:
            return self.text(x, y, text, size, placeholder=None if value else field, **style)
        base = size
        rows, size = fit(text, size, max_width, min_size or size, lines,
                         style.get("weight", 400), style.get("spacing", 0))
        style["_size"] = base
        if fonts.text_width(max(rows, key=len), size, style.get("weight", 400),
                            spacing=style.get("spacing", 0)) > max_width + 0.5:
            WARNINGS.append(f"{self.slide_id}.{field} is too long to fit; shorten it.")
        if "spacing" in style:  # letter spacing scales with the shrunk size
            style["spacing"] = style["spacing"] * size / style["_size"]
        style.pop("_size")
        self.rows = len(rows)
        boxes = []
        for k, row in enumerate(rows):
            lift = (len(rows) - 1 - k) * size * 1.05
            boxes.append(self.text(x, y - lift, row, size, **style))
        return boxes[-1]

    def shape(self, x, y, w, h, fill, radius=0, ellipse=False, top_only=False):
        kind = (
            MSO_SHAPE.OVAL
            if ellipse
            else MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        )
        if top_only:
            kind = MSO_SHAPE.ROUND_2_SAME_RECTANGLE
        s = self.shapes.add_shape(kind, u(x), u(y), u(w), u(h))
        if radius:
            s.adjustments[0] = radius / min(w, h)
        s.line.fill.background()
        if fill:
            s.fill.solid()
            s.fill.fore_color.rgb = self.color(fill)
        else:
            s.fill.background()
        return s

    def line(self, points, color, width):
        pts = [(u(x), u(y)) for x, y in points]
        f = self.shapes.build_freeform(*pts[0])
        f.add_line_segments(pts[1:], close=False)
        s = f.convert_to_shape()
        s.fill.background()
        s.line.color.rgb = self.color(color)
        s.line.width = u(width)
        return s

    def arrow(self, x, y, length, head):
        self.line([(x, y), (x + length, y)], "muted", 2.5)
        self.line(
            [
                (x + length - head, y - head),
                (x + length, y),
                (x + length - head, y + head),
            ],
            "muted",
            2.5,
        )

    def lap(self, i):
        points = track.minimap_points()
        outline = self.line(points, "muted", 2.5)
        outline.name = "lap-outline"
        alpha = OxmlElement("a:alpha")
        alpha.set("val", "70000")
        outline.line._get_or_add_ln().solidFill.srgbClr.append(alpha)
        dot = points[track.index_at(lap_position(i))]
        x, y = dot
        self.shape(x - 8, y - 8, 16, 16, "fg", ellipse=True).name = "lap-dot"
        x, y = track.label_spot(points, dot, str(i + 1))
        self.text(x, y + 6, str(i + 1), 18, weight=600, center=True).name = "lap-label"

    def check(self, field, text, size, max_width, weight=400):
        if fonts.text_width(text, size, weight) > max_width:
            WARNINGS.append(f"{self.slide_id}.{field} is too long to fit; shorten it.")

    def parts(self, field, defaults, positions, center=False, widths=()):
        value = self.fields.get(field, "")
        parts = [s.strip() for s in value.split("|")] if value else defaults
        if value and len(parts) > len(positions):
            WARNINGS.append(f"{self.slide_id}.{field} has {len(parts)} parts separated by |; "
                            f"only {len(positions)} are used.")
        for n, (part, (x, y, size), width) in enumerate(
                zip(parts, positions, widths or [None] * len(positions))):
            if value and width and n == len(positions) - 1 and field.startswith("tile"):
                rows = wrap(part, size, width, 600)
                if len(rows) > 3:
                    WARNINGS.append(f"{self.slide_id}.{field}: the line under the number "
                                    "wraps past 3 lines; shorten it.")
                for k, row in enumerate(rows[:3]):
                    self.text(x, y + k * size * 1.3, row, size, weight=600, center=center)
                continue
            if value and width:
                self.check(field, part, size, width, 600)
            self.text(
                x,
                y,
                part,
                size,
                weight=600,
                center=center,
                placeholder=None if value else field,
            )


def chart(c, single):
    keys = ["wltc"] if single else data.CYCLE_KEYS
    mx = max(data.cell(pt, k).co2_eu for k in keys for pt in data.POWERTRAINS)
    for g, k in enumerate(keys):
        for i, pt in enumerate(data.POWERTRAINS):
            name, color = POWERTRAIN_NAMES[pt], data.CAR_COLOURS[pt]
            if not single and g == 0:
                x = 380 + i * 210
                c.shape(x + 1, 216, 18, 18, color, ellipse=True)
                c.text(x + 28, 233, name, 21, "muted")
            row = data.cell(pt, k)
            x, base, w, r = (
                (265 + i * 290, 740, 200, 5)
                if single
                else (110 + g * 370 + i * 70, 750, 60, 3)
            )
            h = (460 if single else 450) * row.co2_eu / mx
            hollow = row.short_steps > 0
            s = c.shape(x, base - h, w, h, None if hollow else color, r, top_only=True)
            s.name = f"bar:{pt}:{k}"
            if hollow:
                s.line.color.rgb = c.color(color)
                s.line.width = u(4 if single else 3)
            val = format(row.co2_eu, ".1f" if single else ".0f") + (
                "*" if hollow else ""
            )
            c.text(
                x + w / 2,
                base - h - (22 if single else 12),
                val,
                44 if single else 19,
                weight=700 if single else 600,
                center=True,
                spacing=-1 if single else 0,
            )
            if single:
                c.text(x + w / 2, 786, name, 24, "muted", 500, True)
        if not single:
            c.text(
                245 + 370 * g, 796, data.CYCLE_LABELS[k], 24, weight=600, center=True
            )
    c.text(
        800,
        830,
        "g CO2/km, EU grid 250 g/kWh · * outlined: engine short of the trace on some steps",
        17,
        "muted",
        center=True,
    )


def flow(c):
    for i in range(6):
        x = 70 + i * 250
        c.shape(x, 330, 210, 250, "fg" if i == 5 else "soft", 22)
        c.text(x + 105, 400, str(i + 1), 20, "muted", 600, True)
        key = f"step{i+1}"
        name, _, detail = c.fields.get(key, "").partition("|")
        if name.strip():
            c.check(key, name.strip(), 27, 195, 700)
        c.text(
            x + 105,
            460,
            name.strip() or key,
            27,
            "bg" if i == 5 else "fg",
            700,
            True,
            placeholder=None if name else key,
        )
        parts = detail.strip().split(", ")
        if len(parts) >= 3:
            parts = [", ".join(parts[:2]), ", ".join(parts[2:])]
        if len(parts) > 2:
            WARNINGS.append(f"{c.slide_id}.{key}: the detail wraps onto 2 lines at most.")
        for j, line in enumerate(parts[:2]):
            c.check(key, line, 17, 195)
            c.text(x + 105, 505 + j * 24, line, 17, "muted", center=True)
        if i < 5:
            c.arrow(x + 218, 455, 24, 8)


#: Dataflow geometry in design units: node size, column and row pitch.
DF_W, DF_H = 220, 104
DF_X = [40 + 310 * k for k in range(5)]
DF_Y = [248, 438, 628]


def _df_box(col, row):
    return DF_X[col], DF_Y[row], DF_W, DF_H


def _df_arrow(c, points, label=""):
    """A polyline with an arrowhead at its end, and its data label beside the first leg."""
    shape = c.line(points, "muted", 2.5)
    ln = shape.line._get_or_add_ln()
    tail = OxmlElement("a:tailEnd")
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    ln.append(tail)
    if label:
        (x0, y0), (x1, y1) = points[0], points[1]
        if y0 == y1:  # horizontal: centred above the arrow
            c.text((x0 + x1) / 2, y0 - 10, label, 16, "muted", center=True)
        else:  # vertical: to the right of it
            c.text(x0 + 12, (y0 + y1) / 2 + 6, label, 16, "muted")


def dataflow(c):
    """Study A's method as a dataflow chart: inputs, processes, saved files and results."""
    from pptx.enum.shapes import MSO_SHAPE as S

    kinds = {"data": (S.PARALLELOGRAM, None, "fg"), "process": (S.ROUNDED_RECTANGLE, "soft", "fg"),
             "file": (S.CAN, "line", "fg"), "result": (S.PARALLELOGRAM, "fg", "bg")}
    boxes = {}
    for name, kind, col, row in DATAFLOW_NODES:
        x, y, w, h = _df_box(col, row)
        boxes[name] = (x, y, w, h)
        shape_kind, fill, ink = kinds[kind]
        s = c.shapes.add_shape(shape_kind, u(x), u(y), u(w), u(h))
        if shape_kind == S.ROUNDED_RECTANGLE:
            s.adjustments[0] = 18 / h
        elif shape_kind == S.PARALLELOGRAM:
            s.adjustments[0] = 0.2  # a shallow slant leaves room for the text
        if fill:
            s.fill.solid()
            s.fill.fore_color.rgb = c.color(fill)
            s.line.fill.background()
        else:
            s.fill.background()
            s.line.color.rgb = c.color("muted")
            s.line.width = u(2.5)
        key = f"node.{name}"
        title, _, detail = (t.strip() for t in c.fields.get(key, "").partition("|"))
        cx, top = x + w / 2, y + (14 if kind == "file" else 0)
        room = w - (70 if shape_kind == S.PARALLELOGRAM else 36)
        rows = wrap(detail, 16.5, room) if detail else []
        if title:
            c.check(key, title, 21, room, 700)
            if len(rows) > 2:
                WARNINGS.append(f"{c.slide_id}.{key}: the detail wraps past 2 lines; "
                                "shorten it.")
        lift = 11 if len(rows) > 1 else 0  # centre two detail lines in the box
        c.text(cx, top + 45 - lift, title or name, 21, ink, 700, True,
               placeholder=None if title else key)
        for k, row in enumerate(rows[:2]):
            c.text(cx, top + 72 - lift + k * 21, row, 16.5, "muted" if ink == "fg" else ink,
                   center=True)
    for a, b in DATAFLOW_EDGES:
        ax, ay, aw, ah = boxes[a]
        bx, by, bw, bh = boxes[b]
        label = c.fields.get(f"edge.{a}.{b}", "")
        if ay == by:  # same row
            y = ay + ah / 2
            points = ([(ax + aw, y), (bx, y)] if bx > ax else [(ax, y), (bx + bw, y)])
        elif ax == bx:  # same column
            x = ax + aw / 2
            points = ([(x, ay + ah), (x, by)] if by > ay else [(x, ay), (x, by + bh)])
        else:  # down, then across
            x, y = ax + aw / 2, by + bh / 2
            points = [(x, ay + ah), (x, y), (bx, y)]
        _df_arrow(c, points, label)
    # Key to the shapes, in one row under the chart.
    kx, ky = DF_X[0] + 20, DF_Y[2] + DF_H + 46
    for k, (shape_kind, fill, text) in enumerate((
            (S.PARALLELOGRAM, None, "input or output"), (S.ROUNDED_RECTANGLE, "soft", "process"),
            (S.CAN, "line", "saved file"), (S.PARALLELOGRAM, "fg", "result on a later slide"))):
        x = kx + k * 330
        y = ky
        s = c.shapes.add_shape(shape_kind, u(x), u(y), u(46), u(30))
        if fill:
            s.fill.solid()
            s.fill.fore_color.rgb = c.color(fill)
            s.line.fill.background()
        else:
            s.fill.background()
            s.line.color.rgb = c.color("muted")
            s.line.width = u(2)
        c.text(x + 60, y + 22, text, 15, "muted")


def _marker(c, x, y, kind):
    """A filled circle with a check, question mark or exclamation mark: native shapes."""
    fill = {"point": "#30d158", "open": "#ff9f0a", "limit": None}[kind]
    s = c.shapes.add_shape(MSO_SHAPE.OVAL, u(x), u(y), u(34), u(34))
    s.fill.solid()
    s.fill.fore_color.rgb = RGBColor.from_string(fill[1:]) if fill else c.color("muted")
    s.line.fill.background()
    if kind == "point":
        c.line([(x + 9, y + 18), (x + 15, y + 24), (x + 26, y + 11)], "bg", 3.5)
    else:
        c.text(x + 17, y + 25, "?" if kind == "open" else "!", 22, "bg", 700, True)


def wrapup(c, spec):
    """Conclusions and open questions in two columns, model limits in a strip below."""
    study = spec.section
    columns = (("point", 110, "WHAT WE CAN CONCLUDE"), ("open", 840, "STILL OPEN"))
    for kind, x, heading in columns:
        c.text(x, 262, heading, 19, "muted", 600)
        for i in range(3):
            key = f"{kind}{i+1}"
            y = 300 + i * 118
            _marker(c, x, y, kind)
            value = c.fields.get(key, "")
            if not value:
                main, sub = (t.format(study) for t in PLACEHOLDERS[kind])
                c.text(x + 52, y + 26, main, 24, weight=600, placeholder=key)
                c.text(x + 52, y + 58, sub, 18, placeholder=key)
                continue
            statement, _, example = (t.strip() for t in value.partition("|"))
            c.check(key, statement, 24, 600, 600)
            c.text(x + 52, y + 26, statement, 24, weight=600)
            rows = wrap(example, 18, 600)
            if len(rows) > 2:
                WARNINGS.append(f"{c.slide_id}.{key}: the example wraps past 2 lines; "
                                "shorten it.")
            for k, row in enumerate(rows[:2]):
                c.text(x + 52, y + 56 + k * 24, row, 18, "muted")
    c.shape(110, 668, 1380, 150, "soft", 22)
    c.text(140, 708, "MODEL LIMITS", 17, "muted", 600)
    for i in range(3):
        key = f"limit{i+1}"
        x = 140 + i * 450
        _marker(c, x, 728, "limit")
        value = c.fields.get(key, "")
        if not value:
            c.text(x + 48, 752, PLACEHOLDERS["limit"], 18, placeholder=key)
            continue
        rows = wrap(value, 18, 380)
        if len(rows) > 2:
            WARNINGS.append(f"{c.slide_id}.{key}: wraps past 2 lines; shorten it.")
        for k, row in enumerate(rows[:2]):
            c.text(x + 48, 752 + k * 24, row, 18)


def terms(c):
    """A glossary: up to six rows of `term | what it means`, the meaning on up to 2 lines."""
    for i in range(6):
        key = f"term{i+1}"
        y = 262 + i * 96
        c.line([(180, y - 40), (1420, y - 40)], "line", 2)
        value = c.fields.get(key, "")
        term, _, meaning = (s.strip() for s in value.partition("|"))
        if not value:
            c.text(180, y, PLACEHOLDERS["term"][0], 26, weight=700, placeholder=key)
            c.text(560, y, PLACEHOLDERS["term"][1], 21, placeholder=key)
            continue
        c.check(key, term, 26, 350, 700)
        c.text(180, y, term, 26, weight=700)
        rows = wrap(meaning, 21, 860)
        if len(rows) > 2:
            WARNINGS.append(f"{c.slide_id}.{key}: the meaning wraps past 2 lines; shorten it.")
        for k, row in enumerate(rows[:2]):
            c.text(560, y + k * 28, row, 21)


def cars(c):
    traces = cycles()
    for i, (k, pt) in enumerate(zip(data.CYCLE_KEYS, data.POWERTRAINS)):
        x = 80 + 370 * i
        tr = traces[k]
        xs = tr.s if tr.s is not None else tr.t
        km = (
            xs[-1] / 1000
            if tr.s is not None
            else sum(np.diff(xs) * tr.v_kph[1:]) / 3600
        )
        stride = max(1, len(xs) // 300)
        c.shape(x, 230, 330, 270, "soft", 22)
        c.line(
            zip(
                x + 25 + 280 * xs[::stride] / xs[-1],
                410 - 140 * tr.v_kph[::stride] / 150,
            ),
            "fg",
            2.5,
        )
        c.text(x + 25, 455, data.CYCLE_LABELS[k], 26, weight=700)
        c.text(x + 25, 485, f"{km:.1f} km", 18, "muted")
        c.shape(x + 24, 594, 32, 32, data.CAR_COLOURS[pt], ellipse=True)
        c.text(x + 70, 620, POWERTRAIN_NAMES[pt], 26, weight=700)
        c.field("spec." + pt, x + 70, 654, 18, PLACEHOLDERS["spec"], weight=600,
                max_width=255)


def body(c, spec):
    if spec.layout in ("grouped", "single"):
        chart(c, spec.layout == "single")
    elif spec.layout == "flow":
        flow(c)
    elif spec.layout == "cars":
        cars(c)
    elif spec.layout == "tiles":
        for i in range(4):
            x = 80 + 370 * i
            c.shape(x, 280, 330, 400, "soft", 26)
            c.parts(
                f"tile{i+1}",
                PLACEHOLDERS["tile"],
                [(x + 165, 470, 64), (x + 165, 550, 22)],
                True,
                widths=(300, 300),
            )
    elif spec.layout == "wrapup":
        wrapup(c, spec)
    elif spec.layout == "dataflow":
        dataflow(c)
    elif spec.layout == "terms":
        terms(c)
    elif spec.layout == "rows":
        c.text(230, 270, "LIMIT", 19, "muted", 600)
        c.text(900, 270, "NEXT STEP", 19, "muted", 600)
        for i in range(3):
            y = 320 + i * 150
            c.line([(230, y), (1370, y)], "line", 2)
            c.arrow(760, y + 62, 60, 10)
            c.parts(
                f"row{i+1}",
                PLACEHOLDERS["row"],
                [(230, y + 62, 32), (230, y + 100, 21), (900, y + 72, 30)],
                widths=(510, 510, 470),
            )
    elif spec.layout == "slot":
        path = c.fields.get("figure")
        name = None
        if path and path.startswith("chart:"):
            name = path.removeprefix("chart:").strip()
            path = figures.render(name, c.theme, c.out_dir)
        elif path:
            path = Path(__file__).resolve().parents[2] / path
            if not path.is_file():
                raise FileNotFoundError(
                    f"{spec.id}.figure: no image at {fields_path(path)}. Give a path from the "
                    "repository root, e.g. docs/phase-3-sizing.png."
                )
        if path:
            with Image.open(path) as image:
                w, h = image.size
            scale = min(1100 / w, 520 / h)
            picture = c.shapes.add_picture(
                str(path),
                u(800 - w * scale / 2),
                u(500 - h * scale / 2),
                u(w * scale),
                u(h * scale),
            )
            if name:
                picture.name = f"chart:{name}"
        else:
            s = c.shape(250, 240, 1100, 520, None, 26)
            s.line.color.rgb = c.color("line")
            s.line.width = u(3)
            s.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            hint, owner = PLACEHOLDERS["figure"]
            c.parts(
                "figure",
                (hint, owner.format(spec.section)),
                [(800, 490, 30), (800, 535, 22)],
                True,
            )


def fields_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path(__file__).resolve().parents[2]))
    except ValueError:
        return str(path)


def title_credit(c):
    fields = ("subtitle", "byline")
    if all(c.fields.get(k) for k in fields):
        c.text(
            800, 800, " · ".join(c.fields[k] for k in fields), 26, "muted", center=True
        )
        return
    # Keep incomplete credits centred on one line while exposing each placeholder
    # as its own editable shape. Measure advances in the same face as the slide.
    parts = []
    for field in ("subtitle", None, "byline"):
        missing = field is not None and not c.fields.get(field)
        value = (c.fields.get(field) or field) if field else " · "
        width = fonts.text_width(value, 26, italic=missing)
        parts.append((value, width, field if missing else None))
    x = 800 - sum(width for _, width, _ in parts) / 2
    for value, width, placeholder in parts:
        c.text(x, 800, value, 26, "muted", placeholder=placeholder)
        x += width


def use_inter_theme(prs) -> None:
    """Make Inter the theme's heading and body font, so any text box added later is Inter."""
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    theme = prs.slide_master.part.part_related_by(RT.THEME)
    blob = theme.blob.decode("utf-8")
    import re
    blob = re.sub(r'(<a:(?:majorFont|minorFont)>\s*<a:latin typeface=")[^"]*"', r'\1Inter"', blob)
    theme._blob = blob.encode("utf-8")


def build(theme: str, content: dict[str, dict[str, str]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    WARNINGS.clear()
    prs = Presentation()
    use_inter_theme(prs)
    prs.slide_width, prs.slide_height = u(1600), u(900)
    for i, spec in enumerate(SLIDES):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        fields = {k: data.fill(v) for k, v in content.get(spec.id, {}).items()}
        c = Canvas(slide, theme, fields, spec.id, out_dir)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = c.color("bg")
        source = "pwt.deck.structure"
        if spec.layout in ("title", "closing", "opener"):
            path = out_dir / f"{theme}-{spec.id}.png"
            if spec.layout == "title":
                art.title_art(theme, path)
            else:
                corner, number, zoom = SECTIONS.get(spec.section, ("finish", "", 2.4))
                art.opener_art(theme, corner, zoom, path)
            c.shapes.add_picture(str(path), 0, 0, prs.slide_width, prs.slide_height)
            source = (
                "pwt.deck.track and pwt.deck.art. Contour lines are an impression, "
                "interpolated from the generated lap's altitude (373–470 m), not survey data."
            )
            if spec.layout == "title":
                c.field("title", 801, 740, 88, weight=700, center=True, spacing=-3,
                        max_width=1380, min_size=60, lines=2)
                title_credit(c)
            elif spec.layout == "opener":
                c.field("title", 110, 480, 96, weight=700, spacing=-3.5,
                        max_width=790, min_size=64, lines=2)
                c.text(110, 380 - (c.rows - 1) * 96 * 1.05, number, 28, "muted", 600)
                c.text(
                    110,
                    540,
                    f"{track.CORNER_NAMES[corner]} · {track.CORNERS[corner]/1000:.1f} km",
                    28,
                    "muted",
                )
            else:
                c.field("title", 110, 480, 110, weight=700, spacing=-4,
                        max_width=790, min_size=72, lines=2)
                c.field(
                    "subtitle",
                    110,
                    545,
                    28,
                    PLACEHOLDERS["questions.subtitle"],
                    weight=600,
                )
        else:
            c.field("label", 110, 92, 24, color="muted", weight=500, max_width=1270)
            c.field(
                "headline",
                110,
                150,
                44,
                PLACEHOLDERS["slot.headline" if spec.layout == "slot" else "headline"],
                weight=700 if fields.get("headline") else 600,
                max_width=1270,
                min_size=32,
            )
            body(c, spec)
            c.text(110, 862, "model output · first draft", 17, "muted")
            if spec.layout in ("cars", "grouped", "single"):
                source = "pwt.sweep and pwt.deck.data"
            elif fields.get("figure", "").startswith("chart:"):
                name = fields["figure"].removeprefix("chart:").strip()
                source = (
                    f"pwt.deck.figures, redrawn from "
                    f"{fields_path(figures.FIGURES[name])} (study figure {figures.study_figure(name)})"
                )
            elif fields.get("figure"):
                source = fields["figure"]
        if i:
            c.lap(i)
        # Impress applies the theme shadow even to shapes with an empty effectLst.
        for effect in slide._element.xpath(".//a:effectRef"):
            effect.set("idx", "0")
        slide.notes_slide.notes_text_frame.text = (
            fields.get("notes", "") + "\n\nSource: " + source
        )
    path = out_dir / f"group-deck-{theme}.pptx"
    prs.save(path)
    return path
