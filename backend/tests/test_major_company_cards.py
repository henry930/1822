import re
from pathlib import Path

from app.data.major_companies import MAJOR_COMPANIES

DOCS_MAJOR_CARDS = Path(__file__).resolve().parents[2] / "docs/major-company-cards.html"


def test_major_company_cards_file_exists_and_is_standalone_html():
    assert DOCS_MAJOR_CARDS.exists()
    html = DOCS_MAJOR_CARDS.read_text()
    # Not a Claude-Artifacts "Design Component" file (those need an external
    # support.js runtime and aren't usable standalone) - a real replacement
    # for the removed major_company_cards/*.dc.html set.
    assert "<!doctype html>" in html.lower()
    assert "support.js" not in html


def test_major_company_card_data_matches_backend():
    html = DOCS_MAJOR_CARDS.read_text()
    for c in MAJOR_COMPANIES:
        pattern = re.compile(
            r"abbr:\s*'" + re.escape(c.abbr) + r"'.*?home:\s*'([^']+)'.*?dest:\s*'([^']+)'",
            re.DOTALL,
        )
        m = pattern.search(html)
        assert m, f"{c.abbr} not found in major-company-cards.html"
        assert m.group(1) == c.home_location, f"{c.abbr} home mismatch"
        assert m.group(2) == c.destination, f"{c.abbr} destination mismatch"
