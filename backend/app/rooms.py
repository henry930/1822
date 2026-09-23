"""In-memory game room / lobby management and WebSocket broadcast fan-out.

This is intentionally simple (single-process, in-memory) for v1. A room holds a lobby
of connected players before the game starts, and the live GameState once it has.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import uuid
from dataclasses import dataclass, field, is_dataclass
from enum import Enum

from fastapi import WebSocket

from app.engine.actions import ActionError, apply_action
from app.engine.models import GameState
from app.engine.setup import new_game


def _json_default(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _stringify_tuple_keys(value):
    """json.dumps rejects non-str dict keys outright (it never reaches
    `default` for keys, only values) - GameState.stock_stack is keyed by
    (row, col) tuples (see models.py), which crashes serialization the
    moment a company actually floats and gets placed on the stock market
    grid. Recursively rewrite any tuple dict key as "row,col" before
    dumping."""
    if isinstance(value, dict):
        return {
            (",".join(map(str, k)) if isinstance(k, tuple) else k): _stringify_tuple_keys(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_stringify_tuple_keys(v) for v in value]
    return value


def serialize_state(state: GameState) -> str:
    data = _stringify_tuple_keys(dataclasses.asdict(state))
    return json.dumps(data, default=_json_default)


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
    # lobby player_id (the uuid a client connects with) -> engine player_id
    # ("p1".."pN", assigned by new_game in lobby_players order).
    player_id_map: dict[str, str] = field(default_factory=dict)
    # Serializes action-apply + broadcast: with several player sockets each
    # running their own receive loop, two actions can otherwise be applied
    # back-to-back before either one's broadcast finishes going out to every
    # client (broadcast awaits each socket's send_text in turn), so different
    # clients can observe the two resulting states in different orders -
    # e.g. a bot rapidly bidding/passing through minor floats sees the
    # round type visibly flicker backwards. Holding this lock across
    # apply+broadcast makes each action's effect fully visible to everyone
    # before the next one is processed.
    action_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

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
                "player_id_map": self.player_id_map,
            })
        stale = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(pid)
        for pid in stale:
            self.connections.pop(pid, None)

    async def send_error(self, lobby_player_id: str, message: str) -> None:
        ws = self.connections.get(lobby_player_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps({"type": "error", "message": message}))
        except Exception:
            pass

    def start(self) -> None:
        if self.started:
            return
        names = [p.name for p in self.lobby_players]
        self.state = new_game(game_id=self.room_id, player_names=names)
        self.player_id_map = {
            p.player_id: f"p{i + 1}" for i, p in enumerate(self.lobby_players)
        }
        self.started = True

    def apply_action(self, lobby_player_id: str, action: dict) -> None:
        """Raises ActionError on an illegal action - callers should relay
        that back to just the offending client, not broadcast it."""
        if self.state is None:
            raise ActionError("Game has not started.")
        engine_player_id = self.player_id_map.get(lobby_player_id)
        if engine_player_id is None:
            raise ActionError("Unknown player.")
        apply_action(self.state, engine_player_id, action)


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
