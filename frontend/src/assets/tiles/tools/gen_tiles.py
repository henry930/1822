"""Generate clean vector (SVG) hex track tiles for 1822, from tile track/city
specs (not from cropping rail_track.jpg). Track topology + revenue values are
the public 1822 tile manifest (same numbering used by the open-source 18xx.games
rules engine); colors/style are standard 18xx tile-art conventions.
"""
import math
import os
import re

OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
os.makedirs(OUT_DIR, exist_ok=True)

R = 100.0  # hex circumradius in local SVG units
COLORS = {
    "yellow": "#F5DD62",
    "green": "#6FAE5D",
    "brown": "#C17A3D",
    "gray": "#ABABAB",
}
STROKE = "#1a1a1a"
TRACK_W = 13

def deg2rad(d):
    return d * math.pi / 180.0

def edge_angle(e):
    # e=0 -> top flat edge, clockwise: 1 upper-right, 2 lower-right,
    # 3 bottom flat edge, 4 lower-left, 5 upper-left.
    return 90 - 60 * e

def edge_point(e, r=R):
    a = deg2rad(edge_angle(e))
    return (r * math.cos(a), -r * math.sin(a))

def hex_vertices(r=R):
    pts = []
    for k in range(6):
        a = deg2rad(90 - 60 * k + 30)
        pts.append((r * math.cos(a), -r * math.sin(a)))
    return pts

def hex_path(r=R):
    pts = hex_vertices(r)
    d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
    return d


class Tile:
    def __init__(self, tid, color, code, count):
        self.id = tid
        self.color = color
        self.code = code
        self.count = count
        self.cities = []   # list of dicts: {lot, revenue, slots, edges:[...], loc}
        self.towns = []    # list of dicts: {lot, revenue, edges:[...]}
        self.plain_paths = []  # list of (edgeA, edgeB) direct edge-to-edge track
        self.junction = False
        self.junction_edges = []  # edges that route to an implicit center point (no city/town)
        self.label = None
        self.parse()

    def parse(self):
        parts = self.code.split(";")
        lot_kind = {}   # lot index (int, order of appearance) -> 'city'|'town'
        lot_info = []   # list of dicts in appearance order
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if p == "junction":
                self.junction = True
            elif p.startswith("city="):
                info = {"revenue": None, "slots": 1}
                m = re.search(r"revenue:(\d+)", p)
                if m:
                    info["revenue"] = int(m.group(1))
                m = re.search(r"slots:(\d+)", p)
                if m:
                    info["slots"] = int(m.group(1))
                info["edges"] = []
                lot_info.append(("city", info))
            elif p.startswith("town="):
                info = {"revenue": None}
                m = re.search(r"revenue:(\d+)", p)
                if m:
                    info["revenue"] = int(m.group(1))
                info["edges"] = []
                lot_info.append(("town", info))
            elif p.startswith("path="):
                a_m = re.search(r"a:(_?\d+)", p)
                b_m = re.search(r"b:(_?\d+)", p)
                a, b = a_m.group(1), b_m.group(1)

                def resolve(tok):
                    if tok.startswith("_"):
                        return ("lot", int(tok[1:]))
                    return ("edge", int(tok))

                ra, rb = resolve(a), resolve(b)
                if ra[0] == "edge" and rb[0] == "edge":
                    self.plain_paths.append((ra[1], rb[1]))
                else:
                    for kind, val in (ra, rb):
                        if kind == "edge":
                            other = ra if (ra[0], ra[1]) != (kind, val) else rb
                    # find which side is edge, which is lot
                    if ra[0] == "edge":
                        edge_idx, lot_idx = ra[1], rb[1]
                    elif rb[0] == "edge":
                        edge_idx, lot_idx = rb[1], ra[1]
                    else:
                        edge_idx, lot_idx = None, ra[1]
                    if edge_idx is not None:
                        if lot_idx < len(lot_info):
                            lot_info[lot_idx][1]["edges"].append(edge_idx)
                        else:
                            self.junction_edges.append(edge_idx)
            elif p.startswith("label="):
                self.label = p.split("=", 1)[1]
            # upgrade=, border=, icon= etc: ignored for tile art

        for kind, info in lot_info:
            if kind == "city":
                self.cities.append(info)
            else:
                self.towns.append(info)


def lot_center(edges, inset=0.52):
    if not edges:
        return (0.0, 0.0)
    xs, ys = [], []
    for e in edges:
        x, y = edge_point(e, 1.0)
        xs.append(x)
        ys.append(y)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    norm = math.hypot(mx, my)
    if norm < 1e-6:
        return (0.0, 0.0)
    return (mx / norm * R * inset, my / norm * R * inset)


def render_tile(tile: Tile) -> str:
    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-115 -115 230 230" '
        f'width="230" height="230">'
    )
    fill = COLORS[tile.color]
    svg.append(f'<path d="{hex_path()}" fill="{fill}" stroke="{STROKE}" stroke-width="3"/>')

    # Determine center point(s) for each lot (city/town)
    single_lot = (len(tile.cities) + len(tile.towns)) == 1
    lot_positions = []
    for c in tile.cities:
        pos = (0.0, 0.0) if single_lot else lot_center(c["edges"])
        lot_positions.append(("city", c, pos))
    for t in tile.towns:
        pos = (0.0, 0.0) if single_lot else lot_center(t["edges"])
        lot_positions.append(("town", t, pos))

    def edge_or_lot_point(tok_kind, tok_val):
        if tok_kind == "edge":
            return edge_point(tok_val)
        else:
            return lot_positions[tok_val][2]

    # Track: plain edge-to-edge paths (bezier through hex center)
    for a, b in tile.plain_paths:
        p1 = edge_point(a)
        p2 = edge_point(b)
        svg.append(
            f'<path d="M {p1[0]:.2f},{p1[1]:.2f} Q 0,0 {p2[0]:.2f},{p2[1]:.2f}" '
            f'fill="none" stroke="{STROKE}" stroke-width="{TRACK_W}" stroke-linecap="round"/>'
        )

    # Track: edge-to-lot stubs, one per (lot, edge)
    for kind, info, pos in lot_positions:
        for e in info["edges"]:
            p1 = edge_point(e)
            svg.append(
                f'<path d="M {p1[0]:.2f},{p1[1]:.2f} L {pos[0]:.2f},{pos[1]:.2f}" '
                f'fill="none" stroke="{STROKE}" stroke-width="{TRACK_W}" stroke-linecap="round"/>'
            )

    # Track: junction stubs (edge routed straight to an implicit center point)
    for e in tile.junction_edges:
        p1 = edge_point(e)
        svg.append(
            f'<path d="M {p1[0]:.2f},{p1[1]:.2f} L 0,0" '
            f'fill="none" stroke="{STROKE}" stroke-width="{TRACK_W}" stroke-linecap="round"/>'
        )

    # Junction dot (plain track crossing point, no city/town)
    if tile.junction_edges:
        svg.append(f'<circle cx="0" cy="0" r="7" fill="{STROKE}"/>')

    # Draw cities (white circle(s) + revenue) and towns (small black dot)
    for kind, info, pos in lot_positions:
        cx, cy = pos
        if kind == "city":
            slots = info["slots"]
            cr = 30
            if slots <= 1:
                svg.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{cr}" fill="white" stroke="{STROKE}" stroke-width="4"/>')
            else:
                spacing = cr * 1.3
                width = 2 * cr + (slots - 1) * spacing
                svg.append(
                    f'<rect x="{cx - width / 2:.2f}" y="{cy - cr:.2f}" width="{width:.2f}" height="{2 * cr:.2f}" '
                    f'rx="{cr}" ry="{cr}" fill="white" stroke="{STROKE}" stroke-width="4"/>'
                )
                start = -(slots - 1) / 2.0
                for i in range(1, slots):
                    dx = cx + (start + i - 0.5) * spacing
                    svg.append(
                        f'<line x1="{dx:.2f}" y1="{cy - cr + 6:.2f}" x2="{dx:.2f}" y2="{cy + cr - 6:.2f}" '
                        f'stroke="{STROKE}" stroke-width="2.5"/>'
                    )
            if info["revenue"] is not None:
                svg.append(
                    f'<text x="{cx:.2f}" y="{cy + 6:.2f}" font-family="Georgia, serif" '
                    f'font-size="26" font-weight="bold" text-anchor="middle" fill="#111">{info["revenue"]}</text>'
                )
        else:
            svg.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="10" fill="{STROKE}"/>')
            if info["revenue"] is not None:
                # offset the revenue label away from hex center so it doesn't collide with track
                norm = math.hypot(cx, cy)
                if norm > 1e-6:
                    lx, ly = cx / norm * (norm + 26), cy / norm * (norm + 26)
                else:
                    lx, ly = cx, cy - 26
                svg.append(
                    f'<text x="{lx:.2f}" y="{ly + 6:.2f}" font-family="Georgia, serif" '
                    f'font-size="20" text-anchor="middle" fill="#111">{info["revenue"]}</text>'
                )

    # Label (city name-type marker e.g. Y, C, BM, S, EC, L, T)
    if tile.label:
        svg.append(
            f'<text x="0" y="-58" font-family="Georgia, serif" font-size="22" '
            f'font-weight="bold" text-anchor="middle" fill="#111">{tile.label}</text>'
        )

    # Tile id, bottom-left corner
    svg.append(
        f'<text x="-92" y="98" font-family="Arial, sans-serif" font-size="20" '
        f'fill="#333">{tile.id}</text>'
    )

    svg.append("</svg>")
    return "\n".join(svg)


# ---------------------------------------------------------------------------
# The 1822 tile manifest: (id, color, count, code). This is now sourced from
# backend/app/data/tiles.py (the canonical, tested definition shared with the
# rules engine) rather than duplicated here - edit TILE_SPECS in that module
# and re-run this script to regenerate the SVGs/manifest.json.
# ---------------------------------------------------------------------------
import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[5]
_sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.data.tiles import TILE_SPECS as _TILE_SPECS  # noqa: E402
from app.data.tiles import UNLIMITED as _UNLIMITED  # noqa: E402

TILES = [
    (t.id, t.color, 999 if t.count == _UNLIMITED else t.count, t.code)
    for t in _TILE_SPECS
]

def main():
    manifest = []
    for tid, color, count, code in TILES:
        tile = Tile(tid, color, code, count)
        svg_content = render_tile(tile)
        fname = f"tile_{tid}.svg"
        with open(os.path.join(OUT_DIR, fname), "w") as f:
            f.write(svg_content + "\n")
        manifest.append({
            "id": tid,
            "color": color,
            "count": count if count != 999 else "unlimited",
            "label": tile.label,
            "file": fname,
        })

    import json
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(TILES)} tiles into {OUT_DIR}")


if __name__ == "__main__":
    main()
