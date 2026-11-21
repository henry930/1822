import sys, traceback
sys.path.insert(0, 'backend')
from app.engine.setup import new_game
from app.engine import actions
from app.engine.stock_positions import place_token
errs = []
def run(name, f):
    try: f()
    except Exception as e:
        tb = traceback.format_exc().splitlines()
        errs.append(f"[{name}] {type(e).__name__}: {e}\n" + "\n".join(tb[-8:]))
def scen_a():
    s = new_game("g", ["P0", "P1", "P2"], seed=1)
    p = s.active_player_id
    actions.apply_action(s, p, {"type": "bid", "bids": [{"kind": "minor", "box_index": 0, "amount": 100}, {"kind": "private", "box_index": 0, "amount": 0}]})
    for _ in range(12):
        if s.round_type.name != "STOCK": break
        actions.apply_action(s, s.active_player_id, {"type": "pass"})
    assert s.round_type.name == "OPERATING" or s.game_over or s.stock_rounds_completed >= 1, "round did not progress"
def scen_b():
    s = new_game("g", ["P0", "P1", "P2"], seed=1)
    s.phase = 2
    a = s.player_order[0]
    s.players[a].concessions = ["GWR"]
    s.active_player_id = a
    actions.apply_action(s, a, {"type": "convert_concession", "abbr": "GWR", "start_price": 80})
    b = s.active_player_id
    actions.apply_action(s, b, {"type": "buy_share", "company_id": "GWR", "source": "treasury"})
    c = s.active_player_id
    s.majors["GWR"].has_operated = True
    actions.apply_action(s, c, {"type": "pass"})
def scen_c():
    s = new_game("g", ["P0", "P1", "P2"], seed=1)
    s.stock_rounds_completed = 1
    for _ in range(6):
        if s.round_type.name != "STOCK": break
        actions.apply_action(s, s.active_player_id, {"type": "pass"})
    from app.engine.trains import buy_train_from_bank
    from app.engine.round_manager import active_company_id
    assert s.round_type is not None
run("A bids+passes+resolve", scen_a); run("B convert+buy", scen_b); run("C passes", scen_c)
print("\n\n".join(errs) if errs else "SMOKE OK")
