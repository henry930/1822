from fastapi.testclient import TestClient

from app.main import app


def _create_and_join(client, names):
    room_id = client.post("/rooms").json()["room_id"]
    player_ids = []
    for name in names:
        resp = client.post(f"/rooms/{room_id}/join", json={"name": name})
        player_ids.append(resp.json()["player_id"])
    client.post(f"/rooms/{room_id}/start")
    return room_id, player_ids


def test_bid_action_over_websocket_updates_broadcast_state():
    client = TestClient(app)
    room_id, (p1, p2, p3) = _create_and_join(client, ["Alice", "Bob", "Carol"])

    with client.websocket_connect(f"/ws/{room_id}/{p1}") as ws1, \
         client.websocket_connect(f"/ws/{room_id}/{p2}") as ws2, \
         client.websocket_connect(f"/ws/{room_id}/{p3}") as ws3:
        # Every new connection broadcasts to all already-connected clients,
        # so earlier connections accumulate one queued message per
        # connection that comes after them - drain those before asserting.
        first = ws1.receive_json()  # from its own connect
        assert first["type"] == "state"
        id_map = first["player_id_map"]  # lobby player_id -> engine player_id ("p1".."p3")
        assert id_map[p1] == "p1"
        ws1.receive_json()  # from ws2 connecting
        ws1.receive_json()  # from ws3 connecting
        ws2.receive_json()  # from its own connect
        ws2.receive_json()  # from ws3 connecting
        ws3.receive_json()  # from its own connect

        # new_game randomizes turn order, so find whichever lobby connection
        # actually goes first rather than assuming it's p1.
        by_lobby_id = {p1: ws1, p2: ws2, p3: ws3}
        engine_to_lobby = {eng: lob for lob, eng in id_map.items()}
        active_engine_id = first["state"]["active_player_id"]
        active_ws = by_lobby_id[engine_to_lobby[active_engine_id]]

        active_ws.send_text('{"type": "bid", "bids": [{"kind": "concession", "box_index": 0, "amount": 100}]}')

        msg = active_ws.receive_json()
        assert msg["type"] == "state"
        assert msg["state"]["active_player_id"] != active_engine_id  # turn advanced

        # The same broadcast reaches another connection too.
        other_ws = ws2 if active_ws is not ws2 else ws1
        msg2 = other_ws.receive_json()
        assert msg2["state"]["active_player_id"] == msg["state"]["active_player_id"]


def test_illegal_action_sends_error_only_to_the_offending_client():
    client = TestClient(app)
    room_id, (p1, p2, _p3) = _create_and_join(client, ["Alice", "Bob", "Carol"])

    with client.websocket_connect(f"/ws/{room_id}/{p1}") as ws1, \
         client.websocket_connect(f"/ws/{room_id}/{p2}") as ws2:
        first = ws1.receive_json()  # from its own connect
        ws1.receive_json()  # from ws2 connecting
        ws2.receive_json()  # from its own connect

        # Whichever of the two did NOT go first tries to act out of turn.
        id_map = first["player_id_map"]
        active_engine_id = first["state"]["active_player_id"]
        out_of_turn_ws = ws2 if id_map[p1] == active_engine_id else ws1

        out_of_turn_ws.send_text('{"type": "pass"}')

        err = out_of_turn_ws.receive_json()
        assert err["type"] == "error"
        assert "not your turn" in err["message"].lower()
