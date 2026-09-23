"""app.db: SQLite persistence for rooms (so a restart doesn't wipe active
games), the map tab's region corrections (server-side now, not just one
browser's localStorage), and a queryable mirror of the reference data."""
from app import db
from app.rooms import LobbyPlayer, Room, RoomRegistry


def _fresh_conn():
    # Each test gets its own connection to a fresh, freshly-schema'd DB
    # file so tests never see another test's rows - conftest.py already
    # points ONE822_DB_PATH at a per-session temp dir, this goes one step
    # further and gives each test its own file within it.
    import os
    import tempfile

    path = os.path.join(tempfile.mkdtemp(prefix="1822-test-db-case-"), "case.db")
    os.environ["ONE822_DB_PATH"] = path
    db._conn = None
    return db.get_connection()


def test_schema_creates_all_expected_tables():
    conn = _fresh_conn()
    tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    expected = {
        "rooms", "region_corrections", "tiles", "regions", "offboard_areas",
        "terrain_hexes", "blocked_adjacencies", "edge_tolls", "trains",
        "major_companies", "minor_companies",
    }
    assert expected <= tables


def test_seed_reference_data_matches_python_source():
    conn = _fresh_conn()
    db.seed_reference_data(conn)

    from app.data.tiles import TILE_SPECS
    from app.data.trains import TRAIN_TYPES

    tile_count = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
    assert tile_count == len(TILE_SPECS)

    train_count = conn.execute("SELECT COUNT(*) FROM trains").fetchone()[0]
    assert train_count == len(TRAIN_TYPES)

    london = conn.execute("SELECT city_count FROM regions WHERE hex_id = 'M38'").fetchone()
    assert london[0] == 6


def test_seed_reference_data_is_a_full_replace_not_accumulate():
    conn = _fresh_conn()
    db.seed_reference_data(conn)
    db.seed_reference_data(conn)  # calling twice must not double the rows
    from app.data.tiles import TILE_SPECS

    tile_count = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
    assert tile_count == len(TILE_SPECS)


def test_region_correction_round_trip():
    _fresh_conn()
    db.upsert_region_correction("H1", {"cityOrTown": "city", "name": "Aberdeen"}, "2026-01-01T00:00:00Z")
    corrections = db.get_region_corrections()
    assert corrections["H1"]["name"] == "Aberdeen"

    db.upsert_region_correction("H1", {"cityOrTown": "city", "name": "Aberdeen (edited)"}, "2026-01-02T00:00:00Z")
    corrections = db.get_region_corrections()
    assert corrections["H1"]["name"] == "Aberdeen (edited)"  # upsert, not duplicate

    db.delete_region_correction("H1")
    assert "H1" not in db.get_region_corrections()


def test_room_persist_and_reload_round_trips_lobby_state():
    _fresh_conn()
    registry = RoomRegistry()
    room = registry.create_room()
    room.lobby_players.append(LobbyPlayer(player_id="p1", name="Alice"))
    room.persist()

    reloaded = RoomRegistry()
    reloaded.load_from_db()
    restored = reloaded.get(room.room_id)
    assert restored is not None
    assert restored.lobby_players == [LobbyPlayer(player_id="p1", name="Alice")]
    assert restored.started is False
    assert restored.state is None


def test_room_persist_and_reload_round_trips_started_game_state():
    _fresh_conn()
    registry = RoomRegistry()
    room = registry.create_room()
    for i in range(3):
        room.lobby_players.append(LobbyPlayer(player_id=f"p{i}", name=f"Player {i}"))
    room.start()

    reloaded = RoomRegistry()
    reloaded.load_from_db()
    restored = reloaded.get(room.room_id)
    assert restored is not None
    assert restored.started is True
    assert restored.state is not None
    assert restored.state.phase == room.state.phase
    assert restored.player_id_map == room.player_id_map
