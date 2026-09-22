from pathlib import Path

from app.data.major_companies import MAJOR_COMPANIES
from app.data.minor_companies import MINOR_COMPANIES
from app.data.private_companies import PRIVATE_COMPANIES
from app.data.trains import TRAIN_TYPES

DOCS_CARDS = Path(__file__).resolve().parents[2] / "docs/cards"


def test_one_png_per_train():
    files = sorted(p.name for p in (DOCS_CARDS / "trains").glob("train_*.png"))
    expected = sorted(f"train_{t.code}.png" for t in TRAIN_TYPES)
    assert files == expected


def test_one_png_per_minor_company():
    """The card sheet includes both base game (M1-M24) and 1822+ (M25-M30)."""
    files = {p.name for p in (DOCS_CARDS / "minors").glob("M*.png")}
    expected = {f"M{c.number}.png" for c in MINOR_COMPANIES}
    assert files == expected


def test_one_png_per_private_company():
    """The card sheet includes both base game (P1-P18) and 1822+ (P19-P21)."""
    files = {p.name for p in (DOCS_CARDS / "privates").glob("P*.png")}
    expected = {f"P{c.number}.png" for c in PRIVATE_COMPANIES}
    assert files == expected


def test_one_png_per_major_company():
    files = {p.name for p in (DOCS_CARDS / "majors").glob("*.png")}
    expected = {f"{c.abbr.replace('&', '')}.png" for c in MAJOR_COMPANIES}
    assert files == expected
