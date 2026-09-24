"""SQLite persistence layer.

Two distinct things live here, per the actual gaps that existed before this
module: app.rooms was explicitly "in-memory... for v1" (a server restart
silently wiped every active game), and the map tab's region-correction tool
(see MapTab.tsx) only ever saved to one browser's localStorage, never to the
server. Both now persist to a local SQLite file.

The engine itself is untouched: app.engine/app.data still run entirely on
their existing Python dataclasses in memory, and this module doesn't
replace that - it's a persistence side-channel. Reference data (tiles, map
regions, trains, companies) still has its Python files as the source of
truth; the tables here are a queryable, re-seeded-on-every-startup mirror
of them (seed_reference_data does a full replace, so a code change always
wins over whatever a previous run wrote) - useful for inspecting or
querying that data with ordinary SQL/DB tools instead of only from Python.

Room state uses pickle rather than hand-rolled JSON reconstruction:
GameState is a deep dataclass graph (nested dataclasses, Enums, a
tuple-keyed dict for the stock market grid - see rooms.py's own
_stringify_tuple_keys for how gnarly the JSON path already is one-way).
Round-tripping that correctly through JSON would need a matching from-dict
walker for every nested type, easy to get subtly wrong; pickle handles an
arbitrary Python object graph correctly by construction. This is a private,
server-side-only storage format (never sent to a client - the websocket
wire format is still the existing JSON serializer in rooms.py) and ties
saved rooms to the exact class shapes at save time, same "intentionally
simple for v1" tradeoff app.rooms already documented.
"""
from __future__ import annotations

import json
import os
import pickle
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("ONE822_DB_PATH", Path(__file__).resolve().parent.parent / "data" / "1822.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    room_id TEXT PRIMARY KEY,
    lobby_json TEXT NOT NULL,
    started INTEGER NOT NULL DEFAULT 0,
    state_pickle BLOB,
    player_id_map_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS region_corrections (
    hex_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_corrections (
    company_id TEXT PRIMARY KEY,
    data_json TEXT NOT NULL,
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tiles (
    id TEXT PRIMARY KEY,
    color TEXT NOT NULL,
    count TEXT NOT NULL,
    code TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS regions (
    hex_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    label TEXT,
    is_town INTEGER NOT NULL,
    town_count INTEGER NOT NULL,
    city_count INTEGER NOT NULL,
    home_of_minor_json TEXT NOT NULL,
    home_of_major_json TEXT NOT NULL,
    destination_of_major TEXT,
    confidence TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS offboard_areas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hexes_json TEXT NOT NULL,
    value_yellow INTEGER NOT NULL,
    value_green INTEGER NOT NULL,
    value_brown INTEGER NOT NULL,
    value_grey INTEGER NOT NULL,
    confidence TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS terrain_hexes (
    hex_id TEXT PRIMARY KEY,
    terrain TEXT NOT NULL,
    cost INTEGER NOT NULL,
    confidence TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocked_adjacencies (
    hex_a TEXT NOT NULL,
    hex_b TEXT NOT NULL,
    confidence TEXT NOT NULL,
    PRIMARY KEY (hex_a, hex_b)
);

CREATE TABLE IF NOT EXISTS edge_tolls (
    hex_a TEXT NOT NULL,
    hex_b TEXT NOT NULL,
    cost INTEGER NOT NULL,
    confidence TEXT NOT NULL,
    PRIMARY KEY (hex_a, hex_b)
);

CREATE TABLE IF NOT EXISTS trains (
    code TEXT PRIMARY KEY,
    cost INTEGER NOT NULL,
    count INTEGER,
    rusted_by TEXT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS major_companies (
    abbr TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    home_location TEXT NOT NULL,
    destination TEXT NOT NULL,
    station_tokens INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS minor_companies (
    number INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    abbr TEXT NOT NULL,
    home_location TEXT NOT NULL,
    home_hex TEXT NOT NULL,
    expansion INTEGER NOT NULL
);
"""

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """A single shared connection for the process. SQLite serializes writes
    internally; check_same_thread=False is safe here because FastAPI's sync
    endpoints and the websocket loop all run through the same event loop's
    worker thread(s) one call at a time per request, and every write in
    this module is a short, immediately-committed statement."""
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


def seed_reference_data(conn: sqlite3.Connection | None = None) -> None:
    """Full-replace re-seed of the read-only reference tables from the
    Python source of truth (app.data.*). Safe to call on every startup."""
    from app.data.hex_map import BLOCKED_ADJACENCIES, CITIES, EDGE_TOLLS, OFFBOARD_AREAS, TERRAIN_HEXES
    from app.data.major_companies import MAJOR_COMPANIES
    from app.data.minor_companies import MINOR_COMPANIES
    from app.data.tiles import TILE_SPECS
    from app.data.trains import TRAIN_TYPES

    conn = conn or get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM tiles")
    cur.executemany(
        "INSERT INTO tiles (id, color, count, code) VALUES (?, ?, ?, ?)",
        [(t.id, t.color, str(t.count), t.code) for t in TILE_SPECS],
    )

    def _as_list(value: Any) -> list:
        if isinstance(value, tuple):
            return list(value)
        return [value] if value is not None else []

    cur.execute("DELETE FROM regions")
    cur.executemany(
        """INSERT INTO regions
           (hex_id, name, label, is_town, town_count, city_count,
            home_of_minor_json, home_of_major_json, destination_of_major, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                c.id, c.name, c.label, int(c.is_town), c.town_count, c.city_count,
                json.dumps(_as_list(c.home_of_minor)), json.dumps(_as_list(c.home_of_major)),
                c.destination_of_major, c.confidence,
            )
            for c in CITIES
        ],
    )

    cur.execute("DELETE FROM offboard_areas")
    cur.executemany(
        """INSERT INTO offboard_areas
           (id, name, hexes_json, value_yellow, value_green, value_brown, value_grey, confidence)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (o.id, o.name, json.dumps(list(o.hexes)), o.value_yellow, o.value_green, o.value_brown,
             o.value_grey, o.confidence)
            for o in OFFBOARD_AREAS
        ],
    )

    cur.execute("DELETE FROM terrain_hexes")
    cur.executemany(
        "INSERT INTO terrain_hexes (hex_id, terrain, cost, confidence) VALUES (?, ?, ?, ?)",
        [(t.id, t.terrain, t.cost, t.confidence) for t in TERRAIN_HEXES],
    )

    cur.execute("DELETE FROM blocked_adjacencies")
    cur.executemany(
        "INSERT INTO blocked_adjacencies (hex_a, hex_b, confidence) VALUES (?, ?, ?)",
        list(BLOCKED_ADJACENCIES),
    )

    cur.execute("DELETE FROM edge_tolls")
    cur.executemany(
        "INSERT INTO edge_tolls (hex_a, hex_b, cost, confidence) VALUES (?, ?, ?, ?)",
        [(t.hex_a, t.hex_b, t.cost, t.confidence) for t in EDGE_TOLLS],
    )

    cur.execute("DELETE FROM trains")
    cur.executemany(
        "INSERT INTO trains (code, cost, count, rusted_by, name) VALUES (?, ?, ?, ?, ?)",
        [(t.code, t.cost, t.count, t.rusted_by, t.name) for t in TRAIN_TYPES],
    )

    cur.execute("DELETE FROM major_companies")
    cur.executemany(
        """INSERT INTO major_companies (abbr, name, home_location, destination, station_tokens)
           VALUES (?, ?, ?, ?, ?)""",
        [(c.abbr, c.name, c.home_location, c.destination, c.station_tokens) for c in MAJOR_COMPANIES],
    )

    cur.execute("DELETE FROM minor_companies")
    cur.executemany(
        """INSERT INTO minor_companies (number, name, abbr, home_location, home_hex, expansion)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(c.number, c.name, c.abbr, c.home_location, c.home_hex, int(c.expansion)) for c in MINOR_COMPANIES],
    )

    conn.commit()


# --- Rooms -------------------------------------------------------------

def save_room_row(
    room_id: str, lobby_json: str, started: bool, state_pickle: bytes | None, player_id_map_json: str,
) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO rooms (room_id, lobby_json, started, state_pickle, player_id_map_json, updated_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(room_id) DO UPDATE SET
             lobby_json=excluded.lobby_json, started=excluded.started,
             state_pickle=excluded.state_pickle, player_id_map_json=excluded.player_id_map_json,
             updated_at=excluded.updated_at""",
        (room_id, lobby_json, int(started), state_pickle, player_id_map_json),
    )
    conn.commit()


def load_room_rows() -> list[sqlite3.Row]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM rooms").fetchall()
    conn.row_factory = None
    return rows


def delete_room_row(room_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
    conn.commit()


def pickle_state(state: Any) -> bytes:
    return pickle.dumps(state)


def unpickle_state(blob: bytes) -> Any:
    return pickle.loads(blob)


# --- Region corrections --------------------------------------------------

def upsert_region_correction(hex_id: str, data: dict, saved_at: str) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO region_corrections (hex_id, data_json, saved_at) VALUES (?, ?, ?)
           ON CONFLICT(hex_id) DO UPDATE SET data_json=excluded.data_json, saved_at=excluded.saved_at""",
        (hex_id, json.dumps(data), saved_at),
    )
    conn.commit()


def get_region_corrections() -> dict[str, dict]:
    conn = get_connection()
    rows = conn.execute("SELECT hex_id, data_json FROM region_corrections").fetchall()
    return {hex_id: json.loads(data_json) for hex_id, data_json in rows}


def delete_region_correction(hex_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM region_corrections WHERE hex_id = ?", (hex_id,))
    conn.commit()


def bulk_merge_region_corrections(hex_ids: list[str], patch: dict, saved_at: str) -> None:
    """Merges `patch` (only the attribute categories the map tab's bulk
    editor had switched on) into each hex's existing correction, keeping
    whatever that hex already had for every other field - a per-hex name
    or label, say, is never something a bulk edit should touch. A hex with
    no existing correction just gets `patch` as its new one. All hexes
    commit together in one transaction."""
    conn = get_connection()
    existing = get_region_corrections()
    for hex_id in hex_ids:
        merged = {**existing.get(hex_id, {}), **patch, "hexId": hex_id, "savedAt": saved_at}
        conn.execute(
            """INSERT INTO region_corrections (hex_id, data_json, saved_at) VALUES (?, ?, ?)
               ON CONFLICT(hex_id) DO UPDATE SET data_json=excluded.data_json, saved_at=excluded.saved_at""",
            (hex_id, json.dumps(merged), saved_at),
        )
    conn.commit()


# --- Company (home/destination) corrections -------------------------------

def upsert_company_correction(company_id: str, data: dict, saved_at: str) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO company_corrections (company_id, data_json, saved_at) VALUES (?, ?, ?)
           ON CONFLICT(company_id) DO UPDATE SET data_json=excluded.data_json, saved_at=excluded.saved_at""",
        (company_id, json.dumps(data), saved_at),
    )
    conn.commit()


def get_company_corrections() -> dict[str, dict]:
    conn = get_connection()
    rows = conn.execute("SELECT company_id, data_json, saved_at FROM company_corrections").fetchall()
    # saved_at always comes from the column, not the JSON blob - the caller
    # (main.py) doesn't put it in `data` before calling upsert, only the
    # separate `saved_at` argument, so the column is the one source of truth.
    result = {}
    for company_id, data_json, saved_at in rows:
        entry = json.loads(data_json)
        entry["savedAt"] = saved_at
        result[company_id] = entry
    return result


def delete_company_correction(company_id: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM company_corrections WHERE company_id = ?", (company_id,))
    conn.commit()
