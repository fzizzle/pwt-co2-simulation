"""Assemble editable slides in the mockup's 1600 by 900 design coordinates."""

from pathlib import Path

import numpy as np
from matplotlib.font_manager import FontProperties, findfont
from PIL import Image, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.util import Pt
from pptx.oxml.xmlchemy import OxmlElement

from pwt.catalog import POWERTRAIN_NAMES
from pwt.deck import art, data, track
from pwt.deck.structure import SLIDES, SECTIONS, lap_position
from pwt.sweep import cycles

PLACEHOLDERS = {
    "headline": "Your headline",
    "slot.headline": "Owner's headline",
    "spec": "key specs",
    "tile": ("number", "one line"),
    "row": ("limit", "why it matters", "next step"),
    "figure": ("chart or figure from the study", "Study {} owner's slides"),
    "questions.subtitle": "then, if time allows: the live demo",
}


def u(x):
    return round(x * 7620)


def rgb(color):
    return RGBColor.from_string(color.lstrip("#"))


class Canvas:
    def __init__(self, slide, theme, fields):
        self.slide = slide
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
        r.font.name = {500: "Inter Medium", 600: "Inter SemiBold"}.get(weight, "Inter")
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

    def field(self, field, x, y, size, default=None, **style):
        value = self.fields.get(field)
        return self.text(
            x,
            y,
            value or default or PLACEHOLDERS.get(field, field),
            size,
            placeholder=None if value else field,
            **style,
        )

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

    def parts(self, field, defaults, positions, center=False):
        value = self.fields.get(field, "")
        parts = [s.strip() for s in value.split("|")] if value else defaults
        for part, (x, y, size) in zip(parts, positions):
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
        for j, line in enumerate(parts):
            c.text(x + 105, 505 + j * 24, line, 17, "muted", center=True)
        if i < 5:
            c.arrow(x + 218, 455, 24, 8)


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
        c.field("spec." + pt, x + 70, 654, 18, PLACEHOLDERS["spec"], weight=600)


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
            )
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
            )
    elif spec.layout == "slot":
        path = c.fields.get("figure")
        if path:
            path = Path(__file__).resolve().parents[2] / path
            with Image.open(path) as image:
                w, h = image.size
            scale = min(1100 / w, 520 / h)
            c.shapes.add_picture(
                str(path),
                u(800 - w * scale / 2),
                u(500 - h * scale / 2),
                u(w * scale),
                u(h * scale),
            )
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
        face = FontProperties(family="Inter", style="italic" if missing else "normal")
        width = ImageFont.truetype(findfont(face), 104).getlength(value) / 4
        parts.append((value, width, field if missing else None))
    x = 800 - sum(width for _, width, _ in parts) / 2
    for value, width, placeholder in parts:
        c.text(x, 800, value, 26, "muted", placeholder=placeholder)
        x += width


def build(theme: str, content: dict[str, dict[str, str]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    prs = Presentation()
    prs.slide_width, prs.slide_height = u(1600), u(900)
    for i, spec in enumerate(SLIDES):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        fields = {k: data.fill(v) for k, v in content.get(spec.id, {}).items()}
        c = Canvas(slide, theme, fields)
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
                c.field("title", 801, 740, 88, weight=700, center=True, spacing=-3)
                title_credit(c)
            elif spec.layout == "opener":
                c.text(110, 380, number, 28, "muted", 600)
                c.field("title", 110, 480, 96, weight=700, spacing=-3.5)
                c.text(
                    110,
                    540,
                    f"{track.CORNER_NAMES[corner]} · {track.CORNERS[corner]/1000:.1f} km",
                    28,
                    "muted",
                )
            else:
                c.field("title", 110, 480, 110, weight=700, spacing=-4)
                c.field(
                    "subtitle",
                    110,
                    545,
                    28,
                    PLACEHOLDERS["questions.subtitle"],
                    weight=600,
                )
        else:
            c.field("label", 110, 92, 24, color="muted", weight=500)
            c.field(
                "headline",
                110,
                150,
                44,
                PLACEHOLDERS["slot.headline" if spec.layout == "slot" else "headline"],
                weight=700 if fields.get("headline") else 600,
            )
            body(c, spec)
            c.text(110, 862, "model output · first draft", 17, "muted")
            if spec.layout in ("cars", "grouped", "single"):
                source = "pwt.sweep and pwt.deck.data"
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
