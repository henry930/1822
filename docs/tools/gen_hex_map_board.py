"""Render the catalogued hex map (backend/app/data/hex_map.py) as a standalone
HTML page.

IMPORTANT CAVEAT: this only plots the *named/catalogued* hexes (cities, towns,
off-board areas, terrain-cost hexes - ~90 entries), not the full board (which
has several hundred hexes including blank land/sea - see hex_map.py's module
docstring). The column-offset stagger direction (whether odd columns shift up
or down half a hex relative to even columns) is a best-effort visual choice,
not verified against the physical board - use this for a rough reference
layout, not for exact adjacency/routing logic.
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from app.data.hex_map import CITIES, HEX_COLUMNS, OFFBOARD_AREAS, TERRAIN_HEXES  # noqa: E402

DOCS = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

COL_INDEX = {letter: i for i, letter in enumerate(HEX_COLUMNS)}
HEX_ID_RE = re.compile(r"^([A-Q])(\d+)")


def parse_hex_id(hex_id):
    m = HEX_ID_RE.match(hex_id)
    if not m:
        return None
    return COL_INDEX[m.group(1)], int(m.group(2))


def build_points():
    points = []

    def add(hex_id, label, kind, confidence):
        parsed = parse_hex_id(hex_id)
        if parsed is None:
            return
        col, row = parsed
        points.append({
            "id": hex_id, "label": label, "kind": kind,
            "col": col, "row": row, "confidence": confidence,
        })

    for c in CITIES:
        kind = "city" if c.label else ("town" if c.is_town else "city")
        add(c.id, c.name, kind, c.confidence)

    for a in OFFBOARD_AREAS:
        for h in a.hexes:
            add(h, a.name, "offboard", a.confidence)

    for t in TERRAIN_HEXES:
        add(t.id, t.terrain, "terrain", t.confidence)

    return points


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>1822 &mdash; Hex Map (catalogued hexes)</title>
<style>
  body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #16241c; }}
  .page {{ box-sizing: border-box; padding: 24px; display: inline-block; }}
  .heading {{ color: #f2ead9; font-size: 20px; font-weight: 700; margin-bottom: 4px; }}
  .caveat {{ color: #d8c98a; font-size: 12px; max-width: 900px; margin-bottom: 14px; line-height: 1.4; }}
  .map {{ position: relative; }}
  .hex {{
    position: absolute; width: 84px; height: 74px;
    display: flex; align-items: center; justify-content: center; text-align: center;
    font-size: 10px; color: #111; font-weight: 700;
    clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);
  }}
  .hex .txt {{ padding: 2px; line-height: 1.15; }}
  .hex.city {{ background: #e8e2c8; }}
  .hex.town {{ background: #cfe0c8; font-size: 9px; }}
  .hex.offboard {{ background: #b9b9b9; }}
  .hex.terrain {{ background: #d9b285; font-size: 9px; }}
  .hex.approx {{ outline: 2px dashed #c0392b; outline-offset: -2px; }}
  .legend {{ margin-top: 14px; display: flex; gap: 18px; color: #f2ead9; font-size: 11px; flex-wrap: wrap; }}
  .swatch {{ display: inline-block; width: 14px; height: 14px; vertical-align: middle; margin-right: 4px; }}
</style>
</head>
<body>
<div class="page">
  <div class="heading">1822 &mdash; Hex Map (catalogued hexes only)</div>
  <div class="caveat">
    Shows the ~90 named/informational hexes from hex_map.py (cities, towns, off-board areas,
    terrain-cost hexes) - not the full board, which has several hundred hexes including
    blank land/sea not yet catalogued. Hexes outlined in red are "approx" confidence
    (read off the map without a nearby rules-verified anchor - see hex_map.py).
  </div>
  <div class="map" id="map" style="width:{map_w}px; height:{map_h}px;"></div>
  <div class="legend">
    <span><span class="swatch" style="background:#e8e2c8"></span>City</span>
    <span><span class="swatch" style="background:#cfe0c8"></span>Town</span>
    <span><span class="swatch" style="background:#b9b9b9"></span>Off-board area</span>
    <span><span class="swatch" style="background:#d9b285"></span>Terrain-cost hex</span>
    <span><span class="swatch" style="outline:2px dashed #c0392b"></span>Approx confidence</span>
  </div>
</div>
<script>
const POINTS = {points_json};
const HEX_W = 84, HEX_H = 74;
const COL_STEP = HEX_W * 0.75;
const ROW_STEP = HEX_H;
const map = document.getElementById('map');
for (const p of POINTS) {{
  const el = document.createElement('div');
  let cls = 'hex ' + p.kind;
  if (p.confidence === 'approx') cls += ' approx';
  el.className = cls;
  const x = p.col * COL_STEP;
  const y = p.row * ROW_STEP + (p.col % 2 === 1 ? ROW_STEP / 2 : 0);
  el.style.left = x + 'px';
  el.style.top = y + 'px';
  el.setAttribute('data-id', p.id);
  el.innerHTML = `<div class="txt">${{p.id}}<br>${{p.label}}</div>`;
  map.appendChild(el);
}}
</script>
</body>
</html>
"""


def main():
    points = build_points()
    max_col = max(p["col"] for p in points)
    max_row = max(p["row"] for p in points)
    map_w = int((max_col + 1) * 84 * 0.75 + 84)
    map_h = int((max_row + 2) * 74)
    html = TEMPLATE.format(points_json=json.dumps(points), map_w=map_w, map_h=map_h)
    out_path = os.path.join(DOCS, "hex-map-board.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(f"Wrote {out_path} ({len(points)} hexes)")


if __name__ == "__main__":
    main()
