"""In-memory game room / lobby management and WebSocket broadcast fan-out.

This is intentionally simple (single-process, in-memory) for v1. A room holds a lobby
of connected players before the game starts, and the live GameState once it has.
"""
from __future__ import annotations

import dataclasses
import json
import uuid
from dataclasses import dataclass, field, is_dataclass
from enum import Enum

from fastapi import WebSocket

from app.engine.models import GameState
from app.engine.setup import new_game


def _json_default(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_state(state: GameState) -> str:
    return json.dumps(dataclasses.asdict(state), default=_json_default)


@dataclass
class LobbyPlayer:
    player_id: str
    name: str
    connected: bool = False


@dataclass
class Room:
    room_id: str
    lobby_players: list[LobbyPlayer] = field(default_factory=list)
    started: bool = False
    state: GameState | None = None
    connections: dict[str, WebSocket] = field(default_factory=dict)

    async def broadcast(self) -> None:
        if self.state is None:
            payload = json.dumps({
                "type": "lobby",
                "room_id": self.room_id,
                "players": [dataclasses.asdict(p) for p in self.lobby_players],
                "started": self.started,
            })
        else:
            payload = json.dumps({
                "type": "state",
                "state": json.loads(serialize_state(self.state)),
            })
        stale = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(pid)
        for pid in stale:
            self.connections.pop(pid, None)

    def start(self) -> None:
        if self.started:
            return
        names = [p.name for p in self.lobby_players]
        self.state = new_game(game_id=self.room_id, player_names=names)
        self.started = True


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create_room(self) -> Room:
        room_id = uuid.uuid4().hex[:8]
        room = Room(room_id=room_id)
        self._rooms[room_id] = room
        return room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)


registry = RoomRegistry()
