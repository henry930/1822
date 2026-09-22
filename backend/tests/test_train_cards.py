import re
from pathlib import Path

from app.data.trains import TRAIN_TYPES

DOCS_TRAIN_CARDS = Path(__file__).resolve().parents[2] / "docs/train-cards.html"


def test_train_card_names_match_backend_data():
    """Guards against docs/train-cards.html drifting from the photographed
    card names in app.data.trains (see that module's comment: names must be
    transcribed from train.webp, never invented)."""
    html = DOCS_TRAIN_CARDS.read_text()
    for train in TRAIN_TYPES:
        pattern = re.compile(
            r"num:\s*'" + re.escape(train.code) + r"'.*?name:\s*(\"([^\"]+)\"|'([^']+)')"
        )
        m = pattern.search(html)
        assert m, f"train {train.code} not found in train-cards.html"
        card_name = m.group(2) if m.group(2) is not None else m.group(3)
        assert card_name == train.name, (
            f"train {train.code} name mismatch: card has {card_name!r}, "
            f"backend has {train.name!r}"
        )
