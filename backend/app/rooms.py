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

from app import db
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
    # Each broadcast gets the next number here, included in the payload as
    # "seq". A client normally has just one socket, so message order is
    # already guaranteed - but solo/hotseat mode opens up to three
    # independent sockets (one per seat) for a single browser tab, and
    # nothing guarantees those sockets' *receive* callbacks fire in the
    # same order the server sent them in: a message on a slower socket can
    # still be processed after a newer message that arrived first on a
    # faster one, silently reverting the UI to older state. The client
    # compares seq and ignores anything not newer than what it already has.
    broadcast_seq: int = 0

    async def broadcast(self) -> None:
        self.broadcast_seq += 1
        self.persist()
        if self.state is None:
            payload = json.dumps({
                "type": "lobby",
                "room_id": self.room_id,
                "players": [dataclasses.asdict(p) for p in self.lobby_players],
                "started": self.started,
                "seq": self.broadcast_seq,
            })
        else:
            payload = json.dumps({
                "type": "state",
                "state": json.loads(serialize_state(self.state)),
                "player_id_map": self.player_id_map,
                "seq": self.broadcast_seq,
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
        self.persist()

    def apply_action(self, lobby_player_id: str, action: dict) -> None:
        """Raises ActionError on an illegal action - callers should relay
        that back to just the offending client, not broadcast it."""
        if self.state is None:
            raise ActionError("Game has not started.")
        engine_player_id = self.player_id_map.get(lobby_player_id)
        if engine_player_id is None:
            raise ActionError("Unknown player.")
        apply_action(self.state, engine_player_id, action)

    def persist(self) -> None:
        """Saves this room to SQLite so an active game survives a server
        restart (see app.db's module docstring - this was previously pure
        in-memory state, wiped on every restart). `connections` and
        `action_lock` are transport/runtime-only and deliberately excluded;
        `state` (if the game has started) goes through pickle since it's a
        deep dataclass graph, not something worth hand-rolling a JSON
        reconstruction for (see app.db)."""
        lobby_json = json.dumps([dataclasses.asdict(p) for p in self.lobby_players])
        state_blob = db.pickle_state(self.state) if self.state is not None else None
        db.save_room_row(
            room_id=self.room_id,
            lobby_json=lobby_json,
            started=self.started,
            state_pickle=state_blob,
            player_id_map_json=json.dumps(self.player_id_map),
        )


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def create_room(self) -> Room:
        room_id = uuid.uuid4().hex[:8]
        room = Room(room_id=room_id)
        self._rooms[room_id] = room
        room.persist()
        return room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def load_from_db(self) -> None:
        """Repopulates the registry from SQLite - call once at server
        startup so rooms saved before a restart come back to life instead
        of silently vanishing. WebSocket `connections` don't survive a
        restart either way (every client's socket already dropped), so
        clients just reconnect and get the restored state on their next
        message/broadcast."""
        for row in db.load_room_rows():
            room = Room(room_id=row["room_id"])
            room.lobby_players = [LobbyPlayer(**p) for p in json.loads(row["lobby_json"])]
            room.started = bool(row["started"])
            room.player_id_map = json.loads(row["player_id_map_json"])
            if row["state_pickle"] is not None:
                room.state = db.unpickle_state(row["state_pickle"])
            self._rooms[room.room_id] = room


registry = RoomRegistry()
