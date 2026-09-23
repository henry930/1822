from __future__ import annotations

import json
import re
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.data.hex_map import CITIES, HEX_COLUMNS, OFFBOARD_AREAS, TERRAIN_HEXES
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
        cities.append({
            "id": c.id, "name": c.name, "label": c.label, "is_town": c.is_town,
            "home_of_minor": c.home_of_minor, "home_of_major": c.home_of_major,
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

    return {"columns": list(HEX_COLUMNS), "cities": cities, "offboard": offboard, "terrain": terrain}


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
    return {"hex_id": hex_id, "phase": room.state.phase, "company_kind": company_kind, "report": report}


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

        director = req.player_id or company.director_player_id or (state.player_order[0] if state.player_order else None)
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
    await room.broadcast()
    return {"status": "started"}


@app.websocket("/ws/{room_id}/{player_id}")
async def ws_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    room = registry.get(room_id)
    if room is None:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    room.connections[player_id] = websocket
    for p in room.lobby_players:
        if p.player_id == player_id:
            p.connected = True
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
        await room.broadcast()
