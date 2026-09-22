from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
            # v1: inbound game actions will be handled here once the rules engine
            # exposes an apply_action(state, player_id, action) entry point.
            await websocket.receive_text()
    except WebSocketDisconnect:
        room.connections.pop(player_id, None)
        for p in room.lobby_players:
            if p.player_id == player_id:
                p.connected = False
        await room.broadcast()
