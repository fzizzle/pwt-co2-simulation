import shutil

import pytest

from pwt.deck.fidelity import report


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("soffice", "pdftoppm", "chromium")),
    reason="Slide comparison needs LibreOffice, Poppler and Chromium",
)
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_every_slide_matches_mockup(theme, tmp_path):
    rows = report(theme, tmp_path)
    assert [i for i, _ in rows] == list(range(1, 24))
    failed = [(i, score) for i, score in rows if score < 0.99]
    assert not failed, ", ".join(f"slide {i} {score:.6f}" for i, score in failed)
