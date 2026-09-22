"""Track tile definitions: the canonical source of truth for tile topology.

This mirrors (and is the source for) frontend/src/assets/tiles/tools/gen_tiles.py,
which renders these into SVGs for the UI. Counts and revenue values are verified
against the rules.pdf Tile Manifest page (400dpi) and the City Upgrade Table;
see that module's README for the cross-check notes. Do not hand-edit
manifest.json or gen_tiles.py's own tile table - edit TILE_SPECS here and
regenerate (see frontend/src/assets/tiles/README.md).

Spec code format (18xx convention):
  city=revenue:R[,slots:N]   - a city lot worth R, with N station slots (default 1)
  town=revenue:R             - a town (dot) lot worth R
  path=a:E,b:_L              - track from hex edge E (0-5, clockwise from top edge)
                                to lot index L (in order of appearance)
  path=a:E1,b:E2             - plain track directly between two edges (no lot)
  junction                   - a plain track crossing with no revenue location
  label=X                    - the tile's printed city-type label (Y/C/S/T/BM/EC/L)
Parts are joined with ";".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

UNLIMITED = "unlimited"


@dataclass(frozen=True)
class TileSpec:
    id: str
    color: str   # "yellow" | "green" | "brown" | "gray"
    count: int | str   # int, or UNLIMITED for tiles #7/#8/#9 (rule 5.7.21)
    code: str


@dataclass
class CityLot:
    index: int
    revenue: int | None
    slots: int
    edges: list[int] = field(default_factory=list)


@dataclass
class TownLot:
    index: int
    revenue: int | None
    edges: list[int] = field(default_factory=list)


@dataclass
class ParsedTile:
    id: str
    color: str
    count: int | str
    label: str | None
    junction: bool
    cities: list[CityLot]
    towns: list[TownLot]
    plain_paths: list[tuple[int, int]]   # direct edge-to-edge track, no lot
    junction_edges: list[int] = field(default_factory=list)  # edges into an implicit center point


def parse_tile_code(tile_id: str, color: str, count: int | str, code: str) -> ParsedTile:
    """Parse a spec code string into structured lots/paths/edges.

    Ported from gen_tiles.py's Tile.parse(), kept in sync deliberately (same
    algorithm) so both the backend engine and the SVG generator read tiles
    identically.
    """
    label: str | None = None
    junction = False
    lot_order: list[tuple[str, CityLot | TownLot]] = []
    plain_paths: list[tuple[int, int]] = []
    junction_edges: list[int] = []

    parts = [p.strip() for p in code.split(";") if p.strip()]
    lot_index = 0
    for p in parts:
        if p == "junction":
            junction = True
        elif p.startswith("label="):
            label = p.split("=", 1)[1]
        elif p.startswith("city="):
            revenue = _int_or_none(re.search(r"revenue:(\d+)", p))
            slots_m = re.search(r"slots:(\d+)", p)
            slots = int(slots_m.group(1)) if slots_m else 1
            lot_order.append(("city", CityLot(index=lot_index, revenue=revenue, slots=slots)))
            lot_index += 1
        elif p.startswith("town="):
            revenue = _int_or_none(re.search(r"revenue:(\d+)", p))
            lot_order.append(("town", TownLot(index=lot_index, revenue=revenue)))
            lot_index += 1
        elif p.startswith("path="):
            a_m = re.search(r"a:(_?\d+)", p)
            b_m = re.search(r"b:(_?\d+)", p)
            a_tok, b_tok = a_m.group(1), b_m.group(1)

            def resolve(tok: str) -> tuple[str, int]:
                if tok.startswith("_"):
                    return ("lot", int(tok[1:]))
                return ("edge", int(tok))

            ra, rb = resolve(a_tok), resolve(b_tok)
            if ra[0] == "edge" and rb[0] == "edge":
                plain_paths.append((ra[1], rb[1]))
            else:
                lot_ref = ra if ra[0] == "lot" else rb
                edge_ref = ra if ra[0] == "edge" else rb
                if lot_ref[1] < len(lot_order):
                    _, kind_obj = lot_order[lot_ref[1]]
                    kind_obj.edges.append(edge_ref[1])
                else:
                    # No actual city/town lot (e.g. a "junction" tile) - the
                    # spec still uses "_0" to mean "route through the implicit
                    # center point", matching gen_tiles.py's fallback.
                    junction_edges.append(edge_ref[1])

    cities = [obj for kind, obj in lot_order if kind == "city"]
    towns = [obj for kind, obj in lot_order if kind == "town"]
    return ParsedTile(
        id=tile_id, color=color, count=count, label=label, junction=junction,
        cities=cities, towns=towns, plain_paths=plain_paths, junction_edges=junction_edges,
    )


def _int_or_none(m: re.Match | None) -> int | None:
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Tile table. Counts verified against rules.pdf Tile Manifest (400dpi read);
# revenue values verified against the City Upgrade Table in hex_map.py.
# Tiles #7/#8/#9 are coded "unlimited" per rule 5.7.21 rather than their
# literal printed counts (6/24/24) - the rule says the supply is not meant
# to limit play.
# ---------------------------------------------------------------------------
TILE_SPECS: list[TileSpec] = [
    # -- yellow --
    TileSpec("1", "yellow", 1, "town=revenue:10;town=revenue:10;path=a:1,b:_0;path=a:_0,b:3;path=a:0,b:_1;path=a:_1,b:4"),
    TileSpec("2", "yellow", 1, "town=revenue:10;town=revenue:10;path=a:0,b:_0;path=a:_0,b:3;path=a:1,b:_1;path=a:_1,b:2"),
    TileSpec("3", "yellow", 6, "town=revenue:10;path=a:0,b:_0;path=a:_0,b:1"),
    TileSpec("4", "yellow", 6, "town=revenue:10;path=a:0,b:_0;path=a:_0,b:3"),
    TileSpec("5", "yellow", 6, "city=revenue:20;path=a:0,b:_0;path=a:1,b:_0"),
    TileSpec("6", "yellow", 8, "city=revenue:20;path=a:0,b:_0;path=a:2,b:_0"),
    TileSpec("7", "yellow", UNLIMITED, "path=a:0,b:1"),
    TileSpec("8", "yellow", UNLIMITED, "path=a:0,b:2"),
    TileSpec("9", "yellow", UNLIMITED, "path=a:0,b:3"),
    TileSpec("55", "yellow", 1, "town=revenue:10;town=revenue:10;path=a:0,b:_0;path=a:_0,b:3;path=a:1,b:_1;path=a:_1,b:4"),
    TileSpec("56", "yellow", 1, "town=revenue:10;town=revenue:10;path=a:0,b:_0;path=a:_0,b:2;path=a:1,b:_1;path=a:_1,b:3"),
    TileSpec("57", "yellow", 6, "city=revenue:20;path=a:0,b:_0;path=a:_0,b:3"),
    TileSpec("58", "yellow", 6, "town=revenue:10;path=a:0,b:_0;path=a:_0,b:2"),
    TileSpec("69", "yellow", 1, "town=revenue:10;town=revenue:10;path=a:0,b:_0;path=a:_0,b:3;path=a:2,b:_1;path=a:_1,b:4"),
    # -- green --
    TileSpec("14", "green", 6, "city=revenue:30,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("15", "green", 6, "city=revenue:30,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0"),
    TileSpec("80", "green", 6, "junction;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0"),
    TileSpec("81", "green", 6, "junction;path=a:0,b:_0;path=a:2,b:_0;path=a:4,b:_0"),
    TileSpec("82", "green", 8, "junction;path=a:0,b:_0;path=a:1,b:_0;path=a:3,b:_0"),
    TileSpec("83", "green", 8, "junction;path=a:0,b:_0;path=a:5,b:_0;path=a:3,b:_0"),
    TileSpec("141", "green", 4, "town=revenue:10;path=a:0,b:_0;path=a:3,b:_0;path=a:1,b:_0"),
    TileSpec("142", "green", 4, "town=revenue:10;path=a:0,b:_0;path=a:5,b:_0;path=a:3,b:_0"),
    TileSpec("143", "green", 4, "town=revenue:10;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0"),
    TileSpec("144", "green", 4, "town=revenue:10;path=a:0,b:_0;path=a:2,b:_0;path=a:4,b:_0"),
    TileSpec("207", "green", 2, "city=revenue:40,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;label=Y"),
    TileSpec("208", "green", 1, "city=revenue:40,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:3,b:_0;path=a:4,b:_0;label=Y"),
    TileSpec("619", "green", 6, "city=revenue:30,slots:2;path=a:0,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("622", "green", 1, "city=revenue:40,slots:2;path=a:0,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;label=Y"),
    TileSpec("405", "green", 3, "city=revenue:40,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:5,b:_0;label=T"),
    TileSpec("X1", "green", 1, "city=revenue:30,slots:3;path=a:1,b:_0;path=a:2,b:_0;path=a:4,b:_0;label=C"),
    TileSpec("X2", "green", 2, "city=revenue:50,slots:3;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;label=BM"),
    TileSpec("X3", "green", 1, "city=revenue:30,slots:2;path=a:1,b:_0;path=a:4,b:_0;label=S"),
    TileSpec("X4", "green", 1, "city=revenue:0;path=a:2,b:_0;path=a:3,b:_0;path=a:5,b:_0;label=EC"),
    TileSpec("X21", "green", 1,
             "city=revenue:60;city=revenue:60;city=revenue:60;city=revenue:60;city=revenue:60;city=revenue:60;"
             "path=a:0,b:_0;path=a:1,b:_1;path=a:2,b:_2;path=a:3,b:_3;path=a:4,b:_4;path=a:5,b:_5;label=L"),
    # -- brown --
    TileSpec("63", "brown", 8, "city=revenue:40,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;path=a:5,b:_0"),
    TileSpec("544", "brown", 6, "junction;path=a:0,b:_0;path=a:1,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("545", "brown", 6, "junction;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0"),
    TileSpec("546", "brown", 8, "junction;path=a:0,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("611", "brown", 4, "city=revenue:40,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("767", "brown", 4, "town=revenue:10;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0"),
    TileSpec("768", "brown", 4, "town=revenue:10;path=a:0,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:5,b:_0"),
    TileSpec("769", "brown", 6, "town=revenue:10;path=a:0,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("X5", "brown", 3, "city=revenue:50,slots:3;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;label=Y"),
    TileSpec("X6", "brown", 1, "city=revenue:40,slots:3;path=a:1,b:_0;path=a:2,b:_0;path=a:4,b:_0;label=C"),
    TileSpec("X7", "brown", 2, "city=revenue:60,slots:4;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;path=a:5,b:_0;label=BM"),
    TileSpec("X8", "brown", 1, "city=revenue:40,slots:2;path=a:1,b:_0;path=a:4,b:_0;label=S"),
    TileSpec("X9", "brown", 1, "city=revenue:0,slots:2;path=a:2,b:_0;path=a:3,b:_0;path=a:5,b:_0;label=EC"),
    TileSpec("X10", "brown", 3, "city=revenue:50,slots:2;path=a:0,b:_0;path=a:1,b:_0;path=a:5,b:_0;label=T"),
    TileSpec("X22", "brown", 1,
             "city=revenue:80;city=revenue:80;city=revenue:80;city=revenue:80;city=revenue:80;city=revenue:80;"
             "path=a:0,b:_0;path=a:1,b:_1;path=a:2,b:_2;path=a:3,b:_3;path=a:4,b:_4;path=a:5,b:_5;label=L"),
    # -- gray --
    TileSpec("60", "gray", 2, "junction;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;path=a:5,b:_0"),
    TileSpec("169", "gray", 2, "junction;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("X11", "gray", 2, "city=revenue:60,slots:3;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;label=Y"),
    TileSpec("X12", "gray", 1, "city=revenue:60,slots:3;path=a:1,b:_0;path=a:2,b:_0;path=a:4,b:_0;label=C"),
    TileSpec("X13", "gray", 2, "city=revenue:80,slots:4;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;path=a:5,b:_0;label=BM"),
    TileSpec("X14", "gray", 1, "city=revenue:60,slots:3;path=a:1,b:_0;path=a:4,b:_0;label=S"),
    TileSpec("X15", "gray", 1, "city=revenue:0,slots:3;path=a:2,b:_0;path=a:3,b:_0;path=a:5,b:_0;label=EC"),
    TileSpec("X16", "gray", 2, "city=revenue:60,slots:3;path=a:0,b:_0;path=a:1,b:_0;path=a:5,b:_0;label=T"),
    TileSpec("X17", "gray", 2, "town=revenue:10;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;path=a:5,b:_0"),
    TileSpec("X18", "gray", 2, "city=revenue:50,slots:3;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0"),
    TileSpec("X19", "gray", 4, "city=revenue:50,slots:3;path=a:0,b:_0;path=a:1,b:_0;path=a:2,b:_0;path=a:3,b:_0;path=a:4,b:_0;path=a:5,b:_0"),
    TileSpec("X23", "gray", 1,
             "city=revenue:100;city=revenue:100;city=revenue:100;city=revenue:100;city=revenue:100;city=revenue:100;"
             "path=a:0,b:_0;path=a:1,b:_1;path=a:2,b:_2;path=a:3,b:_3;path=a:4,b:_4;path=a:5,b:_5;label=L"),
]

TILE_SPECS_BY_ID: dict[str, TileSpec] = {t.id: t for t in TILE_SPECS}


def parsed_tiles() -> dict[str, ParsedTile]:
    return {t.id: parse_tile_code(t.id, t.color, t.count, t.code) for t in TILE_SPECS}
