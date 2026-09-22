"""Runtime track-tile board state: which tile sits on which hex, at what
rotation, and what station tokens occupy its city/town slots. Shared
foundation for tile placement (this module's validation) and route-tracing
(Task #5), since both need to know "what track actually connects to what"
on a laid tile.

Rotation convention: `rotation` is how many 60-degree clockwise steps have
been applied to a tile's default (as-drawn) orientation - so an edge `e` in
the tile's spec sits at board edge `(e + rotation) % 6` once placed. Edge
numbering matches app.data.tiles / app.engine.hex_grid (0=top/N ... 5=NW).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.data.hex_map import CITIES, TERRAIN_HEXES
from app.data.phases import PHASES_BY_NUMBER, TileColor
from app.data.tiles import TILE_SPECS, TILE_SPECS_BY_ID, UNLIMITED, ParsedTile, parse_tile_code

COLOR_ORDER = ["yellow", "green", "brown", "gray"]
_MAX_COLOR_INDEX = {
    TileColor.YELLOW: 0, TileColor.GREEN: 1, TileColor.BROWN: 2, TileColor.GREY: 3,
}


class TileLayError(Exception):
    pass


@dataclass
class PlacedTile:
    tile_id: str
    rotation: int  # 0-5
    tokens: dict[int, str] = field(default_factory=dict)  # lot index -> company_id


@dataclass
class BoardState:
    tiles: dict[str, PlacedTile] = field(default_factory=dict)
    # remaining count per tile id; None means unlimited (tiles #7/#8/#9, rule 5.7.21)
    tile_pool: dict[str, int | None] = field(default_factory=dict)


def new_board_state() -> BoardState:
    pool: dict[str, int | None] = {}
    for spec in TILE_SPECS:
        pool[spec.id] = None if spec.count == UNLIMITED else spec.count
    return BoardState(tile_pool=pool)


def _parsed(tile_id: str) -> ParsedTile:
    spec = TILE_SPECS_BY_ID[tile_id]
    return parse_tile_code(spec.id, spec.color, spec.count, spec.code)


def rotated_edges_used(parsed: ParsedTile, rotation: int) -> set[int]:
    edges: set[int] = set()
    for c in parsed.cities:
        edges.update((e + rotation) % 6 for e in c.edges)
    for t in parsed.towns:
        edges.update((e + rotation) % 6 for e in t.edges)
    for a, b in parsed.plain_paths:
        edges.add((a + rotation) % 6)
        edges.add((b + rotation) % 6)
    edges.update((e + rotation) % 6 for e in parsed.junction_edges)
    return edges


def connection_pairs(parsed: ParsedTile, rotation: int) -> set[frozenset[int]]:
    """Every pair of board edges that are connected through this tile (at
    this rotation) - i.e. a train could travel between them. Cities/towns
    connect all of their own edges pairwise (any track entering a city can
    exit toward any other edge of that same city); a plain path connects
    exactly its two edges; a junction's edges (rule: an implicit crossing
    with no city/town, see app.data.tiles) are treated as mutually
    connected too - a simplification for simple/compound crossing tiles
    that doesn't model turn restrictions a physical crossing might impose."""
    pairs: set[frozenset[int]] = set()

    def add_all_pairs(edges: list[int]) -> None:
        rotated = [(e + rotation) % 6 for e in edges]
        for i in range(len(rotated)):
            for j in range(i + 1, len(rotated)):
                pairs.add(frozenset((rotated[i], rotated[j])))

    for c in parsed.cities:
        add_all_pairs(c.edges)
    for t in parsed.towns:
        add_all_pairs(t.edges)
    for a, b in parsed.plain_paths:
        pairs.add(frozenset(((a + rotation) % 6, (b + rotation) % 6)))
    add_all_pairs(parsed.junction_edges)
    return pairs


def _next_color_ok(old_color: str | None, new_color: str) -> bool:
    if old_color is None:
        return new_color == "yellow"
    return COLOR_ORDER.index(new_color) == COLOR_ORDER.index(old_color) + 1


### Known limitations (not yet handled by validate_tile_lay):
# - Pre-printed cities (labels BM, Y, C, EC - rule 5.7.13) start with the
#   city already on the map hex and NO yellow tile ever placed there; their
#   first real tile lay is a GREEN upgrade. This function currently assumes
#   every hex starts blank and demands yellow first, which is wrong for
#   those hexes - needs a "pre-printed" flag per hex before this is correct.
# - S/T-labelled hexes use an *unlabeled* yellow tile "as if unlabelled"
#   (rule 5.7.12), only becoming genuinely S/T-labelled at green+. The
#   label-match check here is strict and doesn't yet encode that exemption.


def validate_tile_lay(
    board: BoardState,
    phase: int,
    hex_id: str,
    tile_id: str,
    rotation: int,
    company_kind: str = "major",  # "major" | "minor" - minors can never upgrade past green (rule 3.2.7)
) -> int:
    """Raises TileLayError if illegal; otherwise returns the terrain cost
    (rule 5.7.18, paid only on the hex's first tile lay) the caller must
    deduct from the laying company's treasury."""
    spec = TILE_SPECS_BY_ID.get(tile_id)
    if spec is None:
        raise TileLayError(f"Unknown tile id {tile_id!r}.")
    if not (0 <= rotation <= 5):
        raise TileLayError("Rotation must be 0-5.")

    phase_def = PHASES_BY_NUMBER[phase]
    max_idx = _MAX_COLOR_INDEX[phase_def.max_tile_color]
    if COLOR_ORDER.index(spec.color) > max_idx:
        raise TileLayError(f"{spec.color} tiles are not available yet (phase {phase}).")
    if company_kind == "minor" and COLOR_ORDER.index(spec.color) > COLOR_ORDER.index("green"):
        raise TileLayError("Minor companies may never upgrade track past green (rule 3.2.7).")

    remaining = board.tile_pool.get(tile_id)
    if remaining is not None and remaining <= 0:
        raise TileLayError(f"No {tile_id} tiles remain in the supply.")

    parsed = parse_tile_code(spec.id, spec.color, spec.count, spec.code)
    existing = board.tiles.get(hex_id)

    if existing is None:
        if spec.color != "yellow":
            raise TileLayError("The first tile placed on a hex must be yellow.")
    else:
        old_spec = TILE_SPECS_BY_ID[existing.tile_id]
        if not _next_color_ok(old_spec.color, spec.color):
            raise TileLayError(f"Cannot upgrade {old_spec.color} directly to {spec.color} (must go one step at a time).")
        old_parsed = _parsed(existing.tile_id)
        old_pairs = connection_pairs(old_parsed, existing.rotation)
        new_pairs = connection_pairs(parsed, rotation)
        if not old_pairs.issubset(new_pairs):
            raise TileLayError("Upgrade must preserve every route the previous tile had (rule 5.7.16).")

    catalogued = next((c for c in CITIES if c.id == hex_id), None)
    if catalogued is not None:
        wanted_label = catalogued.label
        if (parsed.label or None) != (wanted_label or None):
            raise TileLayError(
                f"Tile label {parsed.label!r} does not match this hex's label {wanted_label!r} (rule 5.7.11)."
            )

    terrain = next((t for t in TERRAIN_HEXES if t.id == hex_id), None)
    cost = terrain.cost if (terrain is not None and existing is None) else 0
    return cost


def tile_lay_report(
    board: BoardState, phase: int, hex_id: str, company_kind: str = "major",
) -> list[dict]:
    """Every (tile, rotation) combination's legality for a lay on this hex
    right now, computed by literally calling validate_tile_lay for each of
    the 61 tiles x 6 rotations - so this can never drift out of sync with
    what an actual lay would accept or reject. Used to drive the map UI's
    "what can I place here" prompt: one call gets the full grid so rotating
    the tile in the UI afterwards is a free client-side lookup, no refetch."""
    report = []
    for spec in TILE_SPECS:
        for rotation in range(6):
            try:
                cost = validate_tile_lay(board, phase, hex_id, spec.id, rotation, company_kind)
                report.append({
                    "tile_id": spec.id, "rotation": rotation, "valid": True, "cost": cost, "reason": None,
                })
            except TileLayError as e:
                report.append({
                    "tile_id": spec.id, "rotation": rotation, "valid": False, "cost": None, "reason": str(e),
                })
    return report


def apply_tile_lay(board: BoardState, hex_id: str, tile_id: str, rotation: int) -> None:
    """Mutates the board - call only after validate_tile_lay succeeds."""
    existing = board.tiles.get(hex_id)
    if existing is not None:
        old_remaining = board.tile_pool.get(existing.tile_id)
        if old_remaining is not None:
            board.tile_pool[existing.tile_id] = old_remaining + 1  # returned to supply
        # Station tokens on the old tile are NOT auto-carried to the new tile's
        # lot indices here - remapping tokens across an upgrade is deferred to
        # Task #6 (it needs the operating-round context to know which company
        # owns which token).

    remaining = board.tile_pool.get(tile_id)
    if remaining is not None:
        board.tile_pool[tile_id] = remaining - 1

    board.tiles[hex_id] = PlacedTile(tile_id=tile_id, rotation=rotation)
