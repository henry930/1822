import json
import re
from pathlib import Path

from app.data.hex_map import CITIES, OFFBOARD_AREAS, TERRAIN_HEXES
from app.data.stock_market import STOCK_MARKET_CELLS

DOCS = Path(__file__).resolve().parents[2] / "docs"


def _embedded_json(html: str, var_name: str):
    """Boards render their grid client-side from a `const <var> = [...]`
    JSON literal (data-id attributes are added by that JS at runtime, so
    they aren't present in the static file - parse the source array instead)."""
    m = re.search(rf"const {var_name} = (\[.*?\]);", html, re.DOTALL)
    assert m, f"couldn't find `const {var_name} = [...]` in the board HTML"
    return json.loads(m.group(1))


def test_stock_market_board_exists_and_has_all_cells():
    html = (DOCS / "stock-market-board.html").read_text()
    assert (DOCS / "stock-market-board.png").exists()
    cells = _embedded_json(html, "CELLS")
    assert len(cells) == len(STOCK_MARKET_CELLS)


def test_hex_map_board_exists_and_has_all_catalogued_hexes():
    html = (DOCS / "hex-map-board.html").read_text()
    assert (DOCS / "hex-map-board.png").exists()
    points = _embedded_json(html, "POINTS")
    expected_count = len(CITIES) + sum(len(a.hexes) for a in OFFBOARD_AREAS) + len(TERRAIN_HEXES)
    assert len(points) == expected_count
