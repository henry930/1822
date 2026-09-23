from __future__ import annotations

import json
import re
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.data.hex_map import BLOCKED_ADJACENCIES, CITIES, EDGE_TOLLS, HEX_COLUMNS, OFFBOARD_AREAS, TERRAIN_HEXES
from app.engine.actions import ActionError
from app.rooms import LobbyPlayer, registry

app = FastAPI(title="1822 Game Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateRoomResponse(BaseModel):
    room_id: str


class JoinRequest(BaseModel):
    name: str


class JoinResponse(BaseModel):
    player_id: str
    room_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


_COL_INDEX = {letter: i for i, letter in enumerate(HEX_COLUMNS)}
_HEX_ID_RE = re.compile(r"^([A-Z]+)(\d+)([a-z]*)$")


def _lenient_position(hex_id: str) -> dict | None:
    """Best-effort (col, row) for map preview rendering - lenient about the
    'b'-suffixed secondary-town ids (e.g. "E7b") that app.engine.hex_grid's
    strict parser rejects. Returns None for area names that aren't real hex
    ids at all (e.g. "Highlands", "MidWales") - callers should render those
    via their .hexes list instead."""
    m = _HEX_ID_RE.match(hex_id)
    if not m:
        return None
    letters, digits, suffix = m.groups()
    if letters not in _COL_INDEX:
        return None
    col = _COL_INDEX[letters]
    row = int(digits)
    # A lettered-suffix id (e.g. "E7b") is a second town sharing its base
    # hex's coordinates - render it a full hex-step down-right so it's a
    # distinct, clickable hex rather than overlapping its base hex. The
    # frontend's hexCenter() multiplies dx/dy by half the column/row
    # spacing, so 2.0 is one full hex-step (a smaller nudge, like the
    # original 0.35, still left the two hexes close enough to overlap and
    # steal each other's clicks - found via manual play-testing tile
    # placement, where selecting one actually queued a lay on the other).
    nudge = 2.0 if suffix else 0.0
    return {"col": col, "row": row, "dx": nudge, "dy": nudge}


@app.get("/board/map")
def board_map():
    """Static hex-catalog data for the map preview UI - cities, off-board
    areas (exploded to their individual hexes), and terrain hexes, each with
    a best-effort board position. This is reference/preview data, not a
    routing-authoritative full hex grid (see app.engine.hex_grid's module
    docstring) - only the ~90 named/informational hexes are catalogued."""
    cities = []
    for c in CITIES:
        pos = _lenient_position(c.id)
        if pos is None:
            continue
        # Normalized to always be a list client-side (even a single value),
        # since a hex like London/M38 is genuinely home to several companies
        # at once - see CityHex's docstring in app.data.hex_map.
        home_of_minor = list(c.home_of_minor) if isinstance(c.home_of_minor, tuple) else (
            [c.home_of_minor] if c.home_of_minor is not None else []
        )
        home_of_major = list(c.home_of_major) if isinstance(c.home_of_major, tuple) else (
            [c.home_of_major] if c.home_of_major is not None else []
        )
        cities.append({
            "id": c.id, "name": c.name, "label": c.label, "is_town": c.is_town,
            "town_count": c.town_count, "city_count": c.city_count,
            "home_of_minor": home_of_minor, "home_of_major": home_of_major,
            "destination_of_major": c.destination_of_major, "confidence": c.confidence,
            **pos,
        })

    offboard = []
    for area in OFFBOARD_AREAS:
        for hex_id in area.hexes:
            pos = _lenient_position(hex_id)
            if pos is None:
                continue
            offboard.append({
                "id": hex_id, "area_id": area.id, "name": area.name,
                "value_yellow": area.value_yellow, "value_green": area.value_green,
                "value_brown": area.value_brown, "value_grey": area.value_grey,
                "confidence": area.confidence,
                **pos,
            })

    terrain = []
    for t in TERRAIN_HEXES:
        pos = _lenient_position(t.id)
        if pos is None:
            continue
        terrain.append({
            "id": t.id, "terrain": t.terrain, "cost": t.cost, "confidence": t.confidence, **pos,
        })

    blocked_adjacencies = [
        {"hex_a": a, "hex_b": b, "confidence": confidence} for a, b, confidence in BLOCKED_ADJACENCIES
    ]
    edge_tolls = [
        {"hex_a": t.hex_a, "hex_b": t.hex_b, "cost": t.cost, "confidence": t.confidence} for t in EDGE_TOLLS
    ]

    return {
        "columns": list(HEX_COLUMNS), "cities": cities, "offboard": offboard, "terrain": terrain,
        "blocked_adjacencies": blocked_adjacencies, "edge_tolls": edge_tolls,
    }


@app.get("/rooms/{room_id}/tile_lay_options")
def tile_lay_options(room_id: str, hex_id: str, company_kind: str = "major", company_id: str | None = None):
    """Every (tile, rotation) combination's legality for a lay on this hex
    right now, for the room's live game state - drives the map UI's "what
    can I place here" prompt. company_kind should be "minor" or "major"
    (minors can never upgrade past green, rule 3.2.7); defaults to "major"
    (the less restrictive case) when the caller doesn't know which company
    is laying, e.g. when just browsing outside an operating round.

    company_id (e.g. "M24", "GWR"), when given, also gates every tile on
    whether hex_id is actually reachable by that company's track network
    (rule 5.7.9) - a hex nothing connects to shows no legal tiles at all,
    regardless of phase/color. Omit it to browse without that check (e.g.
    outside an operating round, when no company is actually laying)."""
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state is None:
        raise HTTPException(status_code=400, detail="Game has not started")
    if company_kind not in ("minor", "major"):
        raise HTTPException(status_code=400, detail="company_kind must be 'minor' or 'major'")

    from app.engine.board import tile_lay_report
    from app.engine.operating import reachable_hexes_for_tile_lay

    connected = True
    if company_id is not None:
        if company_id not in room.state.minors and company_id not in room.state.majors:
            raise HTTPException(status_code=400, detail=f"Unknown company_id {company_id!r}")
        reachable = reachable_hexes_for_tile_lay(room.state, room.state.board, company_id, company_kind)
        connected = hex_id in reachable

    report = tile_lay_report(room.state.board, room.state.phase, hex_id, company_kind, connected)

    from app.data.phases import PHASES_BY_NUMBER

    max_tile_color = {"yellow": "yellow", "green": "green", "brown": "brown", "grey": "gray"}[
        PHASES_BY_NUMBER[room.state.phase].max_tile_color.name.lower()
    ]

    return {
        "hex_id": hex_id,
        "phase": room.state.phase,
        "company_kind": company_kind,
        "report": report,
        "max_tile_color": max_tile_color,
    }


class DebugForceTileLayRequest(BaseModel):
    hex_id: str
    tile_id: str
    rotation: int
    # Both optional: with company_id, this behaves like a real company lay
    # (connectivity-gated, billed to that company's treasury). Without one,
    # connectivity isn't checked at all (there's no company network to be
    # connected to) and any terrain cost is billed to player_id's personal
    # cash instead - or the room's first player if player_id is omitted too.
    company_id: str | None = None
    company_kind: str = "major"
    player_id: str | None = None


@app.post("/rooms/{room_id}/debug/force_tile_lay")
async def debug_force_tile_lay(room_id: str, req: DebugForceTileLayRequest):
    """Testing/debug only - lays a tile directly onto the board without
    requiring an actual operating round, turn, or director, so the map UI
    can be exercised without playing through a real game first. Every
    board-legality rule is enforced regardless: tile supply, phase/color
    availability, upgrade-must-preserve-track, city/town match, and the
    terrain cost (if any). When company_id is given, connectivity to its
    own track network (rule 5.7.9) is also enforced and the cost is billed
    to its treasury; without one, any hex is a legal target and the cost is
    billed to a player's personal cash instead (rule 5.7.18-20)."""
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state is None:
        raise HTTPException(status_code=400, detail="Game has not started")
    state = room.state
    if req.company_kind not in ("minor", "major"):
        raise HTTPException(status_code=400, detail="company_kind must be 'minor' or 'major'")

    from app.engine.board import TileLayError, apply_tile_lay, validate_tile_lay
    from app.engine.operating import reachable_hexes_for_tile_lay

    if req.company_id is not None:
        if req.company_id not in state.minors and req.company_id not in state.majors:
            raise HTTPException(status_code=400, detail=f"Unknown company_id {req.company_id!r}")
        reachable = reachable_hexes_for_tile_lay(state, state.board, req.company_id, req.company_kind)
        if req.hex_id not in reachable:
            raise HTTPException(
                status_code=400,
                detail=f"{req.hex_id} isn't connected to {req.company_id}'s track network (rule 5.7.9).",
            )

    try:
        cost = validate_tile_lay(
            state.board, state.phase, req.hex_id, req.tile_id, req.rotation, company_kind=req.company_kind
        )
    except TileLayError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # `payer` is whatever object cost gets deducted from - a company's
    # treasury when laying under a company, otherwise a player's personal
    # cash. `balance_attr` names which field on it holds the balance.
    if req.company_id is not None:
        payer = state.minors[req.company_id] if req.company_kind == "minor" else state.majors[req.company_id]
        payer_label = req.company_id
        balance_attr = "treasury"
    else:
        if req.player_id is not None:
            if req.player_id not in state.players:
                raise HTTPException(status_code=400, detail=f"Unknown player_id {req.player_id!r}")
            payer = state.players[req.player_id]
        else:
            payer = next(iter(state.players.values())) if state.players else None
        payer_label = payer.name if payer is not None else "the player"
        balance_attr = "cash"

    payer_balance = getattr(payer, balance_attr) if payer is not None else None
    if payer_balance is not None and cost > payer_balance:
        raise HTTPException(
            status_code=400,
            detail=f"{payer_label} can't afford the £{cost} terrain cost (balance £{payer_balance}; rule 5.7.18-20).",
        )
    if payer is not None:
        setattr(payer, balance_attr, payer_balance - cost)

    apply_tile_lay(state.board, req.hex_id, req.tile_id, req.rotation)

    async with room.action_lock:
        await room.broadcast()
    return {"status": "ok", "hex_id": req.hex_id, "tile_id": req.tile_id, "rotation": req.rotation, "cost": cost}


class DebugRemoveTileRequest(BaseModel):
    hex_id: str


@app.post("/rooms/{room_id}/debug/remove_tile")
async def debug_remove_tile(room_id: str, req: DebugRemoveTileRequest):
    """Testing/debug only - takes a placed tile back off the board and
    returns it to supply. Not a real game action (rule 5.7.16: track is
    never removed once laid) - exists purely so the map UI can be tried
    out repeatedly on the same hex without restarting the room."""
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state is None:
        raise HTTPException(status_code=400, detail="Game has not started")

    from app.engine.board import remove_tile

    removed = remove_tile(room.state.board, req.hex_id)
    if removed is None:
        raise HTTPException(status_code=400, detail=f"No tile placed on {req.hex_id}.")

    async with room.action_lock:
        await room.broadcast()
    return {"status": "ok", "hex_id": req.hex_id, "removed_tile_id": removed.tile_id}


class DebugSetCashRequest(BaseModel):
    player_id: str
    cash: int


@app.post("/rooms/{room_id}/debug/set_cash")
async def debug_set_cash(room_id: str, req: DebugSetCashRequest):
    """Testing/debug only - directly overrides a player's cash (e.g. to
    set up a single-player tile-lay testing room with a specific starting
    budget, rather than whatever new_game's player-count table gives)."""
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state is None:
        raise HTTPException(status_code=400, detail="Game has not started")
    if req.player_id not in room.state.players:
        raise HTTPException(status_code=400, detail=f"Unknown player_id {req.player_id!r}")

    room.state.players[req.player_id].cash = req.cash

    async with room.action_lock:
        await room.broadcast()
    return {"status": "ok", "player_id": req.player_id, "cash": req.cash}


class DebugForceRoundRequest(BaseModel):
    phase: int | None = None
    round_type: str | None = None  # "stock" or "operating"
    company_id: str | None = None  # required when round_type == "operating"
    player_id: str | None = None  # lobby player_id to make director; defaults to the first player


@app.post("/rooms/{room_id}/debug/force_round")
async def debug_force_round(room_id: str, req: DebugForceRoundRequest):
    """Testing/debug only - not a real game action. Jumps straight to a
    given phase and/or round without playing through the bidding that
    would normally get there, so map/tile-lay/operating-round features can
    be exercised without a multi-minute bot playthrough first. Mutates the
    live room state directly and broadcasts the result to every connected
    client, same as a real action would."""
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state is None:
        raise HTTPException(status_code=400, detail="Game has not started")
    state = room.state

    from app.data.phases import PHASES_BY_NUMBER
    from app.engine.models import RoundType
    from app.engine.operating import first_turn_housekeeping
    from app.engine.round_manager import start_stock_round

    if req.phase is not None:
        if req.phase not in PHASES_BY_NUMBER:
            raise HTTPException(status_code=400, detail=f"Unknown phase {req.phase!r}")
        state.phase = req.phase

    if req.round_type == "operating":
        if req.company_id is None:
            raise HTTPException(status_code=400, detail="company_id is required for round_type='operating'")
        if req.company_id in state.minors:
            kind, company = "minor", state.minors[req.company_id]
        elif req.company_id in state.majors:
            kind, company = "major", state.majors[req.company_id]
        else:
            raise HTTPException(status_code=400, detail=f"Unknown company_id {req.company_id!r}")

        # Prefer the caller's explicit player_id, or the first seat in
        # turn order (the human in solo mode - the other two are
        # auto-passed by the frontend), over any director this company
        # already had. A pre-existing director can be a bot seat left over
        # from ordinary stock-round bidding that happened to land on this
        # company before the call; if it's used, the frontend's bot
        # auto-pass effect fires within ~300ms and immediately ends this
        # single-company operating round with a legitimate pass, reverting
        # straight back to a stock round before anyone can act on it.
        director = req.player_id or (state.player_order[0] if state.player_order else None) or company.director_player_id
        if director is None:
            raise HTTPException(status_code=400, detail="No players to assign as director")
        company.director_player_id = director
        company.floated = True
        first_turn_housekeeping(state, state.board, req.company_id, kind)

        state.round_type = RoundType.OPERATING
        state.operating_order = [req.company_id]
        state.current_company_index = 0
    elif req.round_type == "stock":
        start_stock_round(state)
    elif req.round_type is not None:
        raise HTTPException(status_code=400, detail="round_type must be 'stock' or 'operating'")

    async with room.action_lock:
        await room.broadcast()
    return {"status": "ok", "phase": state.phase, "round_type": state.round_type}


@app.post("/rooms", response_model=CreateRoomResponse)
def create_room():
    room = registry.create_room()
    return CreateRoomResponse(room_id=room.room_id)


@app.post("/rooms/{room_id}/join", response_model=JoinResponse)
def join_room(room_id: str, req: JoinRequest):
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.started:
        raise HTTPException(status_code=400, detail="Game already started")
    player_id = uuid.uuid4().hex[:8]
    room.lobby_players.append(LobbyPlayer(player_id=player_id, name=req.name))
    return JoinResponse(player_id=player_id, room_id=room_id)


@app.post("/rooms/{room_id}/start")
async def start_room(room_id: str):
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if len(room.lobby_players) < 3:
        raise HTTPException(status_code=400, detail="1822 requires at least 3 players")
    if len(room.lobby_players) > 7:
        raise HTTPException(status_code=400, detail="1822 supports at most 7 players")
    room.start()
    async with room.action_lock:
        await room.broadcast()
    return {"status": "started"}


@app.websocket("/ws/{room_id}/{player_id}")
async def ws_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    room = registry.get(room_id)
    if room is None:
        # A close before accept() doesn't complete the WS handshake, so the
        # browser only ever sees a generic code-1006 "abnormal closure" -
        # indistinguishable from the server being unreachable at all. Accept
        # first so the real 4404 close code actually reaches the client;
        # otherwise a reconnect loop can never tell "server down, keep
        # retrying" apart from "room gone, stop retrying and say so".
        await websocket.accept()
        await websocket.close(code=4404)
        return
    await websocket.accept()
    room.connections[player_id] = websocket
    for p in room.lobby_players:
        if p.player_id == player_id:
            p.connected = True
    async with room.action_lock:
        await room.broadcast()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                action = json.loads(raw)
            except json.JSONDecodeError:
                await room.send_error(player_id, "Malformed message: expected JSON.")
                continue
            if not isinstance(action, dict) or "type" not in action:
                await room.send_error(player_id, "Malformed action: expected an object with a 'type' field.")
                continue
            async with room.action_lock:
                try:
                    room.apply_action(player_id, action)
                except ActionError as e:
                    await room.send_error(player_id, str(e))
                    continue
                await room.broadcast()
    except WebSocketDisconnect:
        room.connections.pop(player_id, None)
        for p in room.lobby_players:
            if p.player_id == player_id:
                p.connected = False
        async with room.action_lock:
            await room.broadcast()
