"""Render the text-free circuit backgrounds in slide coordinates."""

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from PIL import Image, ImageDraw, ImageFilter

from pwt.deck import track

THEMES: dict[str, dict[str, str]] = {
    "dark": dict(bg="#000000", fg="#f5f5f7", muted="#86868b", soft="#1c1c1e", line="#2c2c2e"),
    "light": dict(bg="#ffffff", fg="#1d1d1f", muted="#86868b", soft="#f5f5f7", line="#e5e5ea"),
}

_STOPS = [0, 0.45, 0.75, 1]
_RGB = [(10, 132, 255), (48, 209, 88), (255, 214, 10), (255, 69, 58)]
# 1600 slide units span the figure's 16 inches.
_PT = 72 / 100


def speed_colour(v_kph: float) -> str:
    fraction = (v_kph - 40) / 110
    return "#%02x%02x%02x" % tuple(
        round(np.interp(fraction, _STOPS, channel)) for channel in zip(*_RGB)
    )


def _road(ax, points, width):
    speed = np.convolve(np.pad(track.lap().v, 3, mode="edge"), np.ones(7) / 7, "valid")
    bands = np.rint(np.clip((speed - 40) / 110, 0, 1) * 48)
    ax.add_collection(LineCollection([points], colors=speed_colour(95),
                                     linewidths=width * 0.96 * _PT, joinstyle="round"))
    boundaries = np.r_[0, np.flatnonzero(np.diff(bands[:-1])) + 1, len(points) - 1]
    segments = [points[max(start - 1, 0):end + 2]
                for start, end in zip(boundaries, boundaries[1:])]
    colours = [speed_colour(40 + 110 * bands[start] / 48) for start in boundaries[:-1]]
    ax.add_collection(LineCollection(segments, colors=colours, linewidths=width * _PT,
                                     joinstyle="round", capstyle="butt"))
    for i in (0, -1):
        ax.add_patch(Circle(points[i], width / 2, color=speed_colour(40 + 110 * bands[i] / 48),
                            linewidth=0, zorder=3))


def _render(theme, points, scale, path, *, title):
    palette = THEMES[theme]
    fig = Figure(figsize=(16, 9), dpi=200, facecolor="none")
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1], xlim=(0, 1600), ylim=(900, 0))
    ax.set_axis_off()
    offset = points[0] - scale * track.lap().xy[0]
    opacity = 0.14 if theme == "dark" else 0.20
    for i, (_, lines) in enumerate(track.relief()):
        major = i % 5 == 0
        ax.add_collection(LineCollection(
            [line * scale + offset for line in lines], colors=palette["fg"],
            linewidths=(1.6 if major else 1) * _PT, alpha=opacity * (1.8 if major else 1),
            joinstyle="round",
        ))
    canvas.draw()
    contours = Image.fromarray(np.asarray(canvas.buffer_rgba())).copy()
    background = Image.new("RGB", contours.size, palette["bg"])
    picture = Image.composite(contours.convert("RGB"), background, contours.getchannel("A"))
    if title:
        mask = Image.new("L", picture.size)
        ImageDraw.Draw(mask).line(list(map(tuple, points * 2)), fill=255, width=340, joint="curve")
        picture = Image.composite(picture, background, mask.filter(ImageFilter.GaussianBlur(90)))

    for collection in list(ax.collections):
        collection.remove()
    _road(ax, points, 13 if title else 30)
    canvas.draw()
    road = Image.fromarray(np.asarray(canvas.buffer_rgba()))
    picture.paste(road, mask=road.getchannel("A"))

    if title:
        alpha = np.interp(np.linspace(1, 0, picture.height), [0, 0.22, 0.42], [1, 0.82, 0])
        strip = alpha[:, None]
    else:
        alpha = np.interp(np.linspace(0, 1, picture.width), [0, 0.72 * 0.6, 0.72], [1, 0.8, 0])
        strip = alpha[None, :]
    fade = Image.fromarray(np.rint(strip * 255).astype("uint8")).resize(picture.size)
    Image.composite(background, picture, fade).save(path)
    return path


def title_art(theme: str, path: Path) -> Path:
    xy = track.lap().xy
    span = np.ptp(xy, axis=0)
    scale = 610 / span[1]
    points = (xy - xy.min(axis=0) - span / 2) * scale + [800, 375]
    return _render(theme, points, scale, path, title=True)


def opener_art(theme: str, corner: str, zoom: float, path: Path) -> Path:
    distance = track.CORNERS[corner]
    focus = track.opener_frame(distance, zoom)
    points = track.zoomed(distance, zoom, *focus)
    return _render(theme, points, 1600 * zoom, path, title=False)
