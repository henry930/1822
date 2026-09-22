"""Render the full stock market grid (backend/app/data/stock_market.py) as a
standalone HTML page, matching the staircase layout on board.webp: rows 0-2
(the highest-value rows) are right-aligned to column 20, rows 3-14 are
left-aligned to column 0 - this is the actual printed shape, not a guess
(verified by which columns are shared between adjacent rows).
"""
import json
import os
import sys

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from app.data.stock_market import STOCK_MARKET_CELLS, _ROWS  # noqa: E402

DOCS = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

TOTAL_COLS = len(_ROWS[3])  # 21: the widest row sets the shared column space


def build_cells():
    cells = []
    for c in STOCK_MARKET_CELLS:
        row_len = len(_ROWS[c.row])
        disp_col = c.col + (TOTAL_COLS - row_len) if c.row in (0, 1, 2) else c.col
        cells.append({"row": c.row, "col": disp_col, "value": c.value, "zone": c.zone, "gameEnd": c.game_end})
    return cells


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>1822 &mdash; Stock Market</title>
<style>
  body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #20201d; }}
  .page {{ box-sizing: border-box; padding: 24px; display: inline-block; }}
  .heading {{ color: #f2ead9; font-size: 20px; font-weight: 700; margin-bottom: 12px; }}
  .grid {{ position: relative; }}
  .cell {{
    position: absolute; width: 44px; height: 30px; box-sizing: border-box;
    border: 1px solid #999; background: #fff; font-size: 11px; color: #111;
    display: flex; align-items: center; justify-content: center; font-weight: 600;
  }}
  .cell.yellow {{ background: #f3e26a; }}
  .cell.start {{ border: 2px solid #c0392b; background: #fff; }}
  .cell.minor_start {{ background: #c0392b; color: #fff; }}
  .cell.gameend {{ box-shadow: inset 0 0 0 2px #111; }}
  .legend {{ margin-top: 14px; display: flex; gap: 18px; color: #f2ead9; font-size: 11px; }}
  .swatch {{ display: inline-block; width: 14px; height: 14px; vertical-align: middle; margin-right: 4px; border: 1px solid #999; }}
</style>
</head>
<body>
<div class="page">
  <div class="heading">1822 &mdash; Stock Market</div>
  <div class="grid" id="grid" style="width:{grid_w}px; height:{grid_h}px;"></div>
  <div class="legend">
    <span><span class="swatch" style="background:#f3e26a"></span>Certificate-limit exempt</span>
    <span><span class="swatch" style="border:2px solid #c0392b"></span>Major/minor start (£60-£100)</span>
    <span><span class="swatch" style="background:#c0392b"></span>Minor-only start (£50)</span>
    <span><span class="swatch" style="box-shadow:inset 0 0 0 2px #111"></span>Game end (£700)</span>
  </div>
</div>
<script>
const CELLS = {cells_json};
const CW = 46, CH = 32;
const grid = document.getElementById('grid');
for (const c of CELLS) {{
  const el = document.createElement('div');
  let cls = 'cell';
  if (c.zone) cls += ' ' + c.zone;
  if (c.gameEnd) cls += ' gameend';
  el.className = cls;
  el.style.left = (c.col * CW) + 'px';
  el.style.top = (c.row * CH) + 'px';
  el.textContent = c.value;
  el.setAttribute('data-id', `r${{c.row}}c${{c.col}}`);
  grid.appendChild(el);
}}
</script>
</body>
</html>
"""


def main():
    cells = build_cells()
    max_col = max(c["col"] for c in cells)
    max_row = max(c["row"] for c in cells)
    grid_w = (max_col + 1) * 46
    grid_h = (max_row + 1) * 32
    html = TEMPLATE.format(cells_json=json.dumps(cells), grid_w=grid_w, grid_h=grid_h)
    out_path = os.path.join(DOCS, "stock-market-board.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"Wrote {out_path} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
