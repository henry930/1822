#!/usr/bin/env python3
"""Generator for graph.json (1822 stock-round rules graph). Source of truth is the data below."""
import json, re, sys, collections

N = {}          # id -> node
E = []          # edges
_edge_seen = set()


def node(id, ntype, label, text, **attrs):
    assert id not in N, "duplicate id " + id
    N[id] = {"id": id, "type": ntype, "label": label, "text": text, "attrs": attrs}


def edge(src, dst, type, note="", **attrs):
    key = (src, dst, type)
    if key in _edge_seen and type not in ("order",):
        return
    _edge_seen.add(key)
    e = {"src": src, "dst": dst, "type": type, "note": note}
    e.update(attrs)
    E.append(e)


def rid(x):
    return ("ruling." + x) if x.startswith("R") and x[1:].isdigit() else ("rule." + x)


REF = re.compile(r"\[([^\]]*)\]")
RID = re.compile(r"^(R\d+|\d+\.\d+\.\d+)$")


def refs_in(s):
    out = []
    for grp in REF.findall(s):
        for part in re.split(r"[,;/ ]+", grp):
            if RID.match(part):
                out.append(part)
    return out


# ---------------------------------------------------------------- components
COMPS = {
    "market": ("Stock market and ordering",
               "Owns the stock-market grid state: token piles, price lookup, yellow-zone test, token moves (down on sale, up on sell-out), start-token placement, descending-share-price order, operating order, game-end-cell test."),
    "certificates": ("Holdings, certificate counting and directorship",
                     "Owns who holds which units/certificates of each major company and of concessions/privates/minors; certificate counting, certificate limit, 60% cap, sell legality incl. director succession, forced-sell test, sold-out test, director swap."),
    "share_trading": ("Player turn actions on shares",
                      "Implements the player actions sell shares, buy share, convert concession, repay loans with all preconditions/effects; owns loans, sold-this-round set, company treasuries and major company status."),
    "bidding": ("Bidding",
                "Owns bids on box items: legality of placing/moving bids, highest bid/bidder, committed money, tokens in use, face values and minimum bids."),
    "bid_boxes": ("Bid boxes and item stacks",
                  "Owns the three item stacks and the 4/3/3 bid boxes: compaction, refill, vacating items to players/removal, concession clearing at phase 5, minor ownership state."),
    "phase_trains": ("Phase and train deck",
                     "Owns game phase and the bank train deck: phase advance on first train of a type, rust/limit hooks, concession-clearing trigger, train exports (L-only and next-train)."),
    "sr_flow": ("Stock-round engine, setup, game end, ledger",
                "Owns game setup, round/turn state machine (turn record, pass streak, status), player order state, cash and bank ledger, the 'a sale happened' flag, game-end triggers, wealth, concession dividends."),
    "sr_resolution": ("End-of-stock-round resolution",
                      "Implements the end-of-round procedure: award/pay bid winners, float minors, unsold-minor train exports, box-1 removal, interest, price rises for sold-out companies, cash-based reorder of players; owns resolution-scratch state."),
}
for k, (lab, txt) in COMPS.items():
    node("comp." + k, "component", lab, txt)

# ---------------------------------------------------------------- entities
ENT = {
    "player": "A player: holds cash, loans, certificates, concessions, privates, minors, bidding tokens; has a stock-turn order position.",
    "private_company": "Private company certificate (face value 0). Obtained only through a bid box (3.1.4); never sold or traded (3.1.6).",
    "concession": "Concession certificate of one major company (face value 100, 3.4.2). Counts against certificate limit; converts to a director's certificate in phases 2-4.",
    "minor_company": "Minor company (M1..M24). One 50% director's certificate worth two shares; no other shares (3.2.2). Obtained only through a bid box; never sold (3.2.5).",
    "major_company": "Major company with 9 certificates (one 20% director's certificate + eight 10% shares); LNWR has 10 certificates of 10% (3.3.2).",
    "lnwr": "London & North Western Railway: special major company, 10 certificates of 10%; director's certificate is a single 10% unit; concession on top of stack (1.7.4).",
    "director_certificate": "Director's certificate: counts as 2 units (LNWR 1 unit) of ownership but as exactly ONE certificate for the certificate limit.",
    "share_certificate": "Ordinary 10% share certificate: 1 unit, 1 certificate.",
    "bid_box": "Bidding box for one item kind (4 minor boxes, 3 concession boxes, 3 private boxes), numbered from 1; holds at most one item and the bidding tokens on it.",
    "bidding_token": "A player's bidding token; sits on a space of an item's bid track whose value is the bid; cannot be withdrawn (4.10.10).",
    "stock_market": "The stock market grid; rows left-aligned as printed (R12).",
    "market_cell": "One cell of the grid: has a value (price), optional yellow flag, optional game-end flag, optional start-value marking; holds an ordered pile of tokens.",
    "stock_token": "A company's share-price token on the market.",
    "train": "A train in the bank deck (types L/2, 3, 4, 5, 6, 7/E).",
    "bank": "The bank: cash 12000 total supply incl. player start money; may go negative (broken).",
    "bank_pool": "Pool where sold shares go; max 50% of a company's stock (5 units).",
    "company_treasury": "A company's cash and unsold shares (treasury shares).",
    "loan": "Debt of a player to the bank (outside the bank's 12000, 4.3.5).",
    "item_stack": "Face-up stack of concessions / minors / privates, top item goes to the lowest empty box.",
    "player_order_card": "Player-number card; defines the stock-turn order.",
    "game": "Whole-game container: phase, round counter, flags, end trigger.",
}
for k, t in ENT.items():
    node("ent." + k, "entity", k.replace("_", " "), t)


# ---------------------------------------------------------------- constants
def const(id, label, text, **a):
    node("const." + id, "constant", label, text, **a)


const("start_money", "Start money per player", "Starting money = 2100 / player count: 3p 700, 4p 525, 5p 420, 6p 350, 7p 300 (1.7.2). Player counts 3..7 inferred from this list.",
      table={"3": 700, "4": 525, "5": 420, "6": 350, "7": 300}, source="1.7.2")
const("bank_total", "Bank total", "Bank is 12000 including players' starting money; initial bank cash = 12000 - n*start_money = 9900 (1.7.2). Loans are outside this sum (4.3.5).", value=12000, initial_bank_cash=9900, source="1.7.2")
const("cert_limit", "Certificate limit table", "Certificate limit per player count (4.2.1, 1.7.2). VALUES ABSENT from RULES.md (column header only). Must be supplied by the rules owner.",
      table={"3": None, "4": None, "5": None, "6": None, "7": None}, missing=True, source="1.7.2/4.2.1")
const("bidding_tokens", "Bidding tokens per player count", "Number of bidding tokens per player by player count (1.7.2, 4.10.3). VALUES ABSENT from RULES.md.",
      table={"3": None, "4": None, "5": None, "6": None, "7": None}, missing=True, source="1.7.2/4.10.3")
const("start_values", "Start values", "Allowed starting share prices: 50 (solid red, minors only, 1.6.3), 60, 70, 80, 90, 100 (red-outlined, majors and minors, 1.6.4). Major start price must be in {60..100}.",
      minor_values=[50, 60, 70, 80, 90, 100], major_values=[60, 70, 80, 90, 100])
const("face_values", "Face values", "Face value: concession 100 (3.4.2), minor 100 (R1), private 0 (3.1.3). Opening bid >= face value (4.10.6).",
      table={"concession": 100, "minor": 100, "private": 0})
const("box_counts", "Bid box counts", "4 minor boxes, 3 concession boxes, 3 private boxes (4.10.1). Box numbers start at 1.", table={"minor": 4, "concession": 3, "private": 3})
const("bid_rules", "Bid rule numbers", "Bids are whole multiples of 5 (4.10.6); at most 3 bids placed/moved per stock turn (4.10.5); no upper bound on a bid (4.10.9).", multiple=5, max_bids_per_turn=3)
const("share_structure", "Share structure of a major company", "Total 10 units. Standard major: director's certificate = 2 units, 8 ordinary certificates of 1 unit. LNWR: director's certificate = 1 unit, 9 ordinary certificates. Minor: one director's certificate worth 2 shares, no other shares (3.2.2). Pool cap 5 units (4.4.2); player cap 6 units (4.5.6).",
      total_units=10, standard={"director_units": 2, "ordinary_certs": 8}, lnwr={"director_units": 1, "ordinary_certs": 9}, pool_cap_units=5, hold_cap_units=6)
const("market_grid", "Stock market grid", "The printed market: grid of cells, rows left-aligned (R12), each cell value in pounds; down = row+1 same column, up = row-1 same column; cell absent = no move. NOT PRESENT in input; must be supplied as data.",
      missing=True, source="1.6.1/R12")
const("yellow_cells", "Yellow zone cells", "Set of cells shaded yellow (lower left, 1.6.5). Certificates of a company whose token is on such a cell do not count against the limit. NOT PRESENT in input.", missing=True)
const("game_end_cells", "Game-end cells", "Cells that carry the 'game end' value (10.1.1). NOT PRESENT in input.", missing=True)
const("start_cells", "Start cells", "Map price->cell for 50 (solid red), 60..100 (red outlined) (1.6.3/1.6.4). NOT PRESENT in input (positions).", missing=True)
const("train_deck", "Train deck composition", "Ascending order from top: double-sided L/2, 3, 4, 5, 6, double-sided 7/E (1.7.11). Counts per type NOT PRESENT in input.", order=["L/2", "3", "4", "5", "6", "7/E"], counts_missing=True)
const("phase_table", "Phase triggers", "Phase of the first train of a type: L/2 as 2-train -> 2; 3 -> 3; 4 -> 4; 5 -> 5; 6 -> 6; 7 or E -> 7 (2.2.3-2.2.8). Phase 5 removes unconverted concessions (2.2.8, R9).",
      table={"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7})
const("rust_table", "Rust table", "Phase 3 rusts L; phase 4 rusts 2; phase 6 rusts 3; phase 7 rusts 4 (2.2.4-2.2.8).", table={"3": ["L"], "4": ["2"], "6": ["3"], "7": ["4"]})
const("interest", "Loan interest", "End of stock round: loans += ceil(loans/2) (4.3.4, 4.11.10, R14).", rate_percent=50, rounding="up")
const("stack_setup", "Stack setup", "Concession stack: 9 shuffled + LNWR on top (1.7.4). Minor stack: 23 shuffled + M24 on top (1.7.5). Private stack: 17 shuffled + P1 on top (1.7.6). 1822+ extras out of scope.",
      concessions=10, minors=24, privates=18, tops={"concession": "LNWR", "minor": "M24", "private": "P1"})

# ---------------------------------------------------------------- states
STATE_OWNER = {}


def state(id, label, typ, scope, unit, owner, desc, part_of, external=None, **extra):
    a = dict(type=typ, scope=scope, unit=unit, owner_component=owner, part_of_entity=part_of)
    if external:
        a["external"] = True
        a["external_note"] = external
    a.update(extra)
    node("st." + id, "state", label, desc, **a)
    STATE_OWNER["st." + id] = owner
    edge("st." + id, "ent." + part_of, "part_of", "")


state("player_count", "Player count", "int 3..7", "game", "players", "sr_flow", "Number of players n; set once at setup.", "game")
state("sr_order", "Stock-turn order", "list<player>", "game", "player ids, index 0 = Player 1 card", "sr_flow",
      "Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction used for 'next in player order' tie-breaks (4.4.2).", "player_order_card")
state("player_cash", "Player cash", "int map player->int", "per player", "pounds (integer)", "sr_flow", "Cash in hand of each player. Never negative.", "player")
state("player_loans", "Player loans", "int map player->int", "per player", "pounds", "share_trading",
      "Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest.", "loan",
      external="Increases from forced train purchases are provided by the operating-round module (5.14/5.15, out of scope); this graph writes only repay and interest.")
state("bank_cash", "Bank cash", "int (can go below zero)", "game", "pounds", "sr_flow", "Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5).", "bank")
state("phase", "Game phase", "int 1..7", "game", "phase number", "phase_trains", "Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1).", "game")
state("sr_count", "Stock rounds started", "int", "game", "rounds", "sr_flow", "1 during the first stock round; used for 10.1.1 'first stock round'.", "game")
state("sr_status", "Stock-round status", "enum {not_started, in_progress, resolving, finished}", "game", "-", "sr_flow", "Where the stock round state machine is.", "game")
state("turn", "Active turn record", "record {active_player, stage in {A_sell,B_repay,C_main}, c_used in {none,buy,convert,bid}, bids_made int, acted bool}", "game", "-", "sr_flow",
      "The current player's stock turn: which player, which step, which exclusive C-action was used, how many bids placed/moved, whether any action was taken (to distinguish pass from end of turn).", "game")
state("pass_streak", "Consecutive passes", "int", "stock round", "turns", "sr_flow", "Number of consecutive turns that were passes; round ends when it equals the player count (4.11.1).", "game")
state("sale_happened", "A sale happened flag", "bool", "stock round", "-", "sr_flow",
      "Set true by sell_shares, buy_share (R15), convert_concession and a bid winning an item at resolution (R6 provisional). Reset at stock-round start. Read by the 10.1.1 first-round-nothing-sold test.", "game")
state("sold_this_round", "Sold-this-round set", "set<(player, major company)>", "stock round", "pairs", "share_trading",
      "Pairs (player, company) such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start.", "player")
state("ordinary_certs", "Ordinary certificates held", "int map (player, major)->int", "per player per major company", "certificates = units of 10% (ordinary share = 1 unit)", "certificates",
      "Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director).", "share_certificate")
state("director_holder", "Director's certificate holder", "map major->player|null", "per major company", "-", "certificates",
      "Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting.", "director_certificate")
state("treasury_shares", "Treasury shares", "int map major->int", "per major company", "ordinary certificates = units of 10%", "certificates", "Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation.", "company_treasury")
state("pool_shares", "Bank-pool shares", "int map major->int", "per major company", "ordinary certificates = units of 10%", "certificates", "Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2).", "bank_pool")
state("company_cash", "Company treasury cash", "int map company->int", "per major and minor company", "pounds", "share_trading", "Cash in a company's treasury.", "company_treasury",
      external="Spent/earned by operating rounds (out of scope); the stock round only credits it.")
state("major_status", "Major company status", "map major->enum {unstarted, floated}", "per major company", "-", "share_trading", "Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11).", "major_company")
state("has_completed_or", "Has completed an operating round", "map major->bool", "per major company", "-", "share_trading", "True once the company has completed an operating round; shares cannot be sold before (4.4.2).", "major_company",
      external="Set true by the operating-round module after the company's first completed operating turn (out of scope). Initial false at flotation.")
state("market_stack", "Market piles", "map cell->ordered list<company> (index 0 = top)", "game", "company ids", "market", "Which company tokens sit on which cell and their pile order. Company price = value of its cell. Pile order decides ties (1.6.2, 4.4.5, 4.12.2, 5.2.2).", "market_cell")
state("player_concessions", "Concessions held", "map player->set<major>", "per player", "concession certificates", "certificates", "Concession certificates a player holds (acquired after resolution, 4.7.5). Removed at phase 5 (R9).", "concession")
state("player_privates", "Privates held", "map player->set<private>", "per player", "private certificates", "certificates", "Private companies held by each player.", "private_company")
state("minor_director", "Minor director's certificate holder", "map minor->player|null", "per minor company", "-", "bid_boxes", "Player holding the 50% director's certificate of a minor (counts 1 certificate; assumption A6). Non-null = purchased and floated.", "minor_company")
state("concession_stack", "Concession stack", "ordered list<major>", "game", "concession certificates (top first)", "bid_boxes", "Remaining concessions; top goes to lowest empty concession box. LNWR on top at setup (1.7.4). Emptied at phase 5 (R9).", "item_stack")
state("minor_stack", "Minor stack", "ordered list<minor>", "game", "minor certificates (top first)", "bid_boxes", "Remaining minors; M24 on top at setup (1.7.5).", "item_stack")
state("private_stack", "Private stack", "ordered list<private>", "game", "private certificates (top first)", "bid_boxes", "Remaining privates; P1 on top at setup (1.7.6).", "item_stack")
state("box_contents", "Bid-box contents", "map (kind, box_no)->item|null", "game", "items", "bid_boxes", "Item sitting in each box: minor boxes 1..4, concession boxes 1..3, private boxes 1..3.", "bid_box")
state("removed_items", "Items removed from play", "set<item>", "game", "items", "bid_boxes", "Items removed from the game (unsold box-1 minor, concessions at phase 5). Audit only; consumed by operating rounds for minor-acquisition rules.", "item_stack",
      external="Consumer is the operating-round module (acquisition rules, out of scope).")
state("bids", "Bids on box items", "map item->map player->amount", "per item", "pounds (multiple of 5)", "bidding", "Bidding tokens on each item's track: at most one token per player per item (assumption A5). Amount = bid. Highest bid = max amount. Cleared at resolution (4.11.2).", "bidding_token")
state("items_with_bids", "Items that had a bid", "set<item>", "stock round", "items", "sr_resolution", "Snapshot at resolution of items on which any token was placed (including unpaid ones, R8); read by the unsold-minor export (4.11.6). Cleared at stock-round start.", "bid_box")
state("pending_minor_floats", "Minors awaiting flotation", "list<(minor, bid, box_no, buyer)>", "stock round", "-", "sr_resolution", "Minors paid for during resolve_bids, to be floated by float_minors in flotation order (4.11.3).", "minor_company")
state("train_deck", "Bank train deck", "ordered list<train type>", "game", "trains (front first)", "phase_trains", "Trains in the bank (not the bank pool), cheapest type first (1.7.11).", "train")
state("phase_events", "Phase-change event queue", "list<{from,to,rusted,trains_limit_check,or_per_sr}>", "game", "events", "phase_trains", "Hook queue consumed by the operating-round module: rusting (2.1.3), train-limit discard in descending share price order (2.1.4/2.1.5), operating rounds per SR (2.1.2).", "game",
      external="Consumed by the operating-round module (out of scope).")
state("game_end", "Game end trigger", "record {trigger in {none, immediate, after_next_or, end_of_current_or}, over bool}", "game", "-", "sr_flow", "First trigger wins (10.1.2).", "game")

# ---------------------------------------------------------------- rules
RULES = {}  # id -> (label, summary, targets, refers)


def rule(id, label, summary, targets=(), refers=(), **a):
    nid = rid(id)
    node(nid, "rule", label, id, summary=summary, **a)
    RULES[id] = (targets, refers)


rule("1.6.1", "Price is token position", "Share price = value of the cell holding the company's token.", ["drv.current_price", "drv.token_cell", "st.market_stack", "const.market_grid"])
rule("1.6.2", "Descending share price order", "Order by price desc; same price -> token furthest right first; same cell -> topmost first.", ["drv.descending_order"])
rule("1.6.3", "Solid red 50 cell", "Cell at 50 is solid red; only minors may start there.", ["const.start_values", "act.place_start_token", "drv.start_cell"])
rule("1.6.4", "Red-outlined start cells", "60..100 cells are start cells for majors and minors.", ["const.start_values", "act.place_start_token", "drv.start_cell", "const.start_cells"], ["4.11.4"])
rule("1.6.5", "Yellow zone", "Certificates of a company whose token is in a yellow cell do not count against the limit.", ["drv.in_yellow", "const.yellow_cells"], ["4.2.3"])
rule("1.7.2", "Bank, start money, tokens, limits", "Bank 12000 incl. start money 2100/n; bidding tokens and cert limit by player count.", ["act.setup_game", "const.start_money", "const.bank_total", "const.bidding_tokens", "const.cert_limit"])
rule("1.7.4", "Concession stack setup", "LNWR concession removed, rest shuffled, LNWR on top.", ["st.concession_stack", "act.setup_game", "const.stack_setup"])
rule("1.7.5", "Minor stack setup", "M24 removed, rest shuffled, M24 on top.", ["st.minor_stack", "act.setup_game", "const.stack_setup"])
rule("1.7.6", "Private stack setup", "P1 removed, rest shuffled, P1 on top.", ["st.private_stack", "act.setup_game", "const.stack_setup"])
rule("1.7.7", "Initial box fill", "Fill each box from its stack starting with box 1.", ["act.refill_boxes"], ["4.1.1"])
rule("1.7.11", "Train order", "Trains ascending, L/2 on top, 7/E at bottom.", ["st.train_deck", "const.train_deck", "act.setup_game"])
rule("1.7.12", "Random player order", "Player order cards dealt at random.", ["st.sr_order", "act.setup_game"])
rule("1.7.14", "Play starts with a stock round", "First round is a stock round.", ["act.start_stock_round"])
rule("2.1.1", "Phase advances on first train of a type", "First train of each type bought or exported advances the phase.", ["act.phase_check", "st.phase", "act.export_train"])
rule("2.1.2", "Phase effects immediate", "Immediate, except two ORs per SR starts after the following SR.", ["act.phase_check", "st.phase_events"])
rule("2.1.3", "Rusting", "Trains of a prior type rust immediately without compensation.", ["st.phase_events", "const.rust_table"])
rule("2.1.4", "Train limit discard", "Excess trains discarded after rusting, into bank pool.", ["st.phase_events"])
rule("2.1.5", "Discard order", "Companies discard in descending share price order.", ["drv.descending_order", "st.phase_events"], ["1.6.2"])
rule("2.2.2", "Start in phase 1", "Game starts in phase 1.", ["st.phase", "act.setup_game"])
rule("2.2.3", "Phase 2", "Phase 2: minor price = bid/2 rounded down to start value, treasury 2x; concessions convertible; major train limit 4.", ["drv.minor_start_price", "drv.minor_start_treasury", "act.convert_concession", "act.phase_check"], ["4.11.4"])
rule("2.2.4", "Phase 3", "Phase 3: L rusts; minor price as phase 2 but treasury = full bid.", ["drv.minor_start_treasury", "act.phase_check", "const.rust_table"], ["4.11.4"])
rule("2.2.5", "Phase 4", "Phase 4: 2-trains rust; limits.", ["act.phase_check", "const.rust_table"])
rule("2.2.6", "Phase 1 text (misplaced)", "Text numbered 2.2.6 is the phase-1 description: minor starts at 50 with 100 treasury irrespective of bid; major companies may not be floated.", ["drv.minor_start_price", "drv.minor_start_treasury", "act.convert_concession"], ["4.11.4", "4.6.2"])
rule("2.2.8", "Phases 5-7", "Phase 5 removes unconverted concessions; phase 6 rusts 3; phase 7 rusts 4.", ["act.clear_concession_boxes", "act.phase_check", "const.phase_table", "const.rust_table"])
rule("3.1.2", "Privates pay revenue", "Private pays fixed revenue each OR (OR scope).", [], ["5.2.1"])
rule("3.1.3", "Private face value 0", "Face value of privates is 0.", ["drv.face_value", "const.face_values"])
rule("3.1.4", "Privates only via bidding", "A private can only be bought through the bidding mechanism.", ["act.place_bid"])
rule("3.1.5", "Privates count toward limit", "Privates held by players count against the certificate limit (P16 exception deferred R11).", ["drv.cert_count_holdings"], ["4.2.2"])
rule("3.1.6", "Privates not tradable", "Privates may not be traded or sold to the bank.", ["act.sell_shares"])
rule("3.2.2", "Minor = 50% director's certificate", "A minor has only a 50% director's certificate worth two shares; no other shares exist.", ["const.share_structure", "act.float_minors"])
rule("3.2.4", "Minors only via bidding", "Players can only buy minors through bidding.", ["act.place_bid"], ["4.10.1", "4.11.4"])
rule("3.2.5", "Minors never sold", "Once bought, a minor may never be sold.", ["act.sell_shares"])
rule("3.3.2", "Major share structure", "9 certificates (director 20% = two shares + eight 10%); LNWR 10 certificates.", ["const.share_structure", "drv.cert_units", "act.convert_concession"])
rule("3.3.3", "Director = majority holder; swap", "Director's certificate belongs to the majority holder; on change it is swapped for two 10% certificates (LNWR one).", ["act.swap_director", "st.director_holder"])
rule("3.4.1", "Concession vs director's certificate", "Director's certificate can't be bought while the concession is in play.", ["act.convert_concession", "act.buy_share"])
rule("3.4.2", "Concessions via boxes, face 100", "Concessions bought through bid boxes; face value 100.", ["drv.face_value", "act.place_bid", "const.face_values"])
rule("3.4.3", "Concessions count toward limit", "Concessions count toward the owner's certificate limit.", ["drv.cert_count_holdings"], ["4.2.2"])
rule("3.4.4", "Concession dividend", "Each concession pays 10 per OR to its owner.", ["act.pay_concession_dividends"], ["5.2.1"])
rule("3.4.5", "Phase 5 concession removal", "At phase 5 concessions are removed from play (flipped to director side) -- overridden by R9.", ["act.clear_concession_boxes"], ["4.8.1"])
rule("4.1.1", "Box refill at start/end of SR", "Shift certificates to the lowest boxes then fill from stacks (first SR: 4 minors, 3 concessions, 3 privates).", ["act.refill_boxes", "act.start_stock_round"], ["4.10.2", "1.7.7"])
rule("4.1.2", "Turn order and bank-only transfers", "Round starts with Player 1 and proceeds in order; share transfers only between player and bank/company.", ["act.start_stock_round", "act.begin_turn", "st.sr_order", "act.buy_share"])
rule("4.1.3", "Turn structure A, B, C", "Sell, then repay loans, then one of buy/convert/bid; may pass.", ["act.begin_turn", "act.pass_turn", "act.sell_shares", "act.repay_loans", "st.turn"])
rule("4.1.4", "C options and round end", "One of: buy one share, convert, place/increase up to 3 bids; round ends when all pass consecutively.", ["act.buy_share", "act.convert_concession", "act.place_bid", "act.move_bid", "drv.sr_over", "act.resolve_stock_round"], ["4.11.1"])
rule("4.2.1", "Certificate limit by player count", "Each certificate counts against a limit set by player count.", ["const.cert_limit", "drv.cert_limit"])
rule("4.2.2", "What counts", "Privates, concessions and stock certificates owned by players count (P16 deferred R11).", ["drv.cert_count_holdings", "drv.certs_held"])
rule("4.2.3", "Yellow exemption", "Share certificates of a company in the yellow zone don't count.", ["drv.cert_count_holdings", "drv.in_yellow"], ["1.6.5"])
rule("4.2.4", "No purchase beyond limit", "A player at the limit may not buy anything that would exceed it.", ["act.buy_share"], ["4.5.7"])
rule("4.2.5", "No bid at limit; leading bids count", "At the limit a player may not bid; each item on which they hold the highest bid counts as a certificate.", ["act.place_bid", "act.move_bid", "drv.cert_count", "drv.items_led"], ["4.10.8"])
rule("4.2.6", "Over limit must sell", "A player over the limit must sell down.", ["drv.must_sell"], ["4.4.7"])
rule("4.3.1", "Loans block buying/converting/bidding", "No buying, converting or bidding while in debt.", ["act.buy_share", "act.convert_concession", "act.place_bid", "act.move_bid"])
rule("4.3.2", "Repay loans after selling", "After selling, a player may repay loans fully or partly to the bank.", ["act.repay_loans"])
rule("4.3.3", "No obligation to sell for repayment", "Not obliged to sell shares to repay.", ["act.repay_loans", "act.sell_shares"])
rule("4.3.4", "Interest at round end", "Debt at SR end incurs 50% interest rounded up.", ["act.charge_interest", "drv.interest_amount", "const.interest"], ["4.11.10"])
rule("4.3.5", "Loans outside bank", "Loans don't count toward the 12000 bank.", ["st.bank_cash", "act.repay_loans", "act.charge_interest"])
rule("4.4.1", "What may be sold", "Any number of stock certificates may be sold to the bank pool; privates, minors, concessions may not.", ["act.sell_shares"])
rule("4.4.2", "Sale constraints and director succession", "Not before company completed an OR; pool <= 50%; director's certificate cannot go into the pool; succession exchange precedes the rest of the sale.", ["act.sell_shares", "drv.sale_legal", "drv.successor", "act.swap_director", "st.has_completed_or", "st.pool_shares"], ["3.3.3"])
rule("4.4.3", "Sale proceeds", "Player receives the current share price per share sold.", ["act.sell_shares"])
rule("4.4.4", "Price drop", "Token moves down one cell per share sold; stops at the bottom.", ["act.move_token_down"])
rule("4.4.5", "Pile placement on move", "Moved token goes to the bottom of the destination pile; unmoved token keeps its place.", ["act.move_token_down", "st.market_stack"])
rule("4.4.6", "Sale order across companies", "Seller chooses the order of sales across companies; it fixes relative pile order.", ["act.sell_shares"])
rule("4.4.7", "Forced selling", "A player over the limit must sell what they can at the first opportunity.", ["drv.must_sell", "drv.can_sell_any", "act.pass_turn", "act.end_turn"], ["4.2.6"])
rule("4.5.1", "Buying mechanics", "Transfer one certificate from pool (pay bank) or treasury (pay company) at the market value.", ["act.buy_share", "st.company_cash"])
rule("4.5.2", "Only shares with a market value", "Director's certificate not buyable before phase 5; ordinary shares not before a director exists.", ["act.buy_share", "st.director_holder"], ["4.8.2"])
rule("4.5.3", "Buying doesn't move price", "Buying does not change the share price.", ["act.buy_share"])
rule("4.5.4", "One certificate per turn", "Only one certificate may be bought per turn.", ["act.buy_share", "st.turn"])
rule("4.5.5", "No rebuy after selling", "No buying of a company's stock after selling it earlier in the same round.", ["act.buy_share", "st.sold_this_round"])
rule("4.5.6", "60% cap", "No further certificates once holding 60% of the company.", ["act.buy_share", "drv.units_held"])
rule("4.5.7", "Limit check despite director change", "Cannot buy a certificate that would exceed the limit even if it changes directorship.", ["act.buy_share"], ["4.2.4"])
rule("4.5.8", "Yellow stock buyable at limit", "Yellow-zone stock does not count; buyable at the limit.", ["act.buy_share", "drv.in_yellow"], ["4.2.3"])
rule("4.5.9", "Buyer becomes director", "If the buyer exceeds the director's holding, they become director via exchange.", ["act.buy_share", "act.swap_director"], ["3.3.3"])
rule("4.6.1", "Formation depends on phase", "Procedure for forming majors depends on phase.", ["act.convert_concession"], ["4.6.2", "4.6.3", "4.6.4"])
rule("4.6.2", "No majors in phase 1", "Majors may not be formed in phase 1.", ["act.convert_concession"])
rule("4.6.3", "Phases 2-4 by concession only", "Director's certificates cannot be bought directly in phases 2-4.", ["act.convert_concession", "act.buy_share"], ["4.7.1"])
rule("4.6.4", "Phase 5 direct buying (deferred)", "From phase 5 directors are bought directly (R11: out of scope).", [], ["4.8.1", "4.8.2", "4.8.3"], deferred=True)
rule("4.7.1", "Convert in phases 2-4", "A player may start a major by converting its concession in phases 2-4.", ["act.convert_concession"])
rule("4.7.2", "Announce price, place token underneath", "Convert, choose a red-outlined start price 60..100, place token under existing tokens.", ["act.convert_concession", "act.place_start_token", "const.start_values"])
rule("4.7.3", "Capitalisation of non-LNWR", "100 from bank plus (2*price-100) from player into treasury; floated; rest of certificates into treasury.", ["act.convert_concession"])
rule("4.7.4", "LNWR conversion", "LNWR: 10% director's certificate; bank pays start price into treasury; floated.", ["act.convert_concession"])
rule("4.7.5", "Bought concessions convertible next round", "Items bid on are acquired only at round end, so convertible next round.", ["act.convert_concession", "act.resolve_bids"])
rule("4.7.6", "Company floated", "After conversion the company is floated.", ["act.convert_concession"], ["4.9.1"])
rule("4.9.1", "Same setup after floating", "Setup after floating is identical for both formation routes; remaining 4.9.x are physical (charter tokens, revenue marker, home station) and skipped.", ["act.convert_concession"])
for i, t in [(1, "Concessions removed, directors buyable"), (2, "Forming player sets price and buys director's certificate"), (3, "Float at 50% sold"), (4, "Phase 6+ full capitalisation"), (5, "Incremental vs full capitalisation"), (6, "Flotation depends on phase at flotation"), (7, "Proceed to 4.9")]:
    rule("4.8.%d" % i, "4.8.%d deferred (%s)" % (i, t), "Direct formation from phase 5 and 50%-sold flotation -- deferred by R11, not modelled.", [], ["4.6.4"], deferred=True)
rule("4.10.1", "Box counts", "4 minor, 3 concession, 3 private boxes.", ["const.box_counts", "st.box_contents"])
rule("4.10.2", "Shift and refill", "Shift remaining to lowest boxes, then fill from stack tops lowest first.", ["act.refill_boxes", "act.shift_boxes"], ["4.1.1"])
rule("4.10.3", "Bidding tokens limit", "Number of tokens by player count = max items a player may bid on.", ["drv.tokens_total", "act.place_bid", "const.bidding_tokens"], ["1.7.2"])
rule("4.10.4", "Place or move a bid", "Place an unallocated token on an empty space, or move a token up on the same item only if another player has a higher bid.", ["act.place_bid", "act.move_bid"])
rule("4.10.5", "Three bids per turn", "Up to three bids placed/moved per turn.", ["act.place_bid", "act.move_bid", "const.bid_rules", "st.turn"])
rule("4.10.6", "Opening bid and multiples of 5", "Opening bid >= face value; whole multiples of 5.", ["drv.bid_amount_valid", "drv.min_legal_bid"])
rule("4.10.7", "Higher than previous; committed <= cash", "Bid must exceed prior bids and keep committed money <= cash.", ["drv.bid_amount_valid", "drv.committed_money"])
rule("4.10.8", "No bid at certificate limit", "No placing/moving at the limit; leading bids count.", ["act.place_bid", "act.move_bid"], ["4.2.5"])
rule("4.10.9", "No ceiling on bids", "Any bid >= 100 over face is allowed (physical chip only).", ["drv.bid_amount_valid"])
rule("4.10.10", "Bids can't be withdrawn", "A bid cannot be withdrawn or moved to another item.", ["act.move_bid", "st.bids"])
rule("4.11.1", "Round ends on consecutive passes", "All players pass consecutively -> stock round over.", ["drv.sr_over", "act.resolve_stock_round"])
rule("4.11.2", "Pay and take items", "Highest bidders pay and take items; tokens are removed.", ["act.resolve_bids"])
rule("4.11.3", "Flotation order", "Purchased minors float from highest sum bid down; tie -> lowest box.", ["act.float_minors", "drv.minor_float_order"])
rule("4.11.4", "Minor start price and treasury", "Phase 1: 50/100; phase 2: half bid down to start value, treasury 2x; phase 3+: same price, treasury = bid.", ["drv.minor_start_price", "drv.minor_start_treasury", "act.float_minors"], ["2.2.3", "2.2.4", "2.2.6"])
rule("4.11.5", "Minor token stacking", "Minor tokens go on top of majors and beneath existing minors.", ["act.place_start_token"])
rule("4.11.6", "Export per unbid minor", "One L/2-train exported from the bank per minor with no bid; no action if none.", ["act.unsold_minor_exports", "act.export_train"], ["2.1.1"])
rule("4.11.7", "Unsold box-1 minor removed", "Unsold minor in box 1 is removed and next train exported (counts for phase).", ["act.remove_box1_minor_and_export", "act.export_train"], ["2.1.1"])
rule("4.11.8", "Unsold items shift down", "Other unsold items remain, shifted to lower boxes.", ["act.shift_boxes", "act.refill_boxes"])
rule("4.11.9", "Reorder players by cash", "Most cash gets card 1; ties keep previous relative order (P9 deferred).", ["act.reorder_players_by_cash", "drv.compute_stock_round_order"])
rule("4.11.10", "Interest on loans", "50% interest on outstanding loans at stock round end.", ["act.charge_interest"], ["4.3.4"])
rule("4.12.1", "Sold-out majors rise", "100% in players' hands -> token up one cell; no move at the top.", ["act.raise_sold_out_prices", "drv.fully_sold", "act.move_token_up"])
rule("4.12.2", "Rise order and placement", "Move in descending price order, top to bottom within piles; moved token goes to bottom of pile.", ["act.raise_sold_out_prices", "act.move_token_up"], ["1.6.2"])
rule("4.12.3", "Minors never sold out", "Minors are never 100% sold.", ["act.raise_sold_out_prices", "drv.fully_sold"])
rule("5.2.1", "Operating order", "A: privates/concessions pay; B: minors in descending price order; C: majors in descending price order.", ["drv.operating_order", "act.pay_concession_dividends"], ["1.6.2"])
rule("5.2.2", "Tie rules and deferred choice", "Same cell: top first; same value different cells: right first; next company decided after the previous finishes.", ["drv.operating_order", "drv.next_operating_company"], ["1.6.2"])
rule("10.1.1", "Game-end triggers", "Nothing sold in first SR -> immediate; token at game-end value in SR -> after next OR; bank broken in SR -> after next OR.", ["act.check_game_end_triggers", "st.game_end", "drv.bank_broken", "drv.is_game_end_cell"])
rule("10.1.2", "First trigger stands", "Once triggered the game ends at the indicated time.", ["act.check_game_end_triggers", "st.game_end"])
rule("10.1.3", "Wealth", "Stock at current prices + cash - loans; open concessions at face value; privates 0.", ["drv.player_wealth"])

# ---------------------------------------------------------------- rulings
RULINGS = {}


def ruling(id, label, summary, overrides=(), constrains=(), **a):
    node("ruling." + id, "ruling", label, id, summary=summary, **a)
    RULINGS[id] = (overrides, constrains)


ruling("R1", "Minor face value 100", "Minor face value = 100 (rulebook states none).", ["4.10.6"], ["drv.face_value", "const.face_values"])
ruling("R2", "Phase-2 minor start price", "Highest start value <= half the winning bid, minimum 50.", ["4.11.4", "2.2.3"], ["drv.minor_start_price"])
ruling("R3", "Minor bid flow", "Player pays full bid to bank. Phase 1: treasury 100, price 50. Phase 2: treasury 2x price. Phase 3+: treasury = bid. Bank covers difference.", ["4.11.4", "2.2.3", "2.2.4", "2.2.6"], ["drv.minor_start_treasury", "act.resolve_bids", "act.float_minors"])
ruling("R4", "LNWR conversion", "Bank pays whole start price into treasury; player pays nothing; gets 1-unit director certificate; no extra discount.", ["4.7.4"], ["act.convert_concession"])
ruling("R5", "Director may sell everything", "Director may sell everything only if another player holds >= director's-certificate units (2; LNWR 1) and more than the remaining holding; ties -> nearest after seller in player order.", ["4.4.2", "3.3.3"], ["drv.sale_legal", "drv.successor"])
ruling("R6", "Nothing-sold test", "Bidding alone is not a sale; buy, sell, convert count. Phase-1 conflict open; provisional: a bid that wins an item at resolution counts.", ["10.1.1"], ["st.sale_happened", "act.check_game_end_triggers", "act.resolve_bids", "act.convert_concession"])
ruling("R7", "Train export semantics", "4.11.6 exports count as L trains, never trigger a phase. 4.11.7 export takes the current buyable pool, runs the phase check, exports a 3-train when L/2 exhausted.", ["4.11.6", "4.11.7", "2.1.1"], ["act.export_train"])
ruling("R8", "Unpayable winner", "If the winner can't pay at resolution the item goes to next highest bidder who can; if nobody can it stays in its box and counts as having had a bid.", ["4.11.2"], ["act.resolve_bids"])
ruling("R9", "Concessions vanish at phase 5", "From phase 5 held concessions disappear, concession boxes are cleared and never refilled.", ["3.4.5", "4.8.1", "2.2.8", "4.1.1", "4.10.2"], ["act.clear_concession_boxes", "act.refill_boxes"])
ruling("R10", "Forced sell blocks buy/bid", "Over the limit must sell down at first opportunity; while over and able to sell the player may not buy or bid.", ["4.4.7", "4.2.6"], ["drv.must_sell", "act.buy_share", "act.place_bid", "act.move_bid", "act.convert_concession"])
ruling("R11", "Deferred scope", "Out of scope: P16 exceptions, P9 exception, 4.8 direct formation from phase 5, stock-market arrows (provisional: off right end -> up one row same column; off left end -> down one row).", ["4.6.4", "4.8.1", "4.8.2", "4.8.3", "4.8.4", "4.8.5", "4.8.6", "4.8.7", "3.1.5", "4.2.2", "4.2.4", "4.5.6", "4.5.7", "4.10.8", "4.11.9", "4.5.2"], ["act.move_token_up", "act.move_token_down", "act.reorder_players_by_cash"])
ruling("R12", "Market data", "Left-aligned rows as printed; price drop = down one row same column; no move if cell does not exist.", ["4.4.4", "4.12.1"], ["const.market_grid", "act.move_token_down", "act.move_token_up"])
ruling("R13", "100% sold test", "Sold out = treasury and bank pool hold zero units.", ["4.12.1"], ["drv.fully_sold"])
ruling("R14", "Interest formula", "Interest at SR end: loans += ceil(loans/2).", ["4.3.4", "4.11.10"], ["act.charge_interest", "drv.interest_amount"])
ruling("R15", "Sale flag", "Selling and buying shares both set the flag 'a sale happened this stock round'.", ["10.1.1"], ["st.sale_happened", "act.sell_shares", "act.buy_share"])

# ---------------------------------------------------------------- actions / derived registry
ACTS = []   # (id, spec)
DRVS = []


def P(check, rule_id=None):
    return {"check": check, "rule": rule_id}


def action(id, comp, label, text, params, pre, eff, err, reads=(), writes=(), calls=(), triggers=(), consts=(), returns="none", notes=""):
    nid = "act." + id
    if not err:
        err = ["NONE for legal input: total function when called in the documented order; ERR_ORDER if invoked out of sequence (e.g. outside resolve_stock_round)"]
    node(nid, "action", label, text, signature={"params": params, "returns": returns},
         preconditions=[({"check": c, "rule": r} if not isinstance(c, dict) else c) for c, r in pre] if pre and isinstance(pre[0], tuple) else pre,
         effects=eff, errors=err, notes=notes, component=comp)
    ACTS.append((nid, comp, reads, writes, calls, triggers, consts, pre, eff, text))


def derived(id, comp, label, text, params, formula, reads=(), calls=(), consts=(), returns="", notes=""):
    nid = "drv." + id
    node(nid, "derived", label, text, signature={"params": params, "returns": returns}, formula=formula, notes=notes, component=comp)
    DRVS.append((nid, comp, reads, calls, consts, formula, text))


def S(*a):
    return ["st." + x for x in a]


def D(*a):
    return ["drv." + x for x in a]


def A(*a):
    return ["act." + x for x in a]


def C(*a):
    return ["const." + x for x in a]


# ================================================================ sr_flow
action("setup_game", "sr_flow", "Set up the game",
       "Initialise all state for a new game: cash, bank, stacks, train deck, order, phase; boxes are filled by the first start_stock_round.",
       ["player_count n", "shuffled concession/minor/private stacks (random input)", "random player order (random input)", "train deck composition (data)", "market data (data)"],
       [("3 <= n <= 7 (start money table only defines these counts)", "1.7.2"), ("cert limit, bidding token, market, train-deck data supplied", "1.7.2")],
       ["[2.2.2] phase = 1",
        "[1.7.2] each player cash = 2100/n; bank_cash = 12000 - 2100 = 9900; all loans 0",
        "[1.7.4] concession_stack = shuffle(9 non-LNWR) with LNWR on top",
        "[1.7.5] minor_stack = shuffle(23) with M24 on top",
        "[1.7.6] private_stack = shuffle(17) with P1 on top",
        "[1.7.11] train_deck = trains ascending L/2 ... 7/E",
        "[1.7.12] sr_order = random permutation",
        "sr_count = 0; sr_status = not_started; all boxes empty (filled by refill_boxes at start of first SR, 1.7.7); market empty; holdings empty; every major unstarted; sale_happened=false; game_end none"],
       ["ERR_PLAYER_COUNT: n not in 3..7", "ERR_MISSING_DATA: a required constant table is missing"],
       writes=S("player_count", "sr_order", "player_cash", "player_loans", "bank_cash", "phase", "sr_count", "sr_status", "turn", "pass_streak", "sale_happened", "sold_this_round", "ordinary_certs", "director_holder", "treasury_shares", "pool_shares", "company_cash", "major_status", "market_stack", "player_concessions", "player_privates", "minor_director", "concession_stack", "minor_stack", "private_stack", "box_contents", "removed_items", "bids", "items_with_bids", "pending_minor_floats", "train_deck", "phase_events", "game_end"),
       consts=C("start_money", "bank_total", "stack_setup", "train_deck", "cert_limit", "bidding_tokens", "market_grid"))

action("start_stock_round", "sr_flow", "Start a stock round",
       "Begin a stock round: refill boxes, reset per-round flags, hand the turn to Player 1.",
       ["none"],
       [("game not over (game_end.over false)", "10.1.2"), ("sr_status in {not_started, finished}", "1.7.14")],
       ["[4.1.1] call refill_boxes (start-of-round refill)",
        "sr_count += 1; sr_status = in_progress",
        "[R15] sale_happened = false",
        "sold_this_round = empty set; items_with_bids = empty; pending_minor_floats = empty; pass_streak = 0",
        "[4.1.2] call begin_turn(sr_order[0])"],
       ["ERR_GAME_OVER", "ERR_SR_ALREADY_RUNNING"],
       reads=S("game_end", "sr_status", "sr_order"), writes=S("sr_count", "sr_status", "sale_happened", "sold_this_round", "items_with_bids", "pending_minor_floats", "pass_streak"),
       calls=A("refill_boxes", "begin_turn"), triggers=A("begin_turn"))

action("begin_turn", "sr_flow", "Begin a player's stock turn",
       "Make a player active and reset the per-turn record.",
       ["player"],
       [("player is the next in sr_order after the previous turn's player (or sr_order[0] at round start)", "4.1.2")],
       ["[4.1.3] turn = {active_player: player, stage: A_sell, c_used: none, bids_made: 0, acted: false}"],
       ["ERR_WRONG_PLAYER"],
       reads=S("sr_order", "sr_status"), writes=S("turn"))

action("end_turn", "sr_flow", "End a turn after acting",
       "Finish a turn in which the player took at least one action; resets the pass streak and passes the turn on.",
       ["player"],
       [("turn.acted is true (otherwise use pass_turn)", "4.1.3"), ("not must_sell(player)", "4.4.7"), ("R10: a player over the limit and able to sell has not finished selling", "R10")],
       ["pass_streak = 0 (any action breaks the consecutive-pass chain; assumption A13)",
        "[4.1.2] next player = successor of player in sr_order (cyclic); call begin_turn(next)"],
       ["ERR_NO_ACTION_TAKEN (use pass_turn)", "ERR_MUST_SELL"],
       reads=S("turn", "sr_order"), writes=S("pass_streak"), calls=A("begin_turn") + D("must_sell", "next_player"), triggers=A("begin_turn"))

action("pass_turn", "sr_flow", "Pass",
       "Player takes no action; the round ends when every player has passed consecutively.",
       ["player"],
       [("turn.acted is false", "4.1.3"), ("not must_sell(player)", "4.4.7"), ("sr_status = in_progress and player is active", "4.1.2")],
       ["[4.1.4] pass_streak += 1",
        "[4.11.1] if drv.sr_over then trigger resolve_stock_round and set sr_status = resolving; else call begin_turn(next player)"],
       ["ERR_MUST_SELL", "ERR_ACTION_ALREADY_TAKEN", "ERR_NOT_ACTIVE"],
       reads=S("turn", "sr_status", "sr_order", "pass_streak"), writes=S("pass_streak", "sr_status"),
       calls=A("begin_turn") + D("must_sell", "sr_over", "next_player"), triggers=A("resolve_stock_round", "begin_turn"))

action("check_game_end_triggers", "sr_flow", "Check game-end triggers",
       "Evaluate the stock-round game-end conditions and record the first trigger.",
       ["context in {after_bank_payment, after_token_move, end_of_stock_round}"],
       [("if game_end.trigger != none: do nothing (first trigger stands)", "10.1.2")],
       ["[10.1.1] if bank_broken: trigger = after_next_or",
        "[10.1.1] if any token is on a game-end cell: trigger = after_next_or",
        "[10.1.1, R6] if context = end_of_stock_round and sr_count = 1 and sale_happened = false: trigger = immediate and over = true",
        "[10.1.2] never overwrite an existing trigger"],
       [],
       reads=S("bank_cash", "market_stack", "sr_count", "sale_happened", "game_end"), writes=S("game_end"),
       calls=D("bank_broken", "is_game_end_cell", "token_cell"), consts=C("game_end_cells"))

action("pay_concession_dividends", "sr_flow", "Pay concession dividends",
       "Operating-round step A for concessions: each held concession pays 10 to its owner from the bank.",
       ["none"],
       [("phase < 5 (concessions exist)", "R9")],
       ["[3.4.4, 5.2.1] for every player and every concession held: player_cash += 10; bank_cash -= 10",
        "[10.1.1] call check_game_end_triggers(after_bank_payment)"],
       [],
       reads=S("player_concessions", "phase"), writes=S("player_cash", "bank_cash"), calls=A("check_game_end_triggers"),
       notes="Private revenues (3.1.2) are table data outside this graph.")

derived("sr_over", "sr_flow", "Stock round over?", "True when all players passed consecutively.", ["none"], "[4.11.1] pass_streak == player_count", reads=S("pass_streak", "player_count"), returns="bool")
derived("bank_broken", "sr_flow", "Bank broken?", "True when the bank has run out of money.", ["none"], "[10.1.1] bank_cash < 0 (assumption A29; loans excluded [4.3.5])", reads=S("bank_cash"), returns="bool")
derived("next_player", "sr_flow", "Next player in order", "The player after p in the cyclic stock-turn order.", ["player p"], "[4.1.2] sr_order[(index(p)+1) mod n]", reads=S("sr_order", "player_count"), returns="player")
derived("player_wealth", "sr_flow", "Player wealth", "Final wealth of a player.", ["player p"],
        "[10.1.3] cash + sum over majors c of units_held(p,c)*current_price(c) + 100 * |concessions held| - loans; privates and company assets count 0",
        reads=S("player_cash", "player_loans", "player_concessions"), calls=D("units_held", "current_price"), returns="int")

# ================================================================ share_trading
action("sell_shares", "share_trading", "Sell shares", "Sell s ordinary certificates of one major company into the bank pool (one batch).",
       ["player", "major company c", "count s"],
       [("turn.active_player = player and turn.stage = A_sell (selling precedes repaying and C action)", "4.1.3"),
        ("c is a major company; privates, minors and concessions can never be sold", "4.4.1"),
        ("major_status[c] = floated and has_completed_or[c]", "4.4.2"),
        ("drv.sale_legal(player,c,s).legal: s <= ordinary_certs unless director with a successor (director's certificate itself never goes to the pool)", "4.4.2"),
        ("pool_shares[c] + s <= 5 (50% of the company)", "4.4.2"),
        ("director selling beyond ordinary certs needs an eligible successor (units >= director units and > remaining holding)", "R5"),
        ("loans do not block selling", "4.3.3")],
       ["let price = current_price(c) read BEFORE any move (assumption A9)",
        "[4.4.2] if sale_legal.swap_needed: call swap_director(c, sale_legal.successor) BEFORE the rest of the sale",
        "[4.4.1] ordinary_certs[player,c] -= s; pool_shares[c] += s",
        "[4.4.3] player_cash += s*price; bank_cash -= s*price",
        "[4.4.4, 4.4.5] call move_token_down(c, s)",
        "[4.5.5] add (player,c) to sold_this_round",
        "[R15] sale_happened = true",
        "[10.1.1] call check_game_end_triggers(after_bank_payment)",
        "turn.acted = true (player may sell several companies in a chosen order [4.4.6])"],
       ["ERR_NOT_SELLABLE: not a floated major / has not completed an OR", "ERR_POOL_FULL", "ERR_TOO_MANY: s exceeds holdings / no successor", "ERR_WRONG_STAGE"],
       reads=S("turn", "major_status", "has_completed_or", "ordinary_certs", "director_holder", "pool_shares"),
       writes=S("ordinary_certs", "pool_shares", "player_cash", "bank_cash", "sold_this_round", "sale_happened", "turn"),
       calls=D("sale_legal", "current_price") + A("swap_director", "move_token_down", "check_game_end_triggers"))

action("repay_loans", "share_trading", "Repay loans", "Pay all or part of the player's loans to the bank (step B).",
       ["player", "amount"],
       [("turn.stage <= B_repay (after sell step, before C)", "4.1.3"), ("0 < amount <= min(loans, cash)", "4.3.2"), ("no obligation to sell to raise the money", "4.3.3")],
       ["[4.3.2] player_cash -= amount; player_loans -= amount",
        "[4.3.5] bank_cash unchanged (loans are a separate source; assumption A28)",
        "turn.stage = B_repay; turn.acted = true"],
       ["ERR_NO_LOANS", "ERR_INSUFFICIENT_CASH", "ERR_WRONG_STAGE"],
       reads=S("turn", "player_cash", "player_loans"), writes=S("player_cash", "player_loans", "turn"))

action("buy_share", "share_trading", "Buy one share", "Buy one ordinary share of a started major company from its treasury or from the bank pool (step C).",
       ["player", "major company c", "source in {treasury, pool}"],
       [("turn.stage <= C_main and turn.c_used = none (buy, convert and bid are exclusive; one certificate per turn)", "4.1.4"),
        ("one certificate per turn", "4.5.4"),
        ("player_loans[player] = 0", "4.3.1"),
        ("not must_sell(player) (over the limit and still able to sell)", "R10"),
        ("major_status[c] = floated and director_holder[c] != null (ordinary shares need a director; director's certificate not buyable by 'buy', phase-5 buying deferred)", "4.5.2"),
        ("source holds >= 1 ordinary certificate (treasury_shares or pool_shares)", "4.5.1"),
        ("player_cash >= current_price(c) (no allowance for committed bids; assumption A7)", "4.5.1"),
        ("(player,c) not in sold_this_round", "4.5.5"),
        ("units_held(player,c) < 6", "4.5.6"),
        ("if not in_yellow(c): cert_count(player) + 1 <= cert_limit even if directorship would change", "4.5.7"),
        ("if in_yellow(c): limit not checked", "4.5.8"),
        ("director certificate cannot be bought while the concession is in play", "3.4.1")],
       ["price = current_price(c) [4.5.3: unchanged by the purchase]",
        "[4.5.1] player_cash -= price; if source = treasury: company_cash[c] += price and treasury_shares[c] -= 1; if source = pool: bank_cash += price and pool_shares[c] -= 1",
        "[4.5.1] ordinary_certs[player,c] += 1",
        "[4.5.9] if units_held(player,c) > units_held(director_holder[c], c): call swap_director(c, player)",
        "[R15] sale_happened = true",
        "turn.c_used = buy; turn.acted = true"],
       ["ERR_LOANS", "ERR_MUST_SELL", "ERR_NOT_STARTED", "ERR_NO_SHARE_AT_SOURCE", "ERR_INSUFFICIENT_CASH", "ERR_SOLD_THIS_ROUND", "ERR_AT_60_PERCENT", "ERR_CERT_LIMIT", "ERR_C_ALREADY_USED"],
       reads=S("turn", "player_loans", "major_status", "director_holder", "treasury_shares", "pool_shares", "player_cash", "sold_this_round", "ordinary_certs"),
       writes=S("player_cash", "company_cash", "treasury_shares", "pool_shares", "bank_cash", "ordinary_certs", "sale_happened", "turn"),
       calls=D("current_price", "units_held", "cert_count", "in_yellow", "cert_limit", "must_sell") + A("swap_director"))

action("convert_concession", "share_trading", "Convert concession", "Convert a held concession into the director's certificate, set the start price and float the major company (phases 2-4).",
       ["player", "major company c", "start_price in {60,70,80,90,100}"],
       [("turn.stage <= C_main and turn.c_used = none", "4.1.4"),
        ("2 <= phase <= 4 (no majors in phase 1; concessions removed at phase 5)", "4.6.2"),
        ("phase 1 forbids floating majors", "2.2.6"),
        ("c in player_concessions[player]", "4.7.5"),
        ("major_status[c] = unstarted", "3.4.1"),
        ("player_loans[player] = 0", "4.3.1"),
        ("not must_sell(player) (assumption A8)", "R10"),
        ("start_price in {60,70,80,90,100}; 50 is for minors only", "1.6.4"),
        ("non-LNWR: player_cash >= 2*start_price - 100", "4.7.3"),
        ("LNWR: player pays nothing", "R4")],
       ["[4.7.2] remove c from player_concessions[player]; director_holder[c] = player",
        "[4.7.2] call place_start_token(c, start_price, major) -- underneath all tokens already in that cell",
        "[4.7.3] non-LNWR: bank_cash -= 100; player_cash -= (2*start_price - 100); company_cash[c] = 2*start_price",
        "[4.7.4, R4] LNWR: bank_cash -= start_price; company_cash[c] = start_price; player pays nothing; director certificate is 1 unit",
        "[3.3.2] treasury_shares[c] = 8 (LNWR 9); pool_shares[c] = 0; ordinary_certs[player,c] unchanged",
        "[4.7.6] major_status[c] = floated (operates next OR; has_completed_or[c] = false)",
        "[R6] sale_happened = true",
        "[10.1.1] call check_game_end_triggers(after_bank_payment)",
        "turn.c_used = convert; turn.acted = true"],
       ["ERR_PHASE", "ERR_NOT_HELD", "ERR_ALREADY_STARTED", "ERR_LOANS", "ERR_MUST_SELL", "ERR_BAD_START_PRICE", "ERR_INSUFFICIENT_CASH", "ERR_C_ALREADY_USED"],
       reads=S("turn", "phase", "player_concessions", "major_status", "player_loans", "player_cash"),
       writes=S("player_concessions", "director_holder", "bank_cash", "player_cash", "company_cash", "treasury_shares", "pool_shares", "major_status", "sale_happened", "turn", "has_completed_or"),
       calls=A("place_start_token", "check_game_end_triggers") + D("must_sell", "cert_units"), consts=C("start_values", "share_structure"))

# ================================================================ certificates
action("swap_director", "certificates", "Swap director's certificate", "Exchange the director's certificate for ordinary certificates of the new director (3.3.3).",
       ["major company c", "new director q"],
       [("q != director_holder[c] and ordinary_certs[q,c] >= cert_units(c)", "3.3.3")],
       ["[3.3.3] old = director_holder[c]",
        "[4.4.2, 4.5.9] ordinary_certs[q,c] -= cert_units(c); ordinary_certs[old,c] += cert_units(c); director_holder[c] = q",
        "total units of every holder unchanged; certificate counts change: q -(cert_units-1), old +(cert_units-1) (LNWR: no change)"],
       ["ERR_NOT_ENOUGH_ORDINARY"],
       reads=S("director_holder", "ordinary_certs"), writes=S("ordinary_certs", "director_holder"), calls=D("cert_units"))

derived("cert_units", "certificates", "Director certificate units", "Units of 10% that a director's certificate counts as.", ["major company c"],
        "[3.3.2] 1 if c = LNWR else 2. As certificates the director's certificate always counts exactly 1.", consts=C("share_structure"), returns="int")
derived("units_held", "certificates", "Units held", "Units of 10% a player holds in a major company.", ["player p", "major c"],
        "[4.5.6] ordinary_certs[p,c] + (cert_units(c) if director_holder[c] == p else 0)", reads=S("ordinary_certs", "director_holder"), calls=D("cert_units"), returns="int")
derived("certs_held", "certificates", "Certificates held", "Number of certificate cards a player holds in a company, for limit counting.", ["player p", "company c"],
        "[4.2.2] major: ordinary_certs[p,c] + (1 if director_holder[c]==p else 0); minor: 1 if minor_director[c]==p else 0",
        reads=S("ordinary_certs", "director_holder", "minor_director"), returns="int")
derived("cert_limit", "certificates", "Certificate limit", "Limit for the current player count.", ["none"], "[4.2.1] const.cert_limit[player_count] (table missing from input)", reads=S("player_count"), consts=C("cert_limit"), returns="int")
derived("cert_count_holdings", "certificates", "Certificates held counted against the limit", "Certificates a player owns that count toward the limit.", ["player p"],
        "[4.2.2, 3.1.5, 3.4.3, 4.2.3] sum over majors and minors c of (0 if in_yellow(c) else certs_held(p,c)) + |player_privates[p]| + |player_concessions[p]| (P16 not exempted, R11)",
        reads=S("player_privates", "player_concessions"), calls=D("certs_held", "in_yellow"), returns="int")
derived("cert_count", "certificates", "Certificate count incl. leading bids", "Count used for every 'at the limit' test.", ["player p"],
        "[4.2.5, 4.10.8] cert_count_holdings(p) + items_led(p)", calls=D("cert_count_holdings", "items_led"), returns="int")
derived("over_limit", "certificates", "Over the limit?", "True when a player holds more than the limit.", ["player p"], "[4.2.6, 4.4.7] cert_count(p) > cert_limit", calls=D("cert_count", "cert_limit"), returns="bool")
derived("successor", "certificates", "Eligible successor director", "Player who would become director if the director's remaining holding is r.", ["major c", "director d", "remaining units r"],
        "[4.4.2, R5] candidates = {q != d : units_held(q,c) >= cert_units(c) and units_held(q,c) > r}; none -> null; else max units_held; tie -> the tying player closest after d in sr_order (cyclic, forward)",
        reads=S("sr_order"), calls=D("units_held", "cert_units"), returns="player|null")
derived("sale_legal", "certificates", "Is a sale legal?", "Whether player p may sell s shares of company c and what directorship change that causes.", ["player p", "major c", "count s"],
        "[4.4.2, R5] let k=ordinary_certs[p,c], H=units_held(p,c), d=director_holder[c]; legal = s>=1 and major_status[c]==floated and has_completed_or[c] and pool_shares[c]+s<=5 and "
        "(p!=d: s<=k ; p==d: s<=k, or (s<=H and successor(c,p,H-s)!=null)); swap_needed = p==d and successor(c,p,H-s)!=null (s<=k: only if another player exceeds H-s; s>k: forced); returns {legal, swap_needed, successor}",
        reads=S("ordinary_certs", "director_holder", "pool_shares", "major_status", "has_completed_or"), calls=D("units_held", "successor"), returns="record")
derived("can_sell_any", "certificates", "Able to sell anything?", "True if at least one sale of one share is legal.", ["player p"], "[4.4.7] exists major c: sale_legal(p,c,1).legal", reads=S("major_status"), calls=D("sale_legal"), returns="bool")
derived("must_sell", "certificates", "Forced to sell?", "True when over the limit and able to sell.", ["player p"], "[4.4.7, R10] over_limit(p) and can_sell_any(p)", calls=D("over_limit", "can_sell_any"), returns="bool")
derived("fully_sold", "certificates", "Company 100% in players' hands?", "Sold-out test for the price rise.", ["major c"],
        "[4.12.1, R13, 4.12.3] major_status[c]==floated and treasury_shares[c]==0 and pool_shares[c]==0 (minors: always false)", reads=S("major_status", "treasury_shares", "pool_shares"), returns="bool")

# ================================================================ market
action("place_start_token", "market", "Place start token", "Place a newly started company's token on its start cell.",
       ["company c", "price", "kind in {major, minor}"],
       [("price in {60..100} for majors; 50 allowed for minors only", "1.6.3"), ("price is a start value", "1.6.4")],
       ["cell = start_cell(price)",
        "[4.7.2] major: insert c at the BOTTOM of the pile in cell",
        "[4.11.5] minor: insert above every major token and below existing minor tokens in the cell"],
       ["ERR_BAD_START_PRICE"],
       reads=S("market_stack"), writes=S("market_stack"), calls=D("start_cell"), consts=C("start_values"))

action("move_token_down", "market", "Move token down", "Price drop after a sale: move down one row per share sold.",
       ["company c", "steps s"],
       [("c has a token on the market", "1.6.1")],
       ["[4.4.4, R12] row' = row; repeat s times: if cell (row'+1, col) exists then row' += 1 else stop",
        "[4.4.5] if the cell changed: remove c from its pile and append at the BOTTOM of the destination pile; if not, keep its place in the pile"],
       ["ERR_NO_TOKEN"],
       reads=S("market_stack"), writes=S("market_stack"), calls=D("token_cell"), consts=C("market_grid"))

action("move_token_up", "market", "Move token up", "Price rise for a sold-out company: one row up, same column.",
       ["company c"],
       [("c has a token on the market", "1.6.1")],
       ["[4.12.1, R12] if cell (row-1, col) exists: move there, else no move",
        "[4.12.2] appended at the BOTTOM of the destination pile",
        "[10.1.1] if the new cell is a game-end cell: call check_game_end_triggers(after_token_move)"],
       ["ERR_NO_TOKEN"],
       reads=S("market_stack"), writes=S("market_stack"), calls=D("token_cell") + A("check_game_end_triggers"), consts=C("market_grid"))

derived("token_cell", "market", "Token cell", "Cell where a company's token sits.", ["company c"], "[1.6.1] the cell whose pile in market_stack contains c", reads=S("market_stack"), returns="cell")
derived("current_price", "market", "Current price", "Share price of a company.", ["company c"], "[1.6.1] grid_value(token_cell(c))", calls=D("token_cell"), consts=C("market_grid"), returns="int")
derived("in_yellow", "market", "In yellow zone?", "True if the company's token is on a yellow cell.", ["company c"], "[1.6.5, 4.2.3] token_cell(c) in yellow_cells; false if the company has no token", calls=D("token_cell"), consts=C("yellow_cells"), returns="bool")
derived("start_cell", "market", "Start cell for a price", "Cell used to start a company at a given price.", ["price"], "[1.6.3, 1.6.4] const.start_cells[price]", consts=C("start_cells", "start_values"), returns="cell")
derived("descending_order", "market", "Descending share price order", "Sort companies by share price order.", ["set of companies"],
        "[1.6.2] sort by key (-price, -col, pile_index_from_top); price desc; same price -> larger column first; same cell -> topmost first; (assumption A26: same price and same column in different rows -> upper row first)",
        reads=S("market_stack"), calls=D("current_price", "token_cell"), returns="list<company>")
derived("operating_order", "market", "Operating order", "Order in which started companies run in an operating round.", ["none"],
        "[5.2.1] floated minors (minor_director != null and token on market) in descending_order, then floated majors in descending_order",
        reads=S("market_stack", "minor_director", "major_status"), calls=D("descending_order"), returns="list<company>")
derived("next_operating_company", "market", "Next company to operate", "Choose the next company after the previous one finished.", ["set of companies already run this OR"],
        "[5.2.2] recompute operating_order now (stock sales during OR may reorder) and take the first company not in done; minors before majors", calls=D("operating_order"), returns="company|null")
derived("is_game_end_cell", "market", "Game-end cell?", "True if the company's token is on a game-end cell.", ["company c"], "[10.1.1] token_cell(c) in game_end_cells", calls=D("token_cell"), consts=C("game_end_cells"), returns="bool")

# ================================================================ bidding
derived("face_value", "bidding", "Face value of an item", "Minimum opening bid for the item kind.", ["item"], "[3.4.2, 3.1.3, R1] concession 100; minor 100; private 0", consts=C("face_values"), returns="int")
derived("highest_bid", "bidding", "Highest bid", "Highest bid placed on an item.", ["item"], "[4.10.7] max over bids[item].values(), or none", reads=S("bids"), returns="int|null")
derived("highest_bidder", "bidding", "Highest bidder", "Player with the highest bid on an item.", ["item"], "[4.10.7] argmax of bids[item]; unique because every new bid must be higher", reads=S("bids"), returns="player|null")
derived("committed_money", "bidding", "Committed money", "Money a player is committed to pay for items they lead.", ["player p"],
        "[4.10.7] sum of highest_bid(item) over items with highest_bidder(item)==p; outbid items do not count", calls=D("highest_bid", "highest_bidder"), reads=S("bids"), returns="int")
derived("items_led", "bidding", "Items led", "Number of items on which the player has the highest bid.", ["player p"], "[4.2.5] count of items with highest_bidder(item)==p", calls=D("highest_bidder"), reads=S("bids"), returns="int")
derived("tokens_total", "bidding", "Bidding tokens per player", "Tokens each player has.", ["none"], "[4.10.3, 1.7.2] const.bidding_tokens[player_count] (table missing)", reads=S("player_count"), consts=C("bidding_tokens"), returns="int")
derived("tokens_used", "bidding", "Tokens in use", "Tokens a player currently has on items, led or outbid.", ["player p"], "[4.10.10] count of items with p in bids[item] (tokens stay until resolution)", reads=S("bids"), returns="int")
derived("min_legal_bid", "bidding", "Minimum legal bid", "Smallest bid currently legal on an item.", ["item"], "[4.10.6, 4.10.7, R1] face_value(item) if no bids else highest_bid(item)+5", calls=D("face_value", "highest_bid"), returns="int")
derived("bid_amount_valid", "bidding", "Is the bid amount valid?", "All amount-related checks shared by place_bid and move_bid.", ["player p", "item", "amount"],
        "[4.10.6, 4.10.7, 4.10.9] amount % 5 == 0 and amount >= min_legal_bid(item) and committed_money(p) + amount <= player_cash[p] (p does not currently lead the item, so it is not double counted); no upper bound",
        reads=S("player_cash"), calls=D("min_legal_bid", "committed_money"), consts=C("bid_rules"), returns="bool")

BID_PRE = [
    ("turn.active_player = player; turn.stage <= C_main; turn.c_used in {none, bid} (bidding is exclusive with buy/convert)", "4.1.4"),
    ("turn.bids_made < 3", "4.10.5"),
    ("item sits in a bid box (kind and box exist); concession items only while phase < 5", "R9"),
    ("player_loans[player] = 0", "4.3.1"),
    ("not must_sell(player)", "R10"),
    ("cert_count(player) < cert_limit (leading bids count; applies to privates too)", "4.10.8"),
    ("bid_amount_valid(player,item,amount)", "4.10.6"),
]
action("place_bid", "bidding", "Place a bid", "Put an unallocated bidding token on an item at a new bid value.",
       ["player", "item", "amount"],
       BID_PRE + [("tokens_used(player) < tokens_total", "4.10.3"), ("player has no token on this item yet (one token per player per item; assumption A5)", "4.10.4"),
                  ("item is a private, a concession or a minor: all only obtainable by bidding", "3.1.4")],
       ["[4.10.4] bids[item][player] = amount",
        "turn.bids_made += 1; turn.c_used = bid; turn.acted = true",
        "[4.2.5] player now counts one more certificate (leading bid)"],
       ["ERR_C_ALREADY_USED", "ERR_TOO_MANY_BIDS", "ERR_ITEM_NOT_IN_BOX", "ERR_LOANS", "ERR_MUST_SELL", "ERR_CERT_LIMIT", "ERR_BAD_AMOUNT", "ERR_NO_TOKENS", "ERR_ALREADY_HAS_TOKEN"],
       reads=S("turn", "player_loans", "box_contents", "phase", "bids"), writes=S("bids", "turn"),
       calls=D("must_sell", "cert_count", "cert_limit", "bid_amount_valid", "tokens_used", "tokens_total"))

action("move_bid", "bidding", "Move a bid up", "Move an already placed token to a higher empty space on the same item.",
       ["player", "item", "new_amount"],
       BID_PRE + [("player already has a token on item and is NOT the highest bidder (another player has a higher bid)", "4.10.4"),
                  ("a token cannot be withdrawn or moved to another item", "4.10.10")],
       ["[4.10.4] bids[item][player] = new_amount (token moves; the old space becomes empty)",
        "turn.bids_made += 1; turn.c_used = bid; turn.acted = true",
        "player now leads the item: committed money and certificate count rise"],
       ["ERR_C_ALREADY_USED", "ERR_TOO_MANY_BIDS", "ERR_NOT_OUTBID", "ERR_NO_TOKEN_ON_ITEM", "ERR_LOANS", "ERR_MUST_SELL", "ERR_CERT_LIMIT", "ERR_BAD_AMOUNT"],
       reads=S("turn", "player_loans", "box_contents", "phase", "bids"), writes=S("bids", "turn"),
       calls=D("must_sell", "cert_count", "cert_limit", "bid_amount_valid", "highest_bidder"))

# ================================================================ bid_boxes
action("shift_boxes", "bid_boxes", "Compact boxes", "Shift items to the lowest-numbered boxes of their kind, preserving order.", ["none"],
       [("applies to every kind separately", "4.10.2")],
       ["[4.10.2, 4.11.8] for each kind: items in boxes 1..m moved to the lowest-numbered boxes in the same relative order"],
       [], reads=S("box_contents"), writes=S("box_contents"), consts=C("box_counts"))

action("refill_boxes", "bid_boxes", "Refill boxes", "Shift then fill empty boxes from the stacks, lowest box first.", ["none"],
       [("concession kind skipped when phase >= 5", "R9")],
       ["[4.10.2] call shift_boxes",
        "[1.7.7, 4.1.1] for kind in (minor, concession, private): for each empty box lowest first: pop the top of the kind's stack into the box; stop when the stack is empty",
        "[R9] when phase >= 5 concession boxes stay empty and concession_stack stays empty"],
       [], reads=S("phase", "concession_stack", "minor_stack", "private_stack", "box_contents"), writes=S("concession_stack", "minor_stack", "private_stack", "box_contents"),
       calls=A("shift_boxes"), consts=C("box_counts"))

action("clear_concession_boxes", "bid_boxes", "Clear concessions at phase 5", "Remove all concessions from play when phase 5 starts.", ["none"],
       [("called only when phase just reached >= 5", "2.2.8")],
       ["[R9] concession boxes emptied; concession_stack emptied; all concessions added to removed_items",
        "[R9, 3.4.5] player_concessions[p] = empty for every player (no refund; certificate counts drop)"],
       [], reads=S("concession_stack", "box_contents", "player_concessions"), writes=S("concession_stack", "box_contents", "player_concessions", "removed_items"))

action("vacate_box_item", "bid_boxes", "Take an item out of its box", "Remove the item from its box and give it to a player or remove it from play.", ["item", "disposition in {award(player), remove}"],
       [("item currently sits in a box", "4.11.2")],
       ["[4.11.2] box_contents[kind][box] = null",
        "award: concession -> player_concessions; private -> player_privates; minor -> minor_director[m] = player",
        "remove: removed_items += item"],
       ["ERR_ITEM_NOT_IN_BOX"],
       reads=S("box_contents"), writes=S("box_contents", "player_concessions", "player_privates", "minor_director", "removed_items"))

# ================================================================ phase_trains
derived("phase_of_train", "phase_trains", "Phase of a train type", "Phase triggered by the first train of a type.", ["train type"], "[2.2.3-2.2.8] const.phase_table (L/2 exported or bought as 2-train -> 2)", consts=C("phase_table"), returns="int")
derived("front_train", "phase_trains", "Front train of the deck", "Next available new train.", ["none"], "[R7] train_deck[0] or null if empty", reads=S("train_deck"), returns="train type|null")

action("phase_check", "phase_trains", "Phase check", "Advance the phase if this is the first train of its type.", ["train type"],
       [("train type in {2,3,4,5,6,7,E}; an L-train never triggers a phase", "2.1.1")],
       ["[2.1.1] new = phase_of_train(type)",
        "if new > phase: phase = new; append event {from, to, rusted = rust_table[new], trains_limit_check, or_per_sr} to phase_events [2.1.2-2.1.5]",
        "[2.2.8, R9] if new >= 5: trigger clear_concession_boxes"],
       [], reads=S("phase"), writes=S("phase", "phase_events"), calls=D("phase_of_train") + A("clear_concession_boxes"), triggers=A("clear_concession_boxes"), consts=C("rust_table", "phase_table"))

action("export_train", "phase_trains", "Export a train", "Remove a train from the bank deck (not the pool); exported trains leave the game.", ["mode in {L_only, next_with_phase}"],
       [("deck not empty (else no action)", "4.11.6")],
       ["mode L_only [4.11.6, R7]: if front is L/2: pop it; counts as an L-train: NO phase check; if no L/2 remains: no action",
        "mode next_with_phase [4.11.7, R7]: pop the front train (L/2 while any remain, then 3, 4, ...); effective type = 2 for an L/2 train else its type; call phase_check(effective type)"],
       [], reads=S("train_deck"), writes=S("train_deck"), calls=D("front_train") + A("phase_check"), triggers=A("phase_check"), consts=C("train_deck"))

# ================================================================ sr_resolution
derived("item_resolution_order", "sr_resolution", "Item payment order", "Order in which items with bids are paid for.", ["none"],
        "[4.11.2] items with >=1 bid sorted by (highest bid desc, box number asc, kind order minor<concession<private) -- assumption A16", reads=S("bids", "box_contents"), calls=D("highest_bid"), returns="list<item>")
derived("minor_start_price", "sr_resolution", "Minor start price", "Starting share price of a purchased minor.", ["phase", "bid"],
        "[4.11.4, R2] phase 1: 50; phase >=2: max{v in {50,60,...,100} : v <= floor(bid/2)}, min 50, max 100", consts=C("start_values"), returns="int")
derived("minor_start_treasury", "sr_resolution", "Minor starting treasury", "Cash a purchased minor receives.", ["phase", "bid", "price"],
        "[4.11.4, R3] phase 1: 100; phase 2: 2*price; phase >=3: bid", returns="int")
derived("minor_float_order", "sr_resolution", "Minor flotation order", "Order in which purchased minors are floated.", ["list of pending minors"],
        "[4.11.3] sort by bid desc, tie -> lower box number", reads=S("pending_minor_floats"), returns="list")
derived("interest_amount", "sr_resolution", "Interest", "Interest added to a loan.", ["loans L"], "[R14, 4.3.4] ceil(L/2) = (L+1)//2", consts=C("interest"), returns="int")
derived("compute_stock_round_order", "sr_resolution", "Compute next stock round order", "Next round's player order from cash.", ["cash map", "previous order"],
        "[4.11.9] sort players by cash descending; equal cash keeps relative order of the previous sr_order; P9 deferred", reads=S("player_cash", "sr_order"), returns="list<player>")

action("resolve_stock_round", "sr_resolution", "Resolve stock round", "Orchestrate the end-of-round procedure (steps in seq order).", ["none"],
       [("drv.sr_over (all players passed consecutively)", "4.11.1")],
       ["step1 [4.11.2] resolve_bids", "step2 [4.11.3-4.11.5] float_minors", "step3 [4.11.6] unsold_minor_exports", "step4 [4.11.7] remove_box1_minor_and_export",
        "step5 [4.11.8, 4.10.2] refill_boxes (shift then fill)", "step6 [4.11.10] charge_interest", "step7 [4.12] raise_sold_out_prices",
        "step8 [4.11.9] reorder_players_by_cash", "step9 [10.1.1] check_game_end_triggers(end_of_stock_round); sr_status = finished"],
       ["ERR_NOT_OVER"],
       reads=S("sr_status"), writes=S("sr_status"), calls=A("resolve_bids", "float_minors", "unsold_minor_exports", "remove_box1_minor_and_export", "refill_boxes", "charge_interest", "raise_sold_out_prices", "reorder_players_by_cash", "check_game_end_triggers") + D("sr_over"),
       triggers=A("resolve_bids", "float_minors", "unsold_minor_exports", "remove_box1_minor_and_export", "refill_boxes", "charge_interest", "raise_sold_out_prices", "reorder_players_by_cash", "check_game_end_triggers"))

action("resolve_bids", "sr_resolution", "Pay and award box items", "Award each item with bids to the highest bidder who can pay; remove tokens.", ["none"],
       [("sr_status = resolving", "4.11.1")],
       ["items_with_bids = every item with >=1 token (snapshot before clearing)",
        "for item in item_resolution_order: for bidders by amount desc: first with player_cash >= amount wins [R8]: player_cash -= amount; bank_cash += amount [R3]; call vacate_box_item(item, award(bidder)); sale_happened = true [R6 provisional]; minors also appended to pending_minor_floats (minor, bid, box, buyer)",
        "[R8] if nobody can pay the item stays in its box (it still counts as having had a bid)",
        "[4.11.2] bids = empty (all tokens removed)"],
       [],
       reads=S("bids", "box_contents", "player_cash"), writes=S("items_with_bids", "player_cash", "bank_cash", "sale_happened", "pending_minor_floats", "bids"),
       calls=A("vacate_box_item") + D("item_resolution_order"))

action("float_minors", "sr_resolution", "Float purchased minors", "Start each purchased minor: price, treasury, token.", ["none"],
       [("flotation uses the phase at resolution time, before this round's exports", "4.11.4")],
       ["[4.11.3] for pending in minor_float_order: price = minor_start_price(phase,bid); treasury = minor_start_treasury(phase,bid,price)",
        "[4.11.5] call place_start_token(minor, price, minor)",
        "[R3] bank_cash -= treasury; company_cash[minor] = treasury (buyer already paid the full bid to the bank)",
        "[10.1.1] call check_game_end_triggers(after_bank_payment)"],
       [], reads=S("pending_minor_floats", "phase", "minor_director"), writes=S("company_cash", "bank_cash"),
       calls=D("minor_float_order", "minor_start_price", "minor_start_treasury") + A("place_start_token", "check_game_end_triggers"))

action("unsold_minor_exports", "sr_resolution", "Export per unbid minor", "One L/2 train exported for each remaining minor box item that had no bid.", ["none"],
       [("after float_minors", "4.11.6")],
       ["[4.11.6] for each minor still in a box and not in items_with_bids: call export_train(L_only)"],
       [], reads=S("box_contents", "items_with_bids"), calls=A("export_train"), triggers=A("export_train"))

action("remove_box1_minor_and_export", "sr_resolution", "Remove unsold box-1 minor", "Remove the unsold minor in minor box 1 and export the next train.", ["none"],
       [("minor box 1 still holds a minor after resolution (unsold; assumption A15 includes unpaid items)", "4.11.7")],
       ["[4.11.7] vacate_box_item(minor, remove); call export_train(next_with_phase)"],
       [], reads=S("box_contents"), calls=A("vacate_box_item", "export_train"), triggers=A("export_train"))

action("charge_interest", "sr_resolution", "Charge loan interest", "Add 50% interest to every player's loans.", ["none"],
       [("applies only to players with loans > 0", "4.3.4")],
       ["[R14, 4.11.10] for each player with loans > 0: loans += interest_amount(loans)", "[4.3.5] bank_cash unchanged"],
       [], reads=S("player_loans"), writes=S("player_loans"), calls=D("interest_amount"), consts=C("interest"))

action("raise_sold_out_prices", "sr_resolution", "Raise sold-out companies", "Move up one cell every 100%-sold major.", ["none"],
       [("only floated majors; minors never qualify", "4.12.3")],
       ["[4.12.1, R13] affected = floated majors with fully_sold(c)", "[4.12.2] order = descending_order(affected) computed once before any move",
        "[4.12.2] for c in order: call move_token_up(c)"],
       [], reads=S("major_status"), calls=D("fully_sold", "descending_order") + A("move_token_up"))

action("reorder_players_by_cash", "sr_resolution", "Reorder players by cash", "Set the next round's player order by cash.", ["none"],
       [("after bid payments", "4.11.9")],
       ["[4.11.9] sr_order = compute_stock_round_order(player_cash, sr_order)"],
       [], reads=S("player_cash", "sr_order"), writes=S("sr_order"), calls=D("compute_stock_round_order"))

# ---------------------------------------------------------------- order edges
ORDER = {
    "resolve": ["resolve_bids", "float_minors", "unsold_minor_exports", "remove_box1_minor_and_export", "refill_boxes", "charge_interest", "raise_sold_out_prices", "reorder_players_by_cash", "check_game_end_triggers"],
}

# ---------------------------------------------------------------- build edges
comp_of = {}
for nid, comp, reads, writes, calls, trig, consts, pre, eff, text in ACTS:
    comp_of[nid] = comp
for nid, comp, reads, calls, consts, formula, text in DRVS:
    comp_of[nid] = comp
for nid, comp in comp_of.items():
    edge(nid, "comp." + comp, "member_of", "")

for nid, comp, reads, writes, calls, trig, consts, pre, eff, text in ACTS:
    for s in reads:
        edge(nid, s, "reads", "", cross_component=(STATE_OWNER[s] != comp))
    for s in writes:
        edge(nid, s, "writes", "", cross_component=(STATE_OWNER[s] != comp))
    for c in calls:
        edge(nid, c, "calls", "", cross_component=(comp_of[c] != comp))
    for c in trig:
        edge(nid, c, "triggers", "", cross_component=(comp_of[c] != comp))
    for c in consts:
        edge(nid, c, "uses_constant", "")
    found = set()
    for chk, r in (pre if pre and isinstance(pre[0], tuple) else []):
        if r:
            found.add(r)
        found.update(refs_in(chk))
    for e_ in eff:
        found.update(refs_in(e_))
    found.update(refs_in(text))
    for r in found:
        edge(rid(r), nid, "constrains", "demanded in preconditions/effects")

for nid, comp, reads, calls, consts, formula, text in DRVS:
    for s in reads:
        edge(nid, s, "reads", "", cross_component=(STATE_OWNER[s] != comp))
    for c in calls:
        edge(nid, c, "calls", "", cross_component=(comp_of[c] != comp))
    for c in consts:
        edge(nid, c, "uses_constant", "")
    for r in set(refs_in(formula)) | set(refs_in(text)):
        edge(rid(r), nid, "constrains", "formula")

for k, seq_names in ORDER.items():
    for i in range(len(seq_names) - 1):
        edge("act." + seq_names[i], "act." + seq_names[i + 1], "order", "inside resolve_stock_round: seq %d runs before seq %d" % (i + 1, i + 2), seq=i + 1)
edge("act.sell_shares", "act.repay_loans", "order", "turn step A before B", seq=1)
for t in ("buy_share", "convert_concession", "place_bid", "move_bid"):
    edge("act.repay_loans", "act." + t, "order", "turn step B before C", seq=2)
for n_, a_ in enumerate(ORDER["resolve"]):
    pass

for rid_, (targets, refers) in RULES.items():
    for t in targets:
        assert t in N, (rid_, t)
        edge(rid(rid_), t, "constrains", "")
    for r in refers:
        assert rid(r) in N, (rid_, r)
        edge(rid(rid_), rid(r), "refers", "")
for ruid, (ovr, cons) in RULINGS.items():
    for r in ovr:
        assert rid(r) in N, (ruid, r)
        edge("ruling." + ruid, rid(r), "overrides", "overrides or completes")
    for t in cons:
        assert t in N, (ruid, t)
        edge("ruling." + ruid, t, "constrains", "")

# ---- annotate states with accessor components
acc = collections.defaultdict(lambda: {"readers": set(), "writers": set()})
for e in E:
    if e["type"] in ("reads", "writes") and e["dst"].startswith("st."):
        acc[e["dst"]]["readers" if e["type"] == "reads" else "writers"].add(comp_of[e["src"]])
for sid in STATE_OWNER:
    a = acc[sid]
    N[sid]["attrs"]["reader_components"] = sorted(a["readers"])
    N[sid]["attrs"]["writer_components"] = sorted(a["writers"])
    N[sid]["attrs"]["shared"] = len(a["readers"] | a["writers"] | {STATE_OWNER[sid]}) > 1
out = {"nodes": list(N.values()), "edges": E}
json.dump(out, open("/home/claude/graphrun/out/graph.json", "w"), indent=1, ensure_ascii=False)
cnt = collections.Counter(n["type"] for n in N.values())
ecnt = collections.Counter(e["type"] for e in E)
print("nodes", dict(cnt), sum(cnt.values()))
print("edges", dict(ecnt), sum(ecnt.values()))
