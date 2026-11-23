import numpy as np
from PIL import Image

from pwt.deck.art import opener_art, speed_colour, title_art


def test_speed_colour_ends():
    assert speed_colour(20) == speed_colour(40) == "#0a84ff"
    assert speed_colour(180) == speed_colour(150) == "#ff453a"


def test_opener_png(tmp_path):
    path = tmp_path / "o.png"
    assert opener_art("dark", "stavelot", 3.0, path) == path
    with Image.open(path) as image:
        assert image.size == (3200, 1800)
        assert image.getpixel((40, 40)) == (0, 0, 0)
        pixels = np.asarray(image)
        assert pixels[:, :640].mean() < 8
        assert np.ptp(pixels[:, 1600:], axis=2).max() > 120


def test_title_png_light(tmp_path):
    path = tmp_path / "t.png"
    assert title_art("light", path) == path
    with Image.open(path) as image:
        assert image.size == (3200, 1800)
        assert image.getpixel((40, 40)) == (255, 255, 255)
