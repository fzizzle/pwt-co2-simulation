"""The deck is set in Inter, and author text that is too long is fitted or reported."""

import shutil
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("fc-list") is None, reason="needs fontconfig")

from pwt.deck import fonts  # noqa: E402
from pwt.deck.render import WARNINGS, build  # noqa: E402


def _xml(pptx: Path, prefix: str) -> str:
    with zipfile.ZipFile(pptx) as z:
        return "".join(z.read(n).decode() for n in z.namelist() if n.startswith(prefix))


@pytest.fixture(scope="module")
def long_deck(tmp_path_factory):
    content = {
        "title": {"title": "Does how you drive matter more than what you drive?"},
        "sim": {"title": "How the simulation works, step by step"},
        "cmp-all": {"headline": "x" * 120},
    }
    out = tmp_path_factory.mktemp("deck")
    path = build("dark", content, out)
    return path, list(WARNINGS)


def test_inter_files_found():
    for weight in fonts.STYLES:
        for italic in (False, True):
            assert fonts.inter_file(weight, italic).is_file()


def test_text_width_scales():
    assert fonts.text_width("Spa", 88) == pytest.approx(2 * fonts.text_width("Spa", 44))


def test_theme_and_runs_are_inter(long_deck):
    path, _ = long_deck
    import re
    theme = _xml(path, "ppt/theme/theme1.xml")  # the slide master's theme
    assert re.findall(r'<a:latin typeface="([^"]*)"', theme)[:2] == ["Inter", "Inter"]
    slides = _xml(path, "ppt/slides/slide")
    faces = {f.split('"')[1] for f in slides.split('typeface=')[1:]}
    assert faces <= {"Inter", "Inter Medium", "Inter SemiBold"}


def test_long_titles_wrap_and_headlines_warn(long_deck):
    from pptx import Presentation

    path, warnings = long_deck
    deck = Presentation(path)
    title_rows = [s.text_frame.text for s in deck.slides[0].shapes
                  if s.has_text_frame and s.text_frame.text.strip()
                  and s.text_frame.text in "Does how you drive matter more than what you drive?"]
    assert len(title_rows) == 2
    opener = {s.text_frame.text: s.top for s in deck.slides[1].shapes if s.has_text_frame}
    assert opener["01"] < min(top for text, top in opener.items() if "simulation" in text or "step" in text)
    assert any(w.startswith("cmp-all.headline") for w in warnings)


def test_missing_figure_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="A-1.figure"):
        build("dark", {"A-1": {"figure": "docs/no-such-figure.png"}}, tmp_path)
