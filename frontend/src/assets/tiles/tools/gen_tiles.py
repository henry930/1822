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


APOTHEM = R * math.sqrt(3) / 2  # hex center -> edge midpoint
CASING_W = TRACK_W + 7           # white outline drawn under every rail
TOWN_R = 13                      # town dot radius
BUBBLE_R = 14                    # revenue bubble radius
SLOT_R = 17                      # city station-slot radius


def edge_mid(e):
    """Midpoint of hex edge e - where track enters/leaves the tile."""
    return edge_point(e, APOTHEM)


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


class EdgeTrack:
    """Track running between two hex edges: a straight line when the edges
    are opposite, otherwise a circular arc (sharp curve for adjacent edges,
    gentle curve for edges two apart) - the standard 18xx track shapes."""

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.p1, self.p2 = edge_mid(a), edge_mid(b)
        sep = min((a - b) % 6, (b - a) % 6)
        self.arc = None
        if sep in (1, 2):
            r = R / 2 if sep == 1 else R * 1.5
            mx, my = (self.p1[0] + self.p2[0]) / 2, (self.p1[1] + self.p2[1]) / 2
            m = math.hypot(mx, my)
            ux, uy = mx / m, my / m
            h = math.dist(self.p1, self.p2) / 2
            t = math.sqrt(r * r - h * h)
            cx, cy = mx + ux * t, my + uy * t  # circle center lies outside, away from hex center
            a1 = math.atan2(self.p1[1] - cy, self.p1[0] - cx)
            a2 = math.atan2(self.p2[1] - cy, self.p2[0] - cx)
            d = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi  # short way round
            self.arc = (cx, cy, r, a1, d)

    def point(self, t):
        if self.arc is None:
            return (self.p1[0] + (self.p2[0] - self.p1[0]) * t,
                    self.p1[1] + (self.p2[1] - self.p1[1]) * t)
        cx, cy, r, a1, d = self.arc
        ang = a1 + d * t
        return (cx + r * math.cos(ang), cy + r * math.sin(ang))

    def d(self):
        (x1, y1), (x2, y2) = self.p1, self.p2
        if self.arc is None:
            return f"M {x1:.2f},{y1:.2f} L {x2:.2f},{y2:.2f}"
        _, _, r, _, d = self.arc
        sweep = 1 if d > 0 else 0
        return f"M {x1:.2f},{y1:.2f} A {r:.2f},{r:.2f} 0 0 {sweep} {x2:.2f},{y2:.2f}"

    def samples(self, n=24):
        return [self.point(i / n) for i in range(n + 1)]


def _seg_samples(p1, p2, n=12):
    return [(p1[0] + (p2[0] - p1[0]) * i / n, p1[1] + (p2[1] - p1[1]) * i / n) for i in range(n + 1)]


def _inside_hex(x, y, margin):
    # flat-top hex: |y| <= apothem, and the slanted sides
    a = APOTHEM - margin
    return abs(y) <= a and (abs(x) * math.sqrt(3) / 2 + abs(y) / 2) <= a


def render_tile(tile: Tile) -> str:
    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-115 -115 230 230" '
        f'width="230" height="230">'
    )
    fill = COLORS[tile.color]
    svg.append(f'<path d="{hex_path()}" fill="{fill}" stroke="{STROKE}" stroke-width="3"/>')

    # Each "layer" is a group of rail paths drawn casing-first then black, so
    # rails that merge at a point join cleanly while a later layer visibly
    # crosses *over* an earlier one (two-rail overlap tiles like #55/#56/#69).
    layers = []           # list of list-of-path-d
    obstacles = []        # sampled points of every rail, for label placement
    town_marks = []       # (x, y, revenue)
    spoke_layer = []

    # Plain edge-to-edge track (no lot).
    for a, b in tile.plain_paths:
        tr = EdgeTrack(a, b)
        layers.append([tr.d()])
        obstacles += tr.samples()

    # Towns on a single through-track (exactly two exits) sit ON that track -
    # straight, sharp or gentle curve - rather than bending it via the center.
    through_towns = [t for t in tile.towns if len(t["edges"]) == 2]
    through_tracks = [EdgeTrack(*t["edges"]) for t in through_towns]
    for tr in through_tracks:
        layers.append([tr.d()])
        obstacles += tr.samples()
    placed = []
    for i, (town, tr) in enumerate(zip(through_towns, through_tracks)):
        others = [p for j, o in enumerate(through_tracks) if j != i for p in o.samples(48)]
        others += [p for a, b in tile.plain_paths for p in EdgeTrack(a, b).samples(48)]
        best, best_score = tr.point(0.5), -1
        for t in (0.5, 0.42, 0.58, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75):
            p = tr.point(t)
            clear = min([math.dist(p, q) for q in others + placed] or [999])
            if clear >= 34:
                best = p
                break
            if clear > best_score:
                best, best_score = p, clear
        placed.append(best)
        town_marks.append((best[0], best[1], town["revenue"]))

    # Everything else: rails from each edge straight in to a lot (cities,
    # towns with 3+ exits, and plain junctions), drawn as one merged layer.
    single_lot = (len(tile.cities) + len(tile.towns)) == 1
    city_positions = []
    for c in tile.cities:
        pos = (0.0, 0.0) if single_lot else lot_center(c["edges"])
        city_positions.append((c, pos))
        for e in c["edges"]:
            p1 = edge_mid(e)
            spoke_layer.append(f"M {p1[0]:.2f},{p1[1]:.2f} L {pos[0]:.2f},{pos[1]:.2f}")
            obstacles += _seg_samples(p1, pos)
    for t in tile.towns:
        if len(t["edges"]) == 2:
            continue
        pos = (0.0, 0.0) if single_lot else lot_center(t["edges"])
        for e in t["edges"]:
            p1 = edge_mid(e)
            spoke_layer.append(f"M {p1[0]:.2f},{p1[1]:.2f} L {pos[0]:.2f},{pos[1]:.2f}")
            obstacles += _seg_samples(p1, pos)
        town_marks.append((pos[0], pos[1], t["revenue"]))
    for e in tile.junction_edges:
        p1 = edge_mid(e)
        spoke_layer.append(f"M {p1[0]:.2f},{p1[1]:.2f} L 0,0")
        obstacles += _seg_samples(p1, (0.0, 0.0))
    if spoke_layer:
        layers.insert(0, spoke_layer)

    for layer in layers:
        for d in layer:
            svg.append(f'<path d="{d}" fill="none" stroke="white" stroke-width="{CASING_W}" stroke-linecap="butt"/>')
        for d in layer:
            svg.append(f'<path d="{d}" fill="none" stroke="{STROKE}" stroke-width="{TRACK_W}" stroke-linecap="butt"/>')
    if spoke_layer:
        # round off the hub where spokes meet so it reads as one joint
        hubs = {(0.0, 0.0)} if (tile.junction_edges or single_lot) else set()
        for hx, hy in hubs:
            svg.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="{TRACK_W / 2:.2f}" fill="{STROKE}"/>')

    # Cities: small station-slot circles laid out like the printed tiles
    # (1 circle, a pair, a triangle of 3, a 2x2 square of 4) on a white
    # backing. Nothing is printed inside them - revenue goes in a bubble.
    blockers = []  # (x, y, radius) round areas labels must stay clear of
    for info, (cx, cy) in city_positions:
        slots = info["slots"]
        s = SLOT_R
        offs = {
            1: [(0, 0)],
            2: [(-s, 0), (s, 0)],
            3: [(-s, -s * 0.577), (s, -s * 0.577), (0, s * 1.155)],
        }.get(slots, [(-s, -s), (s, -s), (s, s), (-s, s)])
        centers = [(cx + dx, cy + dy) for dx, dy in offs]
        backing = ""
        if len(centers) > 1:
            pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in centers)
            backing = f'<polygon points="{pts}" fill="white" stroke-linejoin="round"'
        # outline pass (thick black), then white fill pass, then slot rims
        if backing:
            svg.append(backing + f' stroke="{STROKE}" stroke-width="{2 * s + 6}"/>')
        for x, y in centers:
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{s + 3}" fill="{STROKE}"/>')
        if backing:
            svg.append(backing + f' stroke="white" stroke-width="{2 * s}"/>')
        for x, y in centers:
            svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{s}" fill="white"/>')
        if len(centers) > 1:
            for x, y in centers:
                svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{s - 2}" fill="none" stroke="#666" stroke-width="1.5"/>')
        blockers += [(x, y, s + 3) for x, y in centers]

    # Towns: a bold black dot (white-ringed so it stands out on the rail).
    for tx, ty, _ in town_marks:
        svg.append(f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="{TOWN_R}" fill="{STROKE}" stroke="white" stroke-width="3"/>')
        blockers.append((tx, ty, TOWN_R + 2))

    def clear_spot(anchor, radius, dists):
        """Spot near `anchor` that keeps a `radius` label furthest clear of
        every rail, city, town and already-placed label (never on a line)."""
        ax, ay = anchor
        best, best_score = anchor, -1e9
        for dist in dists:
            for k in range(1 if dist == 0 else 36):
                ang = 2 * math.pi * k / 36
                x, y = ax + dist * math.cos(ang), ay + dist * math.sin(ang)
                if not _inside_hex(x, y, radius + 3):
                    continue
                clear = min([math.dist((x, y), q) - CASING_W / 2 for q in obstacles] or [99])
                clear = min([clear] + [math.dist((x, y), (bx, by)) - br for bx, by, br in blockers])
                score = min(clear - radius, 6) - dist * 0.04  # room first, then stay close
                if score > best_score:
                    best, best_score = (x, y), score
        blockers.append((best[0], best[1], radius))
        return best

    def bubble(pos, text):
        x, y = pos
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{BUBBLE_R}" fill="white" stroke="{STROKE}" stroke-width="2"/>')
        size = 13 if len(str(text)) >= 3 else 15
        svg.append(
            f'<text x="{x:.2f}" y="{y + size * 0.36:.2f}" font-family="Georgia, serif" font-size="{size}" '
            f'font-weight="bold" text-anchor="middle" fill="#111">{text}</text>'
        )

    # Revenue bubbles. Cities that all pay the same (London's six stations)
    # share one bubble in the middle of the tile.
    city_revs = {c["revenue"] for c, _ in city_positions}
    if len(city_positions) > 1 and len(city_revs) == 1 and None not in city_revs:
        bubble(clear_spot((0.0, 0.0), BUBBLE_R, (0, 8, 16)), city_revs.pop())
    else:
        for info, (cx, cy) in city_positions:
            if info["revenue"] is not None:
                dists = [SLOT_R * (1 + 0.577 * (info["slots"] >= 3)) + 3 + BUBBLE_R + d for d in (0, 5, 10, 16, 24)]
                bubble(clear_spot((cx, cy), BUBBLE_R, dists), info["revenue"])
    for tx, ty, rev in town_marks:
        if rev is not None:
            bubble(clear_spot((tx, ty), BUBBLE_R, (30, 36, 42, 50)), rev)

    # Label (city-type marker e.g. Y, C, BM, S, EC, L, T), in open space.
    if tile.label:
        lr = 9 + 6 * len(tile.label)
        lx, ly = clear_spot((0.0, 0.0), lr, (45, 52, 58, 64))
        svg.append(
            f'<text x="{lx:.2f}" y="{ly + 8:.2f}" font-family="Georgia, serif" font-size="22" '
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
