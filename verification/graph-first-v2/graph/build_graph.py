#!/usr/bin/env python3
"""Generator for graph.json v2 (1822 stock round + trains/phases + round flow; node types incl. api, repr, decision).
Source of truth is the data below; run: python3 build_graph.py (writes graph.json, GAP_RESOLUTION.md, stats.json next to this file)."""
import json, re, sys, os, collections

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
    return ("ruling." + x) if re.match(r"^R\d+b?$", x) else ("rule." + x)


REF = re.compile(r"\[([^\]]*)\]")
RID = re.compile(r"^(R\d+b?|\d+\.\d+\.\d+)$")


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
const("start_values", "Start values", "Allowed starting share prices: 50 (solid red, minors only, 1.6.3), 60, 70, 80, 90, 100 (red-outlined, majors and minors, 1.6.4). Major start price must be in {60..100}.",
      minor_values=[50, 60, 70, 80, 90, 100], major_values=[60, 70, 80, 90, 100])
const("face_values", "Face values", "Face value: concession 100 (3.4.2), minor 100 (R1), private 0 (3.1.3). Opening bid >= face value (4.10.6).",
      table={"concession": 100, "minor": 100, "private": 0})
const("box_counts", "Bid box counts", "4 minor boxes, 3 concession boxes, 3 private boxes (4.10.1). Box numbers start at 1.", table={"minor": 4, "concession": 3, "private": 3})
const("bid_rules", "Bid rule numbers", "Bids are whole multiples of 5 (4.10.6); at most 3 bids placed/moved per stock turn (4.10.5); no upper bound on a bid (4.10.9).", multiple=5, max_bids_per_turn=3)
const("share_structure", "Share structure of a major company", "Total 10 units. Standard major: director's certificate = 2 units, 8 ordinary certificates of 1 unit. LNWR: director's certificate = 1 unit, 9 ordinary certificates. Minor: one director's certificate worth 2 shares, no other shares (3.2.2). Pool cap 5 units (4.4.2); player cap 6 units (4.5.6).",
      total_units=10, standard={"director_units": 2, "ordinary_certs": 8}, lnwr={"director_units": 1, "ordinary_certs": 9}, pool_cap_units=5, hold_cap_units=6)
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
state("player_cash", "Player cash", "int map player->int", "per player", "pounds (integer)", "sr_flow", "Cash in hand of each player. Never negative.", "player")
state("player_loans", "Player loans", "int map player->int", "per player", "pounds", "share_trading",
      "Outstanding loans of each player. Created by operating-round forced train purchase / emergency money raising (out of scope); reduced by repay_loans; increased by interest.", "loan",
      external="Increases from forced train purchases are provided by the operating-round module (5.14/5.15, out of scope); this graph writes only repay and interest.")
state("bank_cash", "Bank cash", "int (can go below zero)", "game", "pounds", "sr_flow", "Cash of the bank. Starts 9900. 'Broken' when < 0 (assumption A29). Loans are NOT part of it (4.3.5).", "bank")
state("phase", "Game phase", "int 1..7", "game", "phase number", "phase_trains", "Current phase; starts at 1 (2.2.2); advances when the first train of a type is bought or exported (2.1.1).", "game")
state("pass_streak", "Consecutive passes", "int", "stock round", "turns", "sr_flow", "Number of consecutive turns that were passes; round ends when it equals the player count (4.11.1).", "game")
state("ordinary_certs", "Ordinary certificates held", "int map (player, major)->int", "per player per major company", "certificates = units of 10% (ordinary share = 1 unit)", "certificates",
      "Number of ordinary 10% certificates a player holds in a major company. EXCLUDES the director's certificate, which is stored in director_holder. units_held = ordinary_certs + director units; certs_held = ordinary_certs + (1 if director).", "share_certificate")
state("director_holder", "Director's certificate holder", "map major->player|null", "per major company", "-", "certificates",
      "Holder of the director's certificate of a major company (null until the company is started). The director's certificate = cert_units units (2; LNWR 1) but ONE certificate for limit counting.", "director_certificate")
state("treasury_shares", "Treasury shares", "int map major->int", "per major company", "ordinary certificates = units of 10%", "certificates", "Ordinary certificates in the company treasury, buyable at the current price (4.5.1, 4.7.3). 8 (LNWR 9) at flotation.", "company_treasury")
state("pool_shares", "Bank-pool shares", "int map major->int", "per major company", "ordinary certificates = units of 10%", "certificates", "Ordinary certificates in the bank pool. Max 5 (50%) (4.4.2).", "bank_pool")
state("major_status", "Major company status", "map major->enum {unstarted, floated}", "per major company", "-", "share_trading", "Floated once its concession is converted (4.7.3). Phase-5 direct formation deferred (R11).", "major_company")
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








# ================================================================ share_trading




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
derived("cert_count_holdings", "certificates", "Certificates held counted against the limit", "Certificates a player owns that count toward the limit.", ["player p"],
        "[4.2.2, 3.1.5, 3.4.3, 4.2.3] sum over majors and minors c of (0 if in_yellow(c) else certs_held(p,c)) + |player_privates[p]| + |player_concessions[p]| (P16 not exempted, R11)",
        reads=S("player_privates", "player_concessions"), calls=D("certs_held", "in_yellow"), returns="int")
derived("cert_count", "certificates", "Certificate count incl. leading bids", "Count used for every 'at the limit' test.", ["player p"],
        "[4.2.5, 4.10.8] cert_count_holdings(p) + items_led(p)", calls=D("cert_count_holdings", "items_led"), returns="int")
derived("over_limit", "certificates", "Over the limit?", "True when a player holds more than the limit.", ["player p"], "[4.2.6, 4.4.7] cert_count(p) > cert_limit", calls=D("cert_count", "cert_limit"), returns="bool")
derived("successor", "certificates", "Eligible successor director", "Player who would become director if the director's remaining holding is r.", ["major c", "director d", "remaining units r"],
        "[4.4.2, R5] candidates = {q != d : units_held(q,c) >= cert_units(c) and units_held(q,c) > r}; none -> null; else max units_held; tie -> the tying player closest after d in sr_order (cyclic, forward)",
        reads=S("sr_order"), calls=D("units_held", "cert_units"), returns="player|null")
derived("can_sell_any", "certificates", "Able to sell anything?", "True if at least one sale of one share is legal.", ["player p"], "[4.4.7] exists major c: sale_legal(p,c,1).legal", reads=S("major_status"), calls=D("sale_legal"), returns="bool")
derived("must_sell", "certificates", "Forced to sell?", "True when over the limit and able to sell.", ["player p"], "[4.4.7, R10] over_limit(p) and can_sell_any(p)", calls=D("over_limit", "can_sell_any"), returns="bool")
derived("fully_sold", "certificates", "Company 100% in players' hands?", "Sold-out test for the price rise.", ["major c"],
        "[4.12.1, R13, 4.12.3] major_status[c]==floated and treasury_shares[c]==0 and pool_shares[c]==0 (minors: always false)", reads=S("major_status", "treasury_shares", "pool_shares"), returns="bool")

# ================================================================ market

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
derived("descending_order", "market", "Descending share price order", "Sort companies by share price order.", ["set of companies"],
        "[1.6.2] sort by key (-price, -col, pile_index_from_top); price desc; same price -> larger column first; same cell -> topmost first; (assumption A26: same price and same column in different rows -> upper row first)",
        reads=S("market_stack"), calls=D("current_price", "token_cell"), returns="list<company>")
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


# ================================================================ phase_trains
derived("phase_of_train", "phase_trains", "Phase of a train type", "Phase triggered by the first train of a type.", ["train type"], "[2.2.3-2.2.8] const.phase_table (L/2 exported or bought as 2-train -> 2)", consts=C("phase_table"), returns="int")



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




# ##################################################################################################
# ################################  V2 LAYER: corrections, new scope, new node kinds  ##############
# ##################################################################################################
# Everything above this line is the v1 data that survived unchanged; nodes that v2 changes were removed from
# the v1 text and are re-defined below (same ids where the concept is the same).  New node types (api, repr,
# decision) and the new edge types (implements, binds, resolves, supersedes) are created at the end.

# ---------------------------------------------------------------- generic helpers (v2)
def setattrs(nid, **kw):
    N[nid]["attrs"].update(kw)


def settext(nid, text=None, label=None):
    if text is not None:
        N[nid]["text"] = text
    if label is not None:
        N[nid]["label"] = label


def add_targets(rule_id, targets):
    for t in targets:
        if t not in RULES[rule_id][0]:
            RULES[rule_id][0].append(t)


# ---------------------------------------------------------------- component / entity patches
settext("comp.sr_flow", label="Round engine, setup, game end, ledger",
        text="Owns game setup (given new_game), the stock-round AND operating-round state machines (turn record, pass streak, round type, "
             "operating-round set bookkeeping, operating order), player order state, cash and bank ledger, the 'a sale happened' flag, game-end "
             "triggers and their maturity, start-of-operating-round revenues (private companies, concessions), wealth and final ranking.")
settext("comp.phase_trains", label="Phase, train deck, train purchase",
        text="Owns game phase, the bank train deck and bank pool, company train lists: buying trains from the bank in order, side choice L/2 and 7/E, "
             "train limit, one-E-train limit, L->2 upgrade, phase advance, rusting, discard of excess trains, train exports, concession clearing trigger.")
node("ent.operating_round", "entity", "operating round",
     "An operating round: step A revenues, then minors, then majors run in descending share price order (5.2.1). After each stock round there is a SET of 1 or 2 operating rounds (5.1.1); the set size is locked when the set starts.")

# ---------------------------------------------------------------- constants (v2): all values now present in given data tables
const("cert_limit", "Certificate limit table", "Certificate limit per player count (4.2.1, 1.7.2). The rulebook shows only column headers; the values are in the given data table.",
      table={"3": 26, "4": 20, "5": 16, "6": 13, "7": 11}, missing=False, source="1.7.2/4.2.1", source_in_code="app.data.setup.SETUP_BY_PLAYER_COUNT[n].certificate_limit")
const("bidding_tokens", "Bidding tokens per player count", "Bidding tokens per player by player count (1.7.2, 4.10.3); values from the given data table.",
      table={"3": 6, "4": 5, "5": 4, "6": 3, "7": 3}, missing=False, source="1.7.2/4.10.3", source_in_code="app.data.setup.SETUP_BY_PLAYER_COUNT[n].bidding_tokens")
const("market_grid", "Stock market grid", "The printed market: grid of cells (row, col), rows left-aligned (R12); value in pounds; down = (row+1, col), up = (row-1, col); a cell exists iff its key is in the table; absent cell = no move.",
      missing=False, source="1.6.1/R12", source_in_code="app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)")
const("yellow_cells", "Yellow zone cells", "Cells of the yellow zone (1.6.5): StockCell.zone == 'yellow' (39 cells).", missing=False, source_in_code="StockCell.zone == 'yellow'")
const("game_end_cells", "Game-end cells", "Cells carrying the game-end value (10.1.1): StockCell.game_end is True (only (0,3), value 700).", missing=False, source_in_code="StockCell.game_end is True")
const("start_cells", "Start cells", "Start cells: cells with zone 'start' or 'minor_start'; price -> cell: 100->(4,4), 90->(5,4), 80->(6,4), 70->(7,4), 60->(8,4), 50->(9,4) (50 minors only).",
      missing=False, table={"100": [4, 4], "90": [5, 4], "80": [6, 4], "70": [7, 4], "60": [8, 4], "50": [9, 4]}, source_in_code="cells with zone in {'start','minor_start'}; derive at import, do not hard-code")
const("train_deck", "Train deck composition", "Deck order, front first: double-sided L/2 (22), 3 (9), 4 (6), 5 (3), 6 (3), double-sided 7/E (16) (1.7.11). Stored as counts per code; "
      "a double-sided group is ONE physical pool: remaining(group) = sum of its codes' counts; a card leaves by decrementing the first non-zero code in group order (L before 2; 7 before E).",
      missing=False, groups=[["L", "2"], ["3"], ["4"], ["5"], ["6"], ["7", "E"]], initial_counts={"L": 22, "2": 0, "3": 9, "4": 6, "5": 3, "6": 3, "7": 16, "E": 0},
      source_in_code="app.engine.setup.new_game: bank.train_pool; app.data.trains.TRAIN_TYPES")
const("phase_table", "Phase table", "Phase of the first train of a type: 2-train (bought, or L upgraded) -> 2; 3 -> 3; 4 -> 4; 5 -> 5; 6 -> 6; 7 or E -> 7 (2.2.3-2.2.8). An L-train never starts a phase. "
      "Per phase: train limits (minor/major) 1:2/4 2:2/4 3:2/4 4:1/3 5:1/2 6:1/2 7:1/2; operating rounds per stock round 1:1, 2..7:2; rust 3:L 4:2 6:3 7:4; phase 5 removes concessions (R9).",
      table={"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}, train_limits={"1": [2, 4], "2": [2, 4], "3": [2, 4], "4": [1, 3], "5": [1, 2], "6": [1, 2], "7": [1, 2]},
      ors_per_sr={"1": 1, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2}, missing=False, source_in_code="app.data.phases.PHASES_BY_NUMBER; trains.TRAIN_PHASE (L absent)")
const("train_costs", "Train costs", "Face value of each train type (5.13.4: price paid must be the face value): L 60, 2 120, 3 200, 4 300, 5 500, 6 600, 7 750, E 1000; L->2 upgrade 80 (5.13.9).",
      table={"L": 60, "2": 120, "3": 200, "4": 300, "5": 500, "6": 600, "7": 750, "E": 1000}, l_to_2_upgrade=80, source_in_code="app.data.trains.TRAIN_TYPES_BY_CODE[code].cost; L_TO_2_UPGRADE_COST")
const("private_revenue_table", "Private company revenue table", "Fixed revenue of a private company per operating round (3.1.2): from app.data.private_companies revenue strings: '£N' -> N; '£Nx phase' -> N * phase (P15). Base-game P1..P18.",
      table={"1": "5", "2": "10", "3": "0", "4": "0", "5": "10", "6": "10", "7": "10", "8": "10", "9": "10", "10": "10", "11": "10", "12": "10", "13": "10", "14": "10", "15": "10xphase", "16": "0", "17": "10", "18": "10"},
      source_in_code="app.data.private_companies.PRIVATE_COMPANIES_BY_NUMBER[n].revenue (string)")
const("concession_dividend", "Concession dividend", "A held concession pays 10 per operating round to its owner (3.4.4).", value=10, source="3.4.4")
const("game_end_triggers", "Game-end trigger values", "Stored trigger values (models.GameState.end_trigger_pending): 'next_or' (trigger during a stock round: game ends after exactly one more OR), 'or_end' (token on game-end cell during an OR: ends after that OR), 'or_set_end' (bank broken during an OR: ends after the current OR set). game_over=True = ended.",
      values=["next_or", "or_end", "or_set_end"], source="10.1.1")

# ---------------------------------------------------------------- states (v2)
state("sr_order", "Stock-turn order", "list<player>", "game", "player ids, index 0 = Player 1 card", "sr_flow",
      "Order in which players take stock turns; random at setup (1.7.12); recomputed by cash at each stock-round end (4.11.9). Also the direction for 'nearest after' tie-breaks (4.4.2). The player holding card 1 (index 0) is the start player of every stock round.", "player_order_card")
state("sr_completed", "Stock rounds completed", "int", "game", "rounds", "sr_flow",
      "Number of stock rounds that have finished their resolution (0 during the first stock round). Written ONLY by end_stock_round, after resolve_stock_round returned; so the 10.1.1 'first stock round' test is sr_completed == 0 inside resolution step 9.", "game")
state("round_type", "Round type", "enum {STOCK, OPERATING}", "game", "-", "sr_flow",
      "Which kind of round is running. The game is in a stock round from setup (round 1 is pre-started by new_game) until end_stock_round starts the first operating-round set, and so on alternately (1.7.14, 5.1.1). Replaces the v1 sr_status (no field exists for it).", "game")
state("turn", "Active turn record", "record {active_player, bids_made}", "game", "-", "sr_flow",
      "Whose stock turn it is and how many bids were already placed/moved in this turn. v2 follows the skeleton turn model: EVERY successful sell / buy / convert / bid action ends the turn; there is no stage, no c_used, no acted. bids_made is incremented by the CALLER (actions.py), never by the bidding module, and reset by begin_turn.", "game")
state("sale_happened", "A sale happened flag", "bool", "stock round", "-", "sr_flow",
      "Set true when a player buys a share, sells a share, converts a concession (R15, R6), or wins a bid-box item at resolution (R6b). Reset at stock-round start. Read by the 10.1.1 first-round nothing-sold test (R6b). Written by the module functions themselves (idempotent; the caller actions.py also sets it after buy and convert).", "game")
state("sold_this_round", "Sold-this-round map", "map player -> list<major company> (no duplicates)", "stock round", "pairs", "share_trading",
      "(player, company) pairs such that the player sold >=1 share of the company this stock round; blocks buying that company (4.5.5). Cleared at stock-round start. Stored as lists, not sets (JSON).", "player")
state("has_completed_or", "Has completed an operating round", "map major->bool", "per major company", "-", "share_trading",
      "True once the major company has completed one operating turn; shares cannot be sold before (4.4.2). Initial false at flotation (set false by convert_concession), set true by advance_company when the company finished its turn.", "major_company")
state("phase_events", "Phase-change log", "list<log line>", "game", "lines", "phase_trains",
      "Audit log of phase changes: one line per change with from, to, rusted codes, trains discarded, operating rounds per stock round. NOT a work queue: rust, train-limit discard and concession clearing are applied immediately inside phase_check (2.1.2-2.1.5).", "game",
      external="Audit only; consumers are UI and tests (state.log).")
state("train_deck", "Bank train deck", "map train code -> count (groups L/2 and 7/E share one physical pool)", "game", "trains", "phase_trains",
      "New trains in the bank (not the bank pool), as counts; front = first group (L/2, 3, 4, 5, 6, 7/E) with remaining > 0 (1.7.11). Trains must be bought in this order (5.13.4); exports take from the front (4.11.6/4.11.7).", "train")
state("bank_pool_trains", "Bank pool trains", "list<train code>", "game", "trains", "phase_trains",
      "Trains in the bank POOL (discarded for exceeding the train limit, 2.1.4); they keep their orientation (code). May be bought from phase 3 at face value (5.13.4, 2.2.4). Not to be confused with the bank pool of SHARES.", "train")
state("company_trains", "Company trains", "map company -> list<train code>", "per company", "trains", "phase_trains",
      "Trains owned by each minor and major company; the code records the orientation chosen at purchase (L or 2; 7 or E). Rusted trains vanish (2.1.3); excess trains go to bank_pool_trains (2.1.4).", "train")
state("items_with_bids", "Items that had a bid", "set<(kind, box_index)>", "call-scoped", "items", "sr_resolution",
      "Snapshot taken by resolve_bids of every item on which any token was placed (including items nobody could pay, R8); passed to unsold_minor_exports (4.11.6). Local return value, not stored.", "bid_box")
state("pending_minor_floats", "Minors awaiting flotation", "list<(minor_number, bid, box_index, buyer)>", "call-scoped", "-", "sr_resolution",
      "Minors paid for during resolve_bids, to be floated by float_minors in flotation order (4.11.3). Local return value, not stored.", "minor_company")
state("private_status", "Private company ownership/closure", "map private -> {owner_player | owner_company | none, closed bool}", "per private company", "-", "bid_boxes",
      "Who owns a private (player via Player.private_companies, company via PrivateCompanyState.owner_company_id) and whether it is closed; an open private pays its fixed revenue each OR (3.1.2). Players' side written by vacate_box_item; company acquisition and closing are out of scope (operating-round code).", "private_company",
      external="Acquisition by companies and closing of privates are written by operating-round code outside this graph; this graph only awards to players and reads.")
state("game_end", "Game end trigger", "record {trigger in {none, next_or, or_end, or_set_end}, over bool}", "game", "-", "sr_flow",
      "First trigger wins (10.1.2). over = game_over (immediate trigger or matured deferred trigger).", "game")
state("or_set_size", "Operating rounds in the current set", "int 1..2", "game", "rounds", "sr_flow",
      "Number of operating rounds in the set following the stock round; LOCKED when the set starts (models.operating_rounds_this_set; 2.1.2, 5.1.1); forced to 1 by a 'next_or' trigger (10.1.1).", "operating_round")
state("or_index", "Index of the running operating round", "int 0-based", "game", "rounds", "sr_flow", "Which operating round of the set is running (models.operating_round_index).", "operating_round")
state("or_order", "Operating order so far", "list<company>", "game", "companies", "sr_flow",
      "Companies already chosen to run in the current operating round, in running order; the next company is chosen only after the previous one finished (5.2.2) (models.operating_order).", "operating_round")
state("or_current", "Current company index", "int", "game", "index", "sr_flow", "Index into or_order of the company whose turn it is (models.current_company_index). active_company = or_order[or_current].", "operating_round")

# ---------------------------------------------------------------- rules (v2)
rule("2.2.1", "Phases never go back", "Once a phase introduces a rule it stays; the phase number only increases.", ["act.phase_check", "st.phase"])
rule("3.1.2", "Privates pay revenue", "While open, a private pays its fixed revenue (maybe 0) to its owner at the start of each operating round.", ["act.pay_private_revenues", "drv.private_revenue", "st.private_status", "const.private_revenue_table"], ["5.2.1"])
rule("5.1.1", "Operating rounds per stock round", "One OR after each stock round; once the first 2-train is bought, after the NEXT stock round two ORs.", ["drv.operating_rounds_for_next_set", "act.start_operating_round", "st.or_set_size", "const.phase_table"], ["2.1.2"])
rule("5.3.1", "Company turn: director decides; first-turn housekeeping; buy trains", "Decisions for a company are made by its director; step H buys trains; only housekeeping and step H are in scope here (rest is given operating code).", ["act.advance_company", "act.buy_train"])
rule("5.13.2", "Company without a train must buy one (deferred)", "A company with no train at step H must buy one; forced purchase 5.14 is out of scope (skeleton operate action has no forced-purchase flow).", [], ["5.13.4"], deferred=True)
rule("5.13.3", "Buying from another company (deferred)", "Company-to-company train sale: consent, price 1..treasury; out of scope (only 'buy from bank' is modelled).", [], ["5.13.4"], deferred=True)
rule("5.13.4", "Buy from the bank in order, face value", "From the bank: any bank-pool train, or the next new train; trains must be bought in order (all of the previous type bought or exported); price = face value; pool trains appear only by discard.", ["act.buy_train", "drv.front_group", "drv.train_cost", "st.train_deck", "st.bank_pool_trains", "const.train_costs"], ["2.2.4"])
rule("5.13.5", "Purchase advances the phase; rust", "Buying the first train of a new type advances the phase; some trains rust at once, without compensation.", ["act.buy_train", "act.phase_check", "act.rust_trains"], ["2.1.1", "2.1.3"])
rule("5.13.6", "Multiple purchases; limit checked before buying", "A company may buy several trains one after another, effects apply at once; a company below its limit may buy even if the purchase lowers the limit.", ["act.buy_train", "drv.train_limit", "act.phase_check"])
rule("5.13.7", "At the limit: no purchase", "A company at the train limit cannot buy, even if the purchase would rust enough trains to make room.", ["act.buy_train", "drv.train_limit"])
rule("5.13.8", "L/2 side choice", "The director chooses L or 2 when buying from the L/2 stack; double-sided cards.", ["act.buy_train", "st.company_trains", "st.train_deck"])
rule("5.13.9", "L to 2 upgrade in phases 1-2", "In phases 1 and 2 an L can be converted to a 2 for the indicated price; counts as a train purchase.", ["act.upgrade_l_train", "act.phase_check", "const.train_costs"])
rule("5.13.10", "7/E side choice is final", "The director chooses 7 or E when buying; cannot be changed; 7 cannot be upgraded to E.", ["act.buy_train", "st.company_trains"])
rule("5.13.11", "At most one E-train per company", "A company may own at most one E-train (minors may own but not run it).", ["act.buy_train", "st.company_trains"])
# existing rules gain targets in the new scope
add_targets("2.1.1", ["drv.phase_of_train", "act.buy_train", "act.upgrade_l_train"])
add_targets("2.1.2", ["drv.operating_rounds_for_next_set", "st.or_set_size", "act.start_operating_round", "act.end_stock_round"])
add_targets("2.1.3", ["act.rust_trains", "st.company_trains", "st.bank_pool_trains"])
add_targets("2.1.4", ["act.discard_excess_trains", "drv.train_limit", "st.company_trains", "st.bank_pool_trains"])
add_targets("2.1.5", ["act.discard_excess_trains"])
for _r in ("2.2.3", "2.2.4", "2.2.5", "2.2.8"):
    add_targets(_r, ["const.phase_table", "drv.train_limit"])
add_targets("2.2.6", ["const.phase_table"])
add_targets("1.7.11", ["act.buy_train", "drv.front_group", "drv.deck_remaining"])
add_targets("3.4.4", ["act.pay_concession_dividends"])
add_targets("4.1.1", ["act.start_stock_round"])
add_targets("4.1.2", ["act.end_turn", "st.turn"])
add_targets("4.1.3", ["act.stock_turn_action", "act.end_turn"])
add_targets("4.1.4", ["act.stock_turn_action"])
add_targets("4.11.1", ["act.end_stock_round", "act.pass_turn"])
add_targets("5.2.1", ["act.begin_operating_round", "act.pay_private_revenues", "act.advance_company", "act.end_operating_round"])
add_targets("5.2.2", ["act.advance_company", "st.or_order", "st.or_current"])
add_targets("10.1.1", ["act.end_stock_round", "act.end_operating_round", "const.game_end_triggers", "drv.final_ranking"])
add_targets("10.1.2", ["act.end_operating_round"])
add_targets("10.1.3", ["drv.final_ranking"])
add_targets("4.4.2", ["act.advance_company"])
add_targets("4.2.2", ["drv.cert_limit"])

# ---------------------------------------------------------------- rulings (v2): R6b
ruling("R6b", "First-round nothing-sold, precise", "In 10.1.1 'nothing sold in the first stock round' means: no share bought or sold, no concession converted, AND no bid-box item won at resolution. A round with only unsuccessful bids (nobody could pay, R8) counts as nothing sold; a round in which at least one bid wins an item counts as something sold. PROVISIONAL ruling (adopted by the task owner), replaces the provisional tail of R6.",
        ["10.1.1"], ["st.sale_happened", "act.resolve_bids", "act.check_game_end_triggers", "act.sell_shares", "act.buy_share", "act.convert_concession", "act.end_stock_round"], provisional=True)

state("company_cash", "Company treasury cash", "int map company->int", "per major and minor company", "pounds", "share_trading", "Cash in a company's treasury: credited by buy_share (treasury source), convert_concession, float_minors, pay_private_revenues; debited by buy_train / upgrade_l_train.", "company_treasury",
      external="Also spent/earned by operating-round code outside this graph (tile costs, dividends in operating.py).")


# ================================================================ V2 actions and derived (round engine, phase_trains, share trading, ...)
# ---------------------------------------------------------------- GIVEN-code actions (actions.py, setup.py): modelled so the graph follows the skeleton turn model
action("setup_game", "sr_flow", "Set up the game (given: setup.new_game)",
       "Initialise all state for a new game. GIVEN code (setup.new_game): it ALSO fills the bid boxes and returns a state that is already INSIDE the first stock round.",
       ["game_id", "player_names (3..7)", "seed (random input)"],
       [("3 <= n <= 7 (start money table only defines these counts)", "1.7.2")],
       ["[2.2.2] phase = 1",
        "[1.7.2] each player cash = start money; bank_cash = 12000 - n*start = 9900; all loans 0",
        "[1.7.4] concession_stack = shuffle(9 non-LNWR) with LNWR on top; [1.7.5] minor_stack = 23 shuffled + M24 on top; [1.7.6] private_stack = 17 shuffled + P1 on top",
        "[1.7.11] train_deck counts L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0; bank_pool_trains = []; company_trains empty",
        "[1.7.12] sr_order = random permutation; priority player = sr_order[0]",
        "[1.7.7] boxes filled 3 concession / 4 minor / 3 private from the stack tops (given _refill_bid_boxes; R9 not needed in phase 1)",
        "[1.7.14] round_type = STOCK; turn.active_player = sr_order[0]; turn.bids_made = 0; sr_completed = 0 -- the FIRST stock round is pre-started here, start_stock_round is NOT called for round 1",
        "sale_happened = false; pass_streak = 0; sold_this_round = {}; game_end none; holdings empty; every major unstarted; market empty; or_set_size = 1; or_index = 0; or_order = []; or_current = 0; private_status all unowned and open"],
       ["ValueError: n not in 3..7"],
       writes=S("player_count", "sr_order", "player_cash", "player_loans", "bank_cash", "phase", "sr_completed", "round_type", "turn", "pass_streak", "sale_happened", "sold_this_round", "ordinary_certs", "director_holder", "treasury_shares", "pool_shares", "company_cash", "major_status", "market_stack", "player_concessions", "player_privates", "minor_director", "concession_stack", "minor_stack", "private_stack", "box_contents", "removed_items", "bids", "train_deck", "bank_pool_trains", "company_trains", "phase_events", "game_end", "or_set_size", "or_index", "or_order", "or_current", "private_status", "has_completed_or"),
       consts=C("start_money", "bank_total", "stack_setup", "train_deck", "cert_limit", "bidding_tokens", "market_grid"))

action("apply_action", "sr_flow", "Dispatch one client action (given: actions.apply_action)",
       "GIVEN dispatcher: rejects actions after game over, routes by action type, and runs the game-end trigger check after EVERY action.",
       ["player_id", "action dict {type: pass | bid | buy_share | sell_shares | convert_concession | operate, ...}"],
       [("game not over (ActionError 'Game is over')", "10.1.2")],
       ["route to stock_turn_action / pass_turn / operate_company by action['type']",
        "[10.1.1] after every action call check_game_end_triggers(state) with ONE argument (context None)"],
       ["ActionError (given)"],
       reads=S("game_end"), calls=A("check_game_end_triggers", "stock_turn_action", "pass_turn", "operate_company"), triggers=A("stock_turn_action", "pass_turn", "operate_company"))

action("stock_turn_action", "sr_flow", "Turn-ending stock action wrapper (given: actions._apply_bid/_buy_share/_sell_shares/_convert_concession)",
       "GIVEN wrapper: a stock-round player calls exactly ONE of bid / buy_share / sell_shares / convert_concession; after a successful call the TURN ENDS. v2 follows this skeleton turn model: the v1 sell -> repay -> one-of-C sequence inside one turn is NOT reachable (4.1.3 is simplified).",
       ["player_id", "action dict"],
       [("round_type = STOCK (ActionError otherwise)", "4.1.3"), ("player_id = turn.active_player (ActionError otherwise)", "4.1.2"),
        ("bid: 1..3 bids in the action and bids_made + len(bids) <= 3", "4.10.5")],
       ["call exactly ONE module function (place_bid/move_bid once per bid, buy_share, sell_shares or convert_concession); a module exception is re-raised as ActionError",
        "[4.10.5] bid: turn.bids_made += 1 after each successful bid -- done HERE, never by the bidding module",
        "[A13] pass_streak = 0 (any such action breaks the consecutive-pass chain)",
        "[R15, R6] buy_share and convert_concession: sale_happened = true (redundant: the module functions set it too); sell_shares: NOT set here, sell_shares sets it itself",
        "[4.1.2] call end_turn (advance_stock_player)"],
       ["ActionError (given)"],
       reads=S("round_type", "turn"), writes=S("turn", "pass_streak", "sale_happened"),
       calls=A("place_bid", "move_bid", "buy_share", "sell_shares", "convert_concession", "end_turn"), triggers=A("place_bid", "move_bid", "buy_share", "sell_shares", "convert_concession", "end_turn"))

action("pass_turn", "sr_flow", "Pass (given: actions._apply_pass)",
       "GIVEN: a stock-round pass counts toward the consecutive-pass chain; the round ends when every player has passed in a row. In an operating round the director's pass ends that company's turn. NOTE: a pass is NOT blocked by must_sell (R10 is enforceable only for buy/bid/convert) -- decision GA02.",
       ["player_id"],
       [("stock round: player_id = turn.active_player", "4.1.2"), ("operating round: a company is active and player_id is its director", "5.3.1")],
       ["[4.1.4] stock round: pass_streak += 1",
        "[4.11.1] if pass_streak >= player_count (drv.sr_over): call end_stock_round, else call end_turn",
        "[5.3.1] operating round: call advance_company"],
       ["ActionError (given)"],
       reads=S("round_type", "turn", "pass_streak", "player_count"), writes=S("pass_streak"),
       calls=A("end_stock_round", "end_turn", "advance_company") + D("sr_over"), triggers=A("end_stock_round", "end_turn", "advance_company"))

action("operate_company", "sr_flow", "Operate one company (given: actions._apply_operate)",
       "GIVEN wrapper for one company's operating turn: housekeeping, tile lay, destination check, running trains, dividends (5.12: out of scope, given code), then optional buy of a train, then the turn ends.",
       ["player_id", "action dict {company_id, tile_lay?, dividend_choice?, buy_train?}"],
       [("round_type = OPERATING", "5.2.1"), ("company_id = active_company", "5.2.2"), ("player_id = the company's director", "5.3.1")],
       ["[5.3.1 A-G] first-turn housekeeping, tile lay, destination, run trains, dividends: given operating code (out of scope)",
        "[5.3.1 H] if action['buy_train'] is given: call buy_train(company, kind, code) (TrainError re-raised as ActionError)",
        "[5.2.2] call advance_company"],
       ["ActionError (given)"],
       reads=S("round_type", "or_order", "or_current"), calls=A("buy_train", "advance_company") + D("active_company"), triggers=A("buy_train", "advance_company"))

# ---------------------------------------------------------------- stock-round flow
action("start_stock_round", "sr_flow", "Start a stock round (round 2 onwards, and debug)",
       "Begin a stock round after an operating-round set: refill boxes, reset per-round flags, hand the turn to the Player-1 card holder. NOT used for round 1 (pre-started by setup) but must work at any time (main.py debug endpoint).",
       ["none"],
       [("game not over (game_over False)", "10.1.2")],
       ["[4.1.1] call refill_boxes (start-of-round refill)",
        "round_type = STOCK",
        "[R15] sale_happened = false; sold_this_round = {}; pass_streak = 0",
        "[4.1.2] priority player := sr_order[0] (priority_deal_player_id re-asserted equal to player_order[0]); call begin_turn(sr_order[0])"],
       ["ERR_GAME_OVER: game_over is set (RoundError)"],
       reads=S("game_end", "sr_order"), writes=S("round_type", "sale_happened", "sold_this_round", "pass_streak"),
       calls=A("refill_boxes", "begin_turn"), triggers=A("begin_turn"),
       notes="No 'already running' precondition: there is no sr_status field and main.py calls this function at arbitrary times (decision GA05).")

action("begin_turn", "sr_flow", "Begin a player's stock turn", "Make a player active and reset the per-turn bid counter.",
       ["player_id"],
       [("player_id is a player of the game (the correct successor is guaranteed by the callers)", "4.1.2")],
       ["[4.1.3] turn.active_player = player_id; turn.bids_made = 0"],
       ["ERR_WRONG_PLAYER: player_id not in player_order (RoundError)"],
       reads=S("sr_order"), writes=S("turn"))

action("end_turn", "sr_flow", "End a stock turn (advance_stock_player)",
       "Hand the stock turn to the next player after a turn-ending action or a non-final pass. Used for BOTH 'end turn' and 'pass (not last)'. It does not touch pass_streak (written by actions.py only).",
       ["none"],
       [("a turn-ending action or a non-final pass just happened (guaranteed by the caller actions.py; NOT re-checked)", "4.1.2")],
       ["[4.1.2] call begin_turn(next_player(turn.active_player))",
        "pass_streak is NOT written here (stock_turn_action resets it, pass_turn increments it)"],
       ["NONE for legal input (raises nothing)"],
       reads=S("turn", "sr_order"), calls=A("begin_turn") + D("next_player"), triggers=A("begin_turn"),
       notes="v1 preconditions turn.acted / not must_sell / ERR_NO_ACTION_TAKEN / ERR_MUST_SELL dropped: unenforceable under the skeleton turn model (decision GA01, GA02).")

action("end_stock_round", "sr_flow", "End the stock round: resolve, count, start the operating-round set",
       "Called by pass_turn when every player passed in a row. Resolves the round, counts it, and starts the operating-round set unless the game ended immediately.",
       ["none"],
       [("called by pass_turn after sr_over (4.11.1); NOT re-checked here: the round manager decides when (decision GA37)", "4.11.1")],
       ["let phase_before = phase (needed by the 2.1.2 deferral)",
        "[4.11.1] call resolve_stock_round (steps 1..9)",
        "sr_completed += 1 (AFTER resolution so that step 9 saw sr_completed = 0 in the first round)",
        "[10.1.1] if game_over was set by the immediate trigger: STOP (no operating round starts)",
        "[5.1.1] otherwise call start_operating_round(phase_before)"],
       ["ERR_GAME_OVER: game_over already set at entry (RoundError)"],
       reads=S("game_end", "phase"), writes=S("sr_completed"), calls=A("resolve_stock_round", "start_operating_round"), triggers=A("resolve_stock_round", "start_operating_round"))

action("start_operating_round", "sr_flow", "Start an operating-round set",
       "Start the set of operating rounds that follows a stock round: lock the set size, convert a 'next_or' trigger, begin the first operating round.",
       ["phase_before (phase at the start of the stock-round resolution; default = current phase)"],
       [("game not over", "10.1.2")],
       ["[5.1.1] round_type = OPERATING; or_index = 0",
        "[2.1.2, 5.1.1] or_set_size = operating_rounds_for_next_set(phase_before) (LOCKED for the whole set)",
        "[10.1.1] if end_trigger = next_or: end_trigger = or_set_end and or_set_size = 1 (game ends after exactly this one OR)",
        "call begin_operating_round"],
       ["ERR_GAME_OVER (RoundError)"],
       reads=S("game_end", "phase"), writes=S("round_type", "or_index", "or_set_size", "game_end"),
       calls=A("begin_operating_round") + D("operating_rounds_for_next_set"), triggers=A("begin_operating_round"))

action("begin_operating_round", "sr_flow", "Begin one operating round",
       "Step A of 5.2.1 (private and concession revenue), then choose the first company; if nobody can run, the round ends at once.",
       ["none"],
       [("none beyond being inside an operating-round set", "5.2.1")],
       ["[5.2.1 A, 3.1.2] call pay_private_revenues", "[5.2.1 A, 3.4.4] call pay_concession_dividends",
        "or_order = []; or_current = 0",
        "[5.2.1 B/C, 5.2.2] first = next_operating_company(done = {}); if none: call end_operating_round; else or_order = [first]"],
       ["NONE (raises nothing)"],
       writes=S("or_order", "or_current"), calls=A("pay_private_revenues", "pay_concession_dividends", "end_operating_round") + D("next_operating_company"), triggers=A("pay_private_revenues", "pay_concession_dividends", "end_operating_round"))

action("advance_company", "sr_flow", "Finish a company's turn and choose the next company",
       "Called after a company's operate action or its director's pass. The next company is chosen only now (sales or price moves during the turn may reorder, 5.2.2).",
       ["none"],
       [("a company is active: round_type = OPERATING and 0 <= or_current < len(or_order)", "5.2.2")],
       ["[4.4.2] if the finished company is a major: has_completed_or[c] = true",
        "[5.2.2] done = or_order[0..or_current]; nxt = next_operating_company(done)",
        "if nxt exists: or_order = or_order[0..or_current] + [nxt]; or_current += 1; else call end_operating_round"],
       ["ERR_NO_ACTIVE_COMPANY: nothing is operating (RoundError)"],
       reads=S("round_type", "or_order", "or_current"), writes=S("has_completed_or", "or_order", "or_current"),
       calls=A("end_operating_round") + D("next_operating_company", "active_company"), triggers=A("end_operating_round"))

action("end_operating_round", "sr_flow", "End an operating round",
       "Decide what follows an operating round: game end (matured trigger), the next operating round of the set, or the next stock round.",
       ["none"],
       [("none beyond being inside an operating round", "5.2.1")],
       ["[10.1.1] if end_trigger = or_end (token reached the game-end cell in an OR) or next_or: game_over = true; stop",
        "or_index += 1; if or_index < or_set_size: call begin_operating_round; stop",
        "[10.1.1] the set is complete: if end_trigger = or_set_end: game_over = true; stop",
        "[1.7.14, 5.1.1] otherwise call start_stock_round"],
       ["NONE (raises nothing)"],
       reads=S("game_end", "or_set_size", "or_index"), writes=S("game_end", "or_index"), calls=A("begin_operating_round", "start_stock_round"), triggers=A("begin_operating_round", "start_stock_round"))

derived("sr_over", "sr_flow", "Stock round over?", "True when all players passed consecutively.", ["none"], "[4.11.1] pass_streak >= player_count (actions.py uses >=; == for valid play)", reads=S("pass_streak", "player_count"), returns="bool")
derived("active_company", "sr_flow", "Active company", "The company whose operating turn it is.", ["none"],
        "[5.2.2] or_order[or_current] if round_type = OPERATING and 0 <= or_current < len(or_order) else none", reads=S("round_type", "or_order", "or_current"), returns="company|null")
derived("operating_rounds_for_next_set", "sr_flow", "Operating rounds in the next set", "Size of the operating-round set after a stock round, with the 2.1.2 deferral.", ["phase_before"],
        "[5.1.1, 2.1.2] if end_trigger = next_or: 1 (game ends after exactly one more OR); else const.phase_table.ors_per_sr[phase_before] where phase_before = the phase when the stock round RESOLUTION started (default: current phase). So a phase change during this stock round's resolution (e.g. the first 2-train exported) changes the set size only from the FOLLOWING stock round on; a phase change during an operating round is already in phase_before of the next stock round",
        reads=S("phase", "game_end"), consts=C("phase_table"), returns="int")
derived("bank_broken", "sr_flow", "Bank broken?", "True when the bank has run out of money.", ["none"], "[10.1.1] bank_cash < 0 (assumption A29; loans excluded [4.3.5])", reads=S("bank_cash"), returns="bool")
derived("next_player", "sr_flow", "Next player in order", "The player after p in the cyclic stock-turn order.", ["player p"], "[4.1.2] sr_order[(index(p)+1) mod n]", reads=S("sr_order", "player_count"), returns="player")
derived("private_revenue", "sr_flow", "Private revenue", "Fixed revenue of one private company in the current phase.", ["private number", "phase"],
        "[3.1.2] value from const.private_revenue_table: '£N' -> N; '£Nx phase' -> N * phase (P15)", consts=C("private_revenue_table"), returns="int")
derived("player_wealth", "sr_flow", "Player wealth", "Wealth of a player at game end.", ["player p"],
        "[10.1.3] cash + sum over majors c of units_held(p,c)*current_price(c) + 100 * |concessions held| - loans; privates and company assets count 0",
        reads=S("player_cash", "player_loans", "player_concessions"), calls=D("units_held", "current_price"), returns="int")
derived("final_ranking", "sr_flow", "Final ranking", "Players ordered by wealth, richest first (the richest wins).", ["none"],
        "[10.1.3] sort players by player_wealth descending; ties keep sr_order (needs_owner: no tie-break in the rulebook)", reads=S("sr_order"), calls=D("player_wealth"), returns="list<(player, wealth)>")

action("check_game_end_triggers", "sr_flow", "Check game-end triggers",
       "Evaluate the game-end conditions and record the FIRST trigger. Called after every action (one argument), after bank payments and token moves, and at the end of stock-round resolution.",
       ["context in {None, after_bank_payment, after_token_move, end_of_stock_round}; None = 'after any change'; only end_of_stock_round enables the nothing-sold test; the trigger KIND comes from round_type, not from context"],
       [("a trigger already exists (game_over or end_trigger_pending): do nothing, the first trigger stands", "10.1.2")],
       ["[10.1.2] if game_end.trigger != none or over: return unchanged",
        "[10.1.1, R6b] if context = end_of_stock_round and sr_completed = 0 and not sale_happened: over = true (immediate; game_over = True)",
        "[10.1.1] elif round_type = OPERATING and any token on a game-end cell: trigger = or_end (game ends at the end of that operating round)",
        "[10.1.1] elif round_type = OPERATING and bank_broken: trigger = or_set_end (game ends after the current set of ORs; complete the set even if a token later reaches the game-end cell)",
        "[10.1.1] elif round_type = STOCK and (any token on a game-end cell or bank_broken): trigger = next_or (game ends after exactly one more OR)",
        "[10.1.2] a trigger set earlier in this call is never overwritten; steps are evaluated in this order and the first that fires wins"],
       ["NONE (total function; unknown context strings are treated as None)"],
       reads=S("bank_cash", "market_stack", "sr_completed", "sale_happened", "game_end", "round_type"), writes=S("game_end"),
       calls=D("bank_broken", "is_game_end_cell", "token_cell"), consts=C("game_end_cells", "game_end_triggers"))

action("pay_concession_dividends", "sr_flow", "Pay concession dividends",
       "Operating-round step A for concessions: each held concession pays 10 to its owner from the bank.",
       ["none"],
       [("phase < 5 (concessions exist); at phase >= 5 the call is a no-op", "R9")],
       ["[3.4.4, 5.2.1] for every player and every concession held: player_cash += 10; bank_cash -= 10 (the bank keeps paying when broken)",
        "[R9] phase >= 5: nothing to pay",
        "[10.1.1] call check_game_end_triggers(after_bank_payment) ONCE after all payments"],
       ["NONE (raises nothing)"],
       reads=S("player_concessions", "phase"), writes=S("player_cash", "bank_cash"), calls=A("check_game_end_triggers"), consts=C("concession_dividend"))

action("pay_private_revenues", "sr_flow", "Pay private-company revenue",
       "Operating-round step A for private companies: every open private pays its fixed revenue to its owner (player or company) from the bank.",
       ["none"],
       [("a private pays only while open (not closed)", "3.1.2")],
       ["[3.1.2, 5.2.1 A] for every open private n with revenue r = private_revenue(n, phase) > 0: owner player (Player.private_companies): player_cash += r; owner company (owner_company_id): company_cash += r; bank_cash -= r",
        "[3.1.2] revenue 0 (P3, P4, P16): nothing moves",
        "[10.1.1] call check_game_end_triggers(after_bank_payment) ONCE after all payments"],
       ["NONE (raises nothing)"],
       reads=S("private_status", "player_privates", "phase"), writes=S("player_cash", "company_cash", "bank_cash"), calls=A("check_game_end_triggers") + D("private_revenue"), consts=C("private_revenue_table"),
       notes="P15/P20 'treasury credit' accrual and closing of privates are out of scope (decision GA35).")

# ---------------------------------------------------------------- share trading
action("sell_shares", "share_trading", "Sell shares", "Sell s ordinary certificates of one major company into the bank pool (one batch). Ends the turn (caller).",
       ["player", "major company c", "count s"],
       [("c is a major company; privates, minors, concessions can never be sold", "4.4.1"),
        ("count is an integer >= 1", "4.4.1"),
        ("major_status[c] = floated and has_completed_or[c]", "4.4.2"),
        ("pool_shares[c] + s <= 5 (50% of the company)", "4.4.2"),
        ("drv.sale_legal(player,c,s).legal: s <= ordinary_certs unless the director has an eligible successor (the director's certificate itself never goes to the pool)", "R5"),
        ("loans do not block selling; no round/turn check inside the module (caller checks active player)", "4.3.3")],
       ["let price = current_price(c) read BEFORE any move (assumption A9)",
        "[4.4.2] if sale_legal.swap_needed: call swap_director(c, sale_legal.successor) BEFORE the rest of the sale",
        "[4.4.1] ordinary_certs[player,c] -= s; pool_shares[c] += s",
        "[4.4.3] player_cash += s*price; bank_cash -= s*price",
        "[4.4.4, 4.4.5] call move_token_down(c, s)",
        "[4.5.5] add c to sold_this_round[player] (list, no duplicates)",
        "[R15] sale_happened = true (the module sets it itself; actions.py does not)",
        "[10.1.1] call check_game_end_triggers(after_bank_payment)",
        "[4.4.6] one call = one batch of ONE company; the turn ends after the call (caller sets pass_streak = 0 and calls end_turn)"],
       ["ERR_UNKNOWN_PLAYER", "ERR_NOT_SELLABLE: not a major / not floated / has not completed an OR", "ERR_BAD_COUNT: not an int >= 1", "ERR_POOL_FULL", "ERR_TOO_MANY: s exceeds holdings / no successor (sale_legal.reason)"],
       reads=S("major_status", "has_completed_or", "ordinary_certs", "director_holder", "pool_shares"),
       writes=S("ordinary_certs", "pool_shares", "player_cash", "bank_cash", "sold_this_round", "sale_happened"),
       calls=D("sale_legal", "current_price") + A("swap_director", "move_token_down", "check_game_end_triggers"))

action("repay_loans", "share_trading", "Repay loans", "Pay all or part of the player's loans to the bank (4.1.3 step B). NOT reachable through apply_action in the skeleton (no repay action): implemented and exported only.",
       ["player", "amount (default: all that cash allows)"],
       [("amount is an int > 0 and <= loans (None = min(loans, cash))", "4.3.2"), ("player has loans", "4.3.2"), ("player_cash >= amount; no obligation to sell to raise the money", "4.3.3")],
       ["[4.3.2] player_cash -= amount; player_loans -= amount",
        "[4.3.5] bank_cash unchanged (loans are a separate source; assumption A28)"],
       ["ERR_UNKNOWN_PLAYER", "ERR_NO_LOANS", "ERR_BAD_AMOUNT: not an int, <= 0, or > loans", "ERR_INSUFFICIENT_CASH"],
       reads=S("player_cash", "player_loans"), writes=S("player_cash", "player_loans"),
       notes="wired=false: no caller in the skeleton (decision GA01).")
setattrs("act.repay_loans", wired=False)

action("buy_share", "share_trading", "Buy one share", "Buy one ordinary share of a started major company from its treasury or from the bank pool. Ends the turn (caller).",
       ["player", "major company c", "source in {None, 'treasury', 'pool', 'bank'}; 'bank' = 'pool' = the bank pool; None = module chooses"],
       [("source is None or one of 'treasury', 'pool', 'bank'", "4.5.1"),
        ("player_loans[player] = 0", "4.3.1"),
        ("not must_sell(player) (over the limit and still able to sell)", "R10"),
        ("c is a major, major_status[c] = floated and director_holder[c] != null (ordinary shares need a director; the director's certificate is not buyable here, phase-5 buying deferred)", "4.5.2"),
        ("the source holds >= 1 ordinary certificate (treasury_shares or pool_shares); source None: at least one of them", "4.5.1"),
        ("player_cash >= current_price(c) (no allowance for money committed in leading bids; assumption A7)", "4.5.1"),
        ("c not in sold_this_round[player]", "4.5.5"),
        ("units_held(player,c) < 6", "4.5.6"),
        ("if not in_yellow(c): cert_count(player) + 1 <= cert_limit even if directorship would change; in the yellow zone the limit is not checked", "4.5.7"),
        ("one certificate per turn and concession-in-play: guaranteed by the skeleton turn model (every action ends the turn; only ordinary shares are bought)", "4.5.4")],
       ["price = current_price(c) [4.5.3: unchanged by the purchase]; source None: pool if it holds a share, else treasury (A12; needs_owner)",
        "[4.5.1] player_cash -= price; treasury: company_cash[c] += price and treasury_shares[c] -= 1; pool: bank_cash += price and pool_shares[c] -= 1",
        "[4.5.1] ordinary_certs[player,c] += 1",
        "[4.5.9] if units_held(player,c) > units_held(director_holder[c], c): call swap_director(c, player)",
        "[R15] sale_happened = true (the module sets it; actions.py also does)",
        "[turn model] the turn ends after the call (caller)"],
       ["ERR_UNKNOWN_PLAYER", "ERR_BAD_SOURCE", "ERR_LOANS", "ERR_MUST_SELL", "ERR_NOT_STARTED", "ERR_NO_SHARE_AT_SOURCE", "ERR_INSUFFICIENT_CASH", "ERR_SOLD_THIS_ROUND", "ERR_AT_60_PERCENT", "ERR_CERT_LIMIT"],
       reads=S("player_loans", "major_status", "director_holder", "treasury_shares", "pool_shares", "player_cash", "sold_this_round", "ordinary_certs"),
       writes=S("player_cash", "company_cash", "treasury_shares", "pool_shares", "bank_cash", "ordinary_certs", "sale_happened"),
       calls=D("current_price", "units_held", "cert_count", "in_yellow", "cert_limit", "must_sell") + A("swap_director"))

action("convert_concession", "share_trading", "Convert concession", "Convert a held concession into the director's certificate, set the start price and float the major company (phases 2-4). Ends the turn (caller).",
       ["player", "major company c", "start_price in {60,70,80,90,100}"],
       [("2 <= phase <= 4 (no majors in phase 1; concessions removed at phase 5)", "4.6.2"),
        ("c in player_concessions[player]", "4.7.5"),
        ("major_status[c] = unstarted", "3.4.1"),
        ("player_loans[player] = 0", "4.3.1"),
        ("not must_sell(player) (assumption A8)", "R10"),
        ("start_price in {60,70,80,90,100}; 50 is for minors only", "1.6.4"),
        ("non-LNWR: player_cash >= 2*start_price - 100; LNWR: player pays nothing", "4.7.3")],
       ["[4.7.2] remove c from player_concessions[player]; director_holder[c] = player; the director's units (cert_units) enter the player's holding",
        "[4.7.2] call place_start_token(c, start_price, major) -- underneath all tokens already in that cell",
        "[4.7.3] non-LNWR: bank_cash -= 100; player_cash -= (2*start_price - 100); company_cash[c] = 2*start_price",
        "[4.7.4, R4] LNWR: bank_cash -= start_price; company_cash[c] = start_price; player pays nothing; director certificate is 1 unit",
        "[3.3.2] treasury_shares[c] = 8 (LNWR 9); pool_shares[c] = 0",
        "[4.7.6] major_status[c] = floated; has_completed_or[c] = false (operates in the next OR)",
        "[R6] sale_happened = true (the module sets it; actions.py also does)",
        "[10.1.1] call check_game_end_triggers(after_bank_payment)",
        "[turn model] the turn ends after the call (caller)"],
       ["ERR_PHASE", "ERR_NOT_HELD", "ERR_ALREADY_STARTED", "ERR_LOANS", "ERR_MUST_SELL", "ERR_BAD_START_PRICE", "ERR_INSUFFICIENT_CASH"],
       reads=S("phase", "player_concessions", "major_status", "player_loans", "player_cash"),
       writes=S("player_concessions", "director_holder", "bank_cash", "player_cash", "company_cash", "treasury_shares", "pool_shares", "major_status", "sale_happened", "has_completed_or"),
       calls=A("place_start_token", "check_game_end_triggers") + D("must_sell", "cert_units"), consts=C("start_values", "share_structure"))

derived("sale_legal", "certificates", "Is a sale legal?", "Whether player p may sell s shares of company c, what directorship change that causes, and why not.", ["player p", "major c", "count s"],
        "[4.4.2, R5] let k=ordinary_certs[p,c], H=units_held(p,c), d=director_holder[c]; if c is not a started major: legal=false, reason=ERR_NOT_SELLABLE; "
        "legal = s>=1 and major_status[c]==floated and has_completed_or[c] and pool_shares[c]+s<=5 and (p!=d: s<=k ; p==d: s<=k, or (s<=H and successor(c,p,H-s)!=null)); "
        "swap_needed = p==d and successor(c,p,H-s)!=null (s<=k: only if another player exceeds H-s; s>k: forced); "
        "returns {legal, swap_needed, successor, reason} where reason = null if legal else ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY (GAP A20 fixed)",
        reads=S("ordinary_certs", "director_holder", "pool_shares", "major_status", "has_completed_or"), calls=D("units_held", "successor"), returns="record")

derived("cert_limit", "certificates", "Certificate limit", "Limit for the current player count.", ["none"], "[4.2.1] const.cert_limit[player_count] (26/20/16/13/11 for 3..7 players)", reads=S("player_count"), consts=C("cert_limit"), returns="int")
derived("tokens_total", "bidding", "Bidding tokens per player", "Tokens each player has.", ["none"], "[4.10.3, 1.7.2] const.bidding_tokens[player_count] (6/5/4/3/3)", reads=S("player_count"), consts=C("bidding_tokens"), returns="int")
derived("start_cell", "market", "Start cell for a price", "Cell used to start a company at a given price.", ["price", "kind in {major, minor}"],
        "[1.6.3, 1.6.4] const.start_cells[price]; valid prices: major 60..100, minor 50..100 (50 is solid red, minors only); anything else is an error ERR_BAD_START_PRICE", consts=C("start_cells", "start_values"), returns="cell")
derived("bid_amount_error", "bidding", "Why is a bid amount invalid?", "The error code of the first failing amount check, or none (GAP A19 fixed: three separate codes).", ["player p", "item", "amount"],
        "[4.10.6, 4.10.7] amount not an int or amount % 5 != 0 -> ERR_BAD_AMOUNT; amount < min_legal_bid(item) -> ERR_BID_TOO_LOW; committed_money(p) + amount > player_cash[p] -> ERR_INSUFFICIENT_CASH; else none. bid_amount_valid = (bid_amount_error is none)",
        reads=S("player_cash"), calls=D("min_legal_bid", "committed_money"), consts=C("bid_rules"), returns="error code|null")

# ---------------------------------------------------------------- market / boxes (changed)
action("place_start_token", "market", "Place start token", "Place a newly started company's token on its start cell.",
       ["company c", "price", "kind in {major, minor} (default major)"],
       [("price is a valid start value for the kind: major 60..100; minor 50..100 (50 solid red = minors only)", "1.6.3"), ("kind is major or minor", "1.6.4")],
       ["cell = start_cell(price, kind)",
        "[4.7.2] major: insert c at the BOTTOM of the pile in cell",
        "[4.11.5] minor: insert directly after the LEADING RUN of minor tokens at the top of the pile (index = number of consecutive minor tokens at the top; above every major token, below the existing leading minors) (GAP A28 fixed)"],
       ["ERR_BAD_START_PRICE", "ERR_BAD_KIND"],
       reads=S("market_stack"), writes=S("market_stack"), calls=D("start_cell"), consts=C("start_values"))

derived("operating_order", "market", "Operating order", "Order in which started companies run in an operating round.", ["none"],
        "[5.2.1] floated minors (minor_director != null, token on market, not acquired by a major) in descending_order, then floated majors (major_status = floated, token on market) in descending_order",
        reads=S("market_stack", "minor_director", "major_status"), calls=D("descending_order"), returns="list<company>")

action("vacate_box_item", "bid_boxes", "Take an item out of its box", "Remove the item from its box and give it to a player or remove it from play.", ["item (kind, box_index)", "disposition in {award(player), remove}"],
       [("the box currently holds an item", "4.11.2"), ("award needs a player", "4.11.2")],
       ["[4.11.2] box_contents[kind][box] = null (no shifting here)",
        "award: concession -> player_concessions; private -> player_privates and private_status owner = player; minor -> minor_director[m] = player",
        "remove: removed_items += item (minors: MinorCompanyState.removed = true)"],
       ["ERR_ITEM_NOT_IN_BOX", "ERR_BAD_DISPOSITION"],
       reads=S("box_contents"), writes=S("box_contents", "player_concessions", "player_privates", "minor_director", "removed_items", "private_status"))

BID_PRE2 = [
    ("kind in {minor, concession, private} and the box exists and holds an item; concession items only while phase < 5", "R9"),
    ("turn.bids_made < 3 (READ ONLY: the caller increments it after each successful bid, never this module)", "4.10.5"),
    ("player_loans[player] = 0", "4.3.1"),
    ("not must_sell(player)", "R10"),
    ("cert_count(player) < cert_limit (leading bids count; applies to privates too)", "4.10.8"),
    ("bid_amount_error(player,item,amount) is none: amount an int multiple of 5 (ERR_BAD_AMOUNT), >= min_legal_bid (ERR_BID_TOO_LOW), committed + amount <= cash (ERR_INSUFFICIENT_CASH)", "4.10.6"),
]
action("place_bid", "bidding", "Place a bid", "Put an unallocated bidding token on an item at a new bid value. The given API merges place and move into one function: a player with no token on the item takes this branch.",
       ["player", "item", "amount"],
       BID_PRE2 + [("tokens_used(player) < tokens_total", "4.10.3"), ("player has NO token on this item (otherwise the move branch applies; one token per player per item; assumption A5)", "4.10.4"),
                   ("items are obtainable only by bidding", "3.1.4")],
       ["[4.10.4] bids[item][player] = amount",
        "[4.10.5] bids_made is NOT written here (caller actions.py increments it)",
        "[4.2.5] the player now counts one more certificate (leading bid)"],
       ["ERR_ITEM_NOT_IN_BOX", "ERR_TOO_MANY_BIDS", "ERR_LOANS", "ERR_MUST_SELL", "ERR_CERT_LIMIT", "ERR_BAD_AMOUNT", "ERR_BID_TOO_LOW", "ERR_INSUFFICIENT_CASH", "ERR_NO_TOKENS"],
       reads=S("turn", "player_loans", "box_contents", "phase", "bids"), writes=S("bids"),
       calls=D("must_sell", "cert_count", "cert_limit", "bid_amount_error", "tokens_used", "tokens_total"))

action("move_bid", "bidding", "Move a bid up", "Move an already placed token to a higher space on the same item (same API function as place_bid: branch = the player already has a token on the item).",
       ["player", "item", "new_amount"],
       BID_PRE2 + [("the player already has a token on the item and is NOT the highest bidder (another player has a higher bid)", "4.10.4"),
                   ("a token cannot be withdrawn or moved to another item", "4.10.10")],
       ["[4.10.4] bids[item][player] = new_amount (the token moves; the old space becomes empty)",
        "[4.10.5] bids_made is NOT written here (caller)",
        "the player now leads the item: committed money and certificate count rise"],
       ["ERR_ITEM_NOT_IN_BOX", "ERR_TOO_MANY_BIDS", "ERR_NOT_OUTBID", "ERR_LOANS", "ERR_MUST_SELL", "ERR_CERT_LIMIT", "ERR_BAD_AMOUNT", "ERR_BID_TOO_LOW", "ERR_INSUFFICIENT_CASH"],
       reads=S("turn", "player_loans", "box_contents", "phase", "bids"), writes=S("bids"),
       calls=D("must_sell", "cert_count", "cert_limit", "bid_amount_error", "highest_bidder"))

# ---------------------------------------------------------------- phase_trains
derived("front_train", "phase_trains", "Front train of the deck", "Code of the next available new train (first code with count > 0 in scan order L,2,3,4,5,6,7,E).", ["none"],
        "[R7, 1.7.11] first code in scan order L,2,3,4,5,6,7,E with train_deck[code] > 0, else none", reads=S("train_deck"), returns="train code|null")
derived("front_group", "phase_trains", "Front train group", "The deck group that may currently be bought from (5.13.4 order).", ["none"],
        "[5.13.4, 1.7.11] the first group of [L/2, 3, 4, 5, 6, 7/E] with deck_remaining > 0, else none", reads=S("train_deck"), calls=D("deck_remaining"), returns="group|null")
derived("deck_remaining", "phase_trains", "Remaining cards of a deck group", "Number of new cards left in a group.", ["group"],
        "[T12] sum of train_deck[code] over the group's codes (L/2: L+2; 7/E: 7+E)", reads=S("train_deck"), returns="int")
derived("train_group", "phase_trains", "Group of a train code", "Deck group a train code belongs to.", ["code"], "[5.13.8, 5.13.10] L,2 -> L/2; 3; 4; 5; 6; 7,E -> 7/E; unknown code -> error ERR_UNKNOWN_TRAIN", consts=C("train_deck"), returns="group")
derived("train_cost", "phase_trains", "Train face value", "Price of a train type.", ["code"], "[5.13.4] const.train_costs[code]; unknown code -> ERR_UNKNOWN_TRAIN", consts=C("train_costs"), returns="int")
derived("train_limit", "phase_trains", "Train limit", "Number of trains a company may own in a phase.", ["kind in {minor, major}", "phase"],
        "[2.1.4, 2.2.3-2.2.8] const.phase_table.train_limits[phase][kind] (minor/major: 1-3: 2/4; 4: 1/3; 5-7: 1/2)", consts=C("phase_table"), returns="int")

action("phase_check", "phase_trains", "Phase check", "Advance the phase if this is the first train of its type and apply the phase effects AT ONCE: rust, train-limit discard, concession clearing.", ["train code"],
       [("an L-train never triggers a phase; codes 2..7, E map through the phase table; the phase never decreases", "2.2.1")],
       ["[2.1.1] new = phase_of_train(code); if none or new <= phase: do nothing",
        "old = phase; phase = new",
        "[2.1.3] for every phase p in old+1..new (so skipped phases are not lost): call rust_trains(rust_table[p])",
        "[2.1.4, 2.1.5] call discard_excess_trains (AFTER rusting, descending share price order)",
        "[2.2.8, R9] if old < 5 <= new: call clear_concession_boxes",
        "[2.1.2] append ONE audit line to phase_events (from, to, rusted codes, discarded count, operating rounds per stock round); the operating-round count is applied by start_operating_round, never here"],
       ["NONE (raises nothing; unknown code = no phase effect)"],
       reads=S("phase"), writes=S("phase", "phase_events"), calls=D("phase_of_train") + A("rust_trains", "discard_excess_trains", "clear_concession_boxes"),
       triggers=A("rust_trains", "discard_excess_trains", "clear_concession_boxes"), consts=C("rust_table", "phase_table"))

action("rust_trains", "phase_trains", "Rust trains", "Remove every train of a rusted type from the game without compensation.", ["train code"],
       [("rusting is immediate and without compensation", "2.1.3")],
       ["[2.1.3] remove every train with that code from every company_trains list, from bank_pool_trains and from the deck counts; nothing is paid"],
       ["NONE (raises nothing)"],
       reads=S("company_trains", "bank_pool_trains", "train_deck"), writes=S("company_trains", "bank_pool_trains", "train_deck"), consts=C("rust_table"))

action("discard_excess_trains", "phase_trains", "Discard excess trains", "Companies above the new train limit discard the excess into the bank pool, without compensation.", ["none"],
       [("applies after rusting; companies act in descending share price order", "2.1.5")],
       ["[2.1.5] order = descending_order(companies that own trains)",
        "[2.1.4] for each company in order: while len(trains) > train_limit(kind, phase): discard ONE train into bank_pool_trains (orientation kept); which train: the lowest face value first (needs_owner: a director's choice)",
        "no compensation"],
       ["NONE (raises nothing)"],
       reads=S("company_trains", "phase", "market_stack"), writes=S("company_trains", "bank_pool_trains"), calls=D("train_limit", "descending_order"), consts=C("train_costs"))

action("export_train", "phase_trains", "Export a train", "Remove a train from the bank deck (not the pool); exported trains leave the game.", ["mode in {L_only, next_with_phase}"],
       [("deck not empty (else no action)", "4.11.6")],
       ["mode L_only [4.11.6, R7]: if the front group is L/2: remove one card (decrement L first, then 2); counts as an L-train: NO phase check; if no L/2 remains: no action",
        "mode next_with_phase [4.11.7, R7]: remove one card from the front group (L/2 while any remain, then 3, 4, ...; decrement the first non-zero code of the group); effective type = '2' if the card came from L/2, else its code ('7' for the 7/E group); call phase_check(effective type)"],
       ["ERR_BAD_MODE: mode not one of the two constants (TrainError)"],
       reads=S("train_deck"), writes=S("train_deck"), calls=D("front_train") + A("phase_check"), triggers=A("phase_check"), consts=C("train_deck"))

action("buy_train", "phase_trains", "Buy a train from the bank", "A company buys one train from the bank (new train in order, or a bank-pool train) at face value; phase effects apply at once. Does NOT require the company to be floated.",
       ["company c", "kind in {major, minor}", "train code", "source in {None, 'new', 'pool'} (None: new train if the code's group is the front group, else pool)"],
       [("c exists in the dict of its kind", "5.3.1"),
        ("code is a known train code; source valid", "5.13.4"),
        ("len(company_trains[c]) < train_limit(kind, phase) BEFORE buying (the phase after the purchase is irrelevant)", "5.13.7"),
        ("code = E: company owns no E-train yet", "5.13.11"),
        ("new train: train_group(code) = front_group (all trains of the previous group bought or exported); pool train: code in bank_pool_trains and phase >= 3", "5.13.4"),
        ("company_cash[c] >= train_cost(code) (price = face value); forced purchase / emergency money is out of scope", "5.13.4")],
       ["[5.13.4] company_cash[c] -= cost; bank_cash += cost",
        "[5.13.8, 5.13.10] new train: remove one card from the group (decrement the first non-zero code of the group); the orientation chosen = the code appended; pool train: remove that code from bank_pool_trains",
        "company_trains[c] += [code] (orientation is final; 7 cannot become E)",
        "[5.13.5, 5.13.6] new train: call phase_check(code) at once (rust, discard, phases); pool train: no phase check (type already in play)"],
       ["ERR_UNKNOWN_COMPANY", "ERR_UNKNOWN_TRAIN", "ERR_BAD_SOURCE", "ERR_TRAIN_LIMIT", "ERR_E_LIMIT", "ERR_NOT_NEXT_TRAIN", "ERR_NOT_IN_POOL", "ERR_INSUFFICIENT_FUNDS"],
       reads=S("company_trains", "phase", "train_deck", "bank_pool_trains", "company_cash"),
       writes=S("company_cash", "bank_cash", "train_deck", "bank_pool_trains", "company_trains"),
       calls=D("train_limit", "front_group", "train_group", "train_cost", "deck_remaining") + A("phase_check"), triggers=A("phase_check"), consts=C("train_costs", "train_deck"))

action("upgrade_l_train", "phase_trains", "Upgrade an L-train to a 2-train", "Flip an owned L-train to a 2-train for 80 in phases 1-2; counts as a train purchase and can start phase 2.",
       ["company c", "kind in {major, minor}"],
       [("c exists in the dict of its kind", "5.3.1"), ("phase <= 2", "5.13.9"), ("the company owns an L-train", "5.13.9"), ("company_cash[c] >= 80", "5.13.9")],
       ["[5.13.9] company_cash[c] -= 80; bank_cash += 80", "one L in company_trains[c] becomes '2' (the card is flipped; the deck counts are unchanged)", "[2.2.3, 5.13.9] call phase_check('2') (counts as a train purchase)"],
       ["ERR_UNKNOWN_COMPANY", "ERR_PHASE", "ERR_NO_L_TRAIN", "ERR_INSUFFICIENT_FUNDS"],
       reads=S("company_trains", "phase", "company_cash"), writes=S("company_cash", "bank_cash", "company_trains"), calls=A("phase_check"), triggers=A("phase_check"), consts=C("train_costs"))

# ---------------------------------------------------------------- resolution
action("resolve_stock_round", "sr_resolution", "Resolve stock round", "Orchestrate the end-of-round procedure (steps in seq order). Callable whenever the caller invokes it: the ROUND MANAGER decides when (no sr_over precondition).", ["none"],
       [("none: no sr_over check, no round_type check (decision GA37); with no bids and no minors in boxes the steps simply do nothing", "4.11.1")],
       ["step1 [4.11.2] resolve_bids -> (items_with_bids, pending_minor_floats)", "step2 [4.11.3-4.11.5] float_minors(pending)", "step3 [4.11.6] unsold_minor_exports(items_with_bids)", "step4 [4.11.7] remove_box1_minor_and_export",
        "step5 [4.11.8, 4.10.2] refill_boxes (shift then fill)", "step6 [4.11.10] charge_interest", "step7 [4.12] raise_sold_out_prices", "step8 [4.11.9] reorder_players_by_cash",
        "step9 [10.1.1] check_game_end_triggers(end_of_stock_round)",
        "does NOT increment sr_completed, change round_type or reset per-round flags (end_stock_round / start_stock_round do)"],
       ["NONE (raises nothing)"],
       calls=A("resolve_bids", "float_minors", "unsold_minor_exports", "remove_box1_minor_and_export", "refill_boxes", "charge_interest", "raise_sold_out_prices", "reorder_players_by_cash", "check_game_end_triggers"),
       triggers=A("resolve_bids", "float_minors", "unsold_minor_exports", "remove_box1_minor_and_export", "refill_boxes", "charge_interest", "raise_sold_out_prices", "reorder_players_by_cash", "check_game_end_triggers"))

action("resolve_bids", "sr_resolution", "Pay and award box items", "Award each item with bids to the highest bidder who can pay; remove tokens. Returns (items_with_bids, pending_minor_floats).", ["none"],
       [("none: callable at any time (R6b: with no bids nothing happens and no sale is recorded)", "4.11.2")],
       ["items_with_bids = every item with >=1 token (snapshot before clearing; returned, not stored)",
        "for item in item_resolution_order: for bidders by amount desc: first with player_cash >= amount wins [R8]: player_cash -= amount; bank_cash += amount [R3]; call vacate_box_item(item, award(bidder)); [R6b] sale_happened = true (an item WON counts as a sale); minors also appended to pending_minor_floats (minor, bid, box_index, buyer)",
        "[R8, R6b] if nobody can pay the item stays in its box, still counts as having had a bid (in items_with_bids) but does NOT set sale_happened",
        "[4.11.2] bids = empty (all tokens removed)"],
       ["NONE (raises nothing)"],
       reads=S("bids", "box_contents", "player_cash"), writes=S("items_with_bids", "player_cash", "bank_cash", "sale_happened", "pending_minor_floats", "bids"),
       calls=A("vacate_box_item") + D("item_resolution_order"))

action("float_minors", "sr_resolution", "Float purchased minors", "Start each purchased minor: price, treasury, token.", ["pending_minor_floats (default none)"],
       [("flotation uses the phase at resolution time, before this round's exports", "4.11.4")],
       ["[4.11.3] for pending in minor_float_order: price = minor_start_price(phase,bid); treasury = minor_start_treasury(phase,bid,price)",
        "[4.11.5] call place_start_token(minor, price, minor)",
        "[R3] bank_cash -= treasury; company_cash[minor] = treasury (buyer already paid the full bid to the bank); the minor is marked floated",
        "[10.1.1] call check_game_end_triggers(after_bank_payment) ONCE after the loop"],
       ["NONE (raises nothing)"],
       reads=S("pending_minor_floats", "phase", "minor_director"), writes=S("company_cash", "bank_cash"),
       calls=D("minor_float_order", "minor_start_price", "minor_start_treasury") + A("place_start_token", "check_game_end_triggers"))

action("unsold_minor_exports", "sr_resolution", "Export per unbid minor", "One L/2 train exported for each remaining minor box item that had no bid.", ["items_with_bids"],
       [("after float_minors", "4.11.6")],
       ["[4.11.6] for each minor still in a box and not in items_with_bids (box indexes ascending): call export_train(L_only)"],
       ["NONE (raises nothing)"],
       reads=S("box_contents", "items_with_bids"), calls=A("export_train"), triggers=A("export_train"))


# ##################################################################################################
# ################################  INTERFACE LAYER: api nodes  ####################################
# ##################################################################################################
# One api node per public function, per exception class and per shared constant of the 8 new modules.
# id = api.<module>.<name>.  Every name that given code imports/calls is kept EXACTLY (given_name=True);
# other names are the v1 names of BINDING.md unless a more descriptive public name was obvious (then the v1 name is an alias).
# Exception convention (decision GA38): every module defines ONE exception class derived directly from Exception;
# message = "<ERR_CODE>: <text>"; attribute .code = the ERR_CODE; no shared base class (layering; given code catches per module).
# Atomicity (decision DN17): every public function validates ALL preconditions before its first mutation.
import ast as _ast

API = {}      # id -> dict
MODULES = ["shares", "certificates", "company_formation", "bidding", "turn_order", "trains", "scoring", "round_manager"]
EXC_OF = {"shares": "ShareError", "certificates": "CertificateError", "company_formation": "ConcessionError", "bidding": "BidError",
          "turn_order": "MarketError", "trains": "TrainError", "scoring": "ScoringError", "round_manager": "RoundError"}
LAYER = {"turn_order": 1, "certificates": 2, "scoring": 3, "trains": 4, "shares": 5, "company_formation": 5, "bidding": 6, "round_manager": 7}


def api(module, signature, implements=(), raises=(), enforced=(), not_enforced=(), callers=(), aliases=(), notes="", returns="", given_name=False, kind="function", **extra):
    """signature: python text 'name(params) -> ret' (functions), 'class X(Base)' (exception/NamedTuple), 'NAME = value' (constant)."""
    assert module in MODULES
    if kind == "function":
        name = signature.split("(")[0]
        _ast.parse("def " + signature + ": pass")  # syntax check, defaults must be explicit python
    elif kind in ("exception", "class"):
        name = signature.split()[1].split("(")[0].rstrip(":")
        _ast.parse(signature + ": pass")
    else:
        name = signature.split("=")[0].strip()
        _ast.parse(signature)
    nid = "api.%s.%s" % (module, name)
    assert nid not in N, nid
    defaults = {}
    if kind == "function":
        fn = _ast.parse("def " + signature + ": pass").body[0]
        a = fn.args
        pos = a.posonlyargs + a.args
        for arg, d in zip(pos[len(pos) - len(a.defaults):], a.defaults):
            defaults[arg.arg] = _ast.unparse(d)
        for arg, d in zip(a.kwonlyargs, a.kw_defaults):
            if d is not None:
                defaults[arg.arg] = _ast.unparse(d)
        params = [x.arg for x in pos + a.kwonlyargs]
    else:
        params = []
    ex = [{"class": c, "code": code, "when": when} for (c, code, when) in raises]
    for e in ex:
        assert e["class"] == EXC_OF[module] or e["class"] == "ValueError", (nid, e)
    attrs = dict(module=module, name=name, kind=kind, signature=signature, params=params, defaults=defaults, returns=returns,
                 raises=ex, enforced=[{"n": i + 1, "check": c, "code": k} for i, (c, k) in enumerate(enforced)], not_enforced=list(not_enforced),
                 given_callers=list(callers), aliases=list(aliases), given_name=bool(given_name), implements=list(implements), notes=notes, layer=LAYER[module])
    attrs.update(extra)
    node(nid, "api", name, "%s.%s: %s" % (module, name, signature), **attrs)
    API[nid] = attrs
    return nid


def exc(module, doc):
    cls = EXC_OF[module]
    api(module, "class %s(Exception)" % cls, kind="exception", given_name=cls in ("ShareError", "ConcessionError", "BidError", "TrainError"),
        notes="Single exception class of the module, derived directly from Exception (decision GA38). Message '<ERR_CODE>: <text>'; attribute .code = ERR_CODE. " + doc,
        bases=["Exception"], callers=({"ShareError": ["actions._apply_buy_share", "actions._apply_sell_shares"], "ConcessionError": ["actions._apply_convert_concession"],
                                      "BidError": ["actions._apply_bid"], "TrainError": ["actions._apply_operate", "operating.first_turn_housekeeping"]}.get(cls, [])))


# ================================================================ turn_order (layer 1)
exc("turn_order", "Raised for market lookups on a company without a token and for invalid start prices.")
api("turn_order", "token_cell(state: GameState, company_id: str) -> tuple[int, int] | None", ["drv.token_cell"], aliases=["market_cell"], returns="(row, col) or None",
    not_enforced=["company_id need not exist: an unknown or tokenless company gives None, no exception"])
api("turn_order", "current_price(state: GameState, company_id: str) -> int", ["drv.current_price"], [("MarketError", "ERR_NO_TOKEN", "the company has no token on the market")], aliases=["share_price"], returns="value of the token's cell",
    enforced=[("company has a token on the market", "ERR_NO_TOKEN")])
api("turn_order", "in_yellow(state: GameState, company_id: str) -> bool", ["drv.in_yellow"], returns="False if the company has no token", not_enforced=["no exception for a tokenless company"])
api("turn_order", "is_game_end_cell(state: GameState, company_id: str) -> bool", ["drv.is_game_end_cell"], returns="False if the company has no token", not_enforced=["no exception for a tokenless company"])
api("turn_order", "start_cell(price: int, kind: str = 'major') -> tuple[int, int]", ["drv.start_cell"], [("MarketError", "ERR_BAD_KIND", "kind not in {'major','minor'}"), ("MarketError", "ERR_BAD_START_PRICE", "price not a start value for the kind (major 60..100, minor 50..100)")],
    enforced=[("kind in {'major','minor'}", "ERR_BAD_KIND"), ("price in 60..100 step 10 for major; 50..100 step 10 for minor", "ERR_BAD_START_PRICE")], returns="(row, col)")
api("turn_order", "place_start_token(state: GameState, company_id: str, price: int, kind: str = 'major') -> None", ["act.place_start_token"],
    [("MarketError", "ERR_BAD_KIND", "bad kind"), ("MarketError", "ERR_BAD_START_PRICE", "bad price for kind")],
    enforced=[("kind in {'major','minor'}", "ERR_BAD_KIND"), ("price valid for kind (start_cell)", "ERR_BAD_START_PRICE")],
    not_enforced=["company exists / is floated / has no token yet (re-placing simply moves the token)"], callers=[], returns="None")
api("turn_order", "move_token_down(state: GameState, company_id: str, steps: int = 1) -> None", ["act.move_token_down"],
    [("MarketError", "ERR_NO_TOKEN", "no token"), ("MarketError", "ERR_BAD_STEPS", "steps not an int >= 0")],
    enforced=[("steps is an int >= 0 (0 = no-op)", "ERR_BAD_STEPS"), ("company has a token", "ERR_NO_TOKEN")], not_enforced=["no game-end check (a drop never reaches the top)"])
api("turn_order", "move_token_up(state: GameState, company_id: str) -> None", ["act.move_token_up"], [("MarketError", "ERR_NO_TOKEN", "no token")],
    enforced=[("company has a token", "ERR_NO_TOKEN")], notes="Calls scoring.check_game_end_triggers(state, 'after_token_move') (LAZY import) after a move onto a game-end cell.")
api("turn_order", "descending_order(state: GameState, company_ids: Iterable[str]) -> list[str]", ["drv.descending_order"], [("MarketError", "ERR_NO_TOKEN", "a listed company has no token")],
    aliases=["descending_share_price_order"], enforced=[("every listed company has a token", "ERR_NO_TOKEN")], returns="ids sorted by stock_positions.descending_price_key (given)")
api("turn_order", "operating_order(state: GameState) -> list[str]", ["drv.operating_order"], returns="floated minors then floated majors, each in descending_order; acquired and removed minors excluded")
api("turn_order", "next_operating_company(state: GameState, done: Iterable[str] = ()) -> str | None", ["drv.next_operating_company"], returns="first company of operating_order(state) (recomputed now) not in done; None if none")
api("turn_order", "compute_stock_round_order(cash: dict[str, int], previous_order: list[str]) -> list[str]", ["drv.compute_stock_round_order"],
    [("MarketError", "ERR_PLAYER_MISMATCH", "cash keys differ from previous_order players")], aliases=["next_player_order"], enforced=[("set(cash) == set(previous_order)", "ERR_PLAYER_MISMATCH")],
    returns="players by cash descending; equal cash keeps previous relative order (stable)")
api("turn_order", "reorder_players_by_cash(state: GameState) -> None", ["act.reorder_players_by_cash"], aliases=["reorder_players"],
    not_enforced=["no exception"], notes="Writes BOTH state.player_order and state.priority_deal_player_id (= player_order[0]).", callers=[])
api("turn_order", "raise_sold_out_prices(state: GameState) -> None", ["act.raise_sold_out_prices"], not_enforced=["no exception"], notes="Snapshot of affected companies and order taken once before any move (A22). Lazy-imports certificates.fully_sold.")

# ================================================================ certificates (layer 2)
exc("certificates", "Raised by swap_director and by lookups of unknown companies.")
api("certificates", "TOTAL_UNITS = 10", kind="constant", value=10, notes="const.share_structure: units per company.")
api("certificates", "POOL_CAP_UNITS = 5", kind="constant", value=5, notes="const.share_structure: bank pool holds at most 5 units.")
api("certificates", "HOLD_CAP_UNITS = 6", kind="constant", value=6, notes="const.share_structure: a player may hold at most 6 units (60%).")
api("certificates", "class SaleCheck(NamedTuple)", kind="class", notes="Fields: legal: bool, swap_needed: bool, successor: str | None, reason: str | None = None. reason is None if legal, else ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY (GAP A20 fix).",
    fields=["legal: bool", "swap_needed: bool", "successor: str | None", "reason: str | None = None"], implements=["drv.sale_legal"])
api("certificates", "cert_units(company_id: str) -> int", ["drv.cert_units"], returns="1 if company_id == 'LNWR' else 2", not_enforced=["no exception for unknown ids"])
api("certificates", "ordinary_certs(state: GameState, player_id: str, company_id: str) -> int", ["st.ordinary_certs"], returns="Player.shares.get(c,0) - cert_units(c) if the player is the director else Player.shares.get(c,0)",
    not_enforced=["unknown ids: 0"], notes="Accessor of the DERIVED state node st.ordinary_certs (units, director's certificate excluded).")
api("certificates", "units_held(state: GameState, player_id: str, company_id: str) -> int", ["drv.units_held"], returns="= Player.shares.get(c, 0)", not_enforced=["unknown ids: 0"])
api("certificates", "certs_held(state: GameState, player_id: str, company_id: str) -> int", ["drv.certs_held"], [("CertificateError", "ERR_UNKNOWN_COMPANY", "company id in neither state.majors nor state.minors")],
    enforced=[("company_id in state.majors or state.minors", "ERR_UNKNOWN_COMPANY")], returns="major: ordinary + (1 if director); minor: 1 if director_player_id == player else 0")
api("certificates", "cert_limit(state: GameState) -> int", ["drv.cert_limit"], returns="SETUP_BY_PLAYER_COUNT[len(player_order)].certificate_limit")
api("certificates", "cert_count_holdings(state: GameState, player_id: str) -> int", ["drv.cert_count_holdings"], returns="certificates counted against the limit; yellow-zone companies count 0; privates and concessions 1 each")
api("certificates", "cert_count(state: GameState, player_id: str) -> int", ["drv.cert_count"], returns="cert_count_holdings + bidding.items_led (LAZY import)")
api("certificates", "over_limit(state: GameState, player_id: str) -> bool", ["drv.over_limit"], returns="cert_count > cert_limit")
api("certificates", "successor(state: GameState, company_id: str, director_id: str, remaining_units: int) -> str | None", ["drv.successor"], returns="eligible successor or None (R5)")
api("certificates", "sale_legal(state: GameState, player_id: str, company_id: str, count: int = 1) -> SaleCheck", ["drv.sale_legal"], returns="SaleCheck; never raises for illegal sales (reason says why)",
    not_enforced=["raises nothing: an unknown or non-major company id gives SaleCheck(False, False, None, 'ERR_NOT_SELLABLE')"])
api("certificates", "can_sell_any(state: GameState, player_id: str) -> bool", ["drv.can_sell_any"], returns="exists major c with sale_legal(p, c, 1).legal")
api("certificates", "must_sell(state: GameState, player_id: str) -> bool", ["drv.must_sell"], returns="over_limit and can_sell_any")
api("certificates", "fully_sold(state: GameState, company_id: str) -> bool", ["drv.fully_sold"], returns="floated major with 0 treasury units and 0 pool units; minors and unknown ids False")
api("certificates", "swap_director(state: GameState, company_id: str, new_director_id: str) -> None", ["act.swap_director"],
    [("CertificateError", "ERR_NOT_STARTED", "the company has no director"), ("CertificateError", "ERR_SAME_DIRECTOR", "new director already is the director"), ("CertificateError", "ERR_NOT_ENOUGH_ORDINARY", "new director holds fewer than cert_units ordinary certificates")],
    enforced=[("company has a director", "ERR_NOT_STARTED"), ("new_director_id != current director", "ERR_SAME_DIRECTOR"), ("ordinary_certs(new) >= cert_units(c)", "ERR_NOT_ENOUGH_ORDINARY")],
    notes="Changes ONLY MajorCompanyState.director_player_id: every Player.shares value is unchanged (units are invariant, T1).")

# ================================================================ scoring (layer 3)
exc("scoring", "Raised only for unknown players in player_wealth / final_ranking.")
api("scoring", "CONTEXT_AFTER_BANK_PAYMENT = 'after_bank_payment'", kind="constant", value="after_bank_payment", notes="check_game_end_triggers context.")
api("scoring", "CONTEXT_AFTER_TOKEN_MOVE = 'after_token_move'", kind="constant", value="after_token_move", notes="check_game_end_triggers context.")
api("scoring", "CONTEXT_END_OF_STOCK_ROUND = 'end_of_stock_round'", kind="constant", value="end_of_stock_round", notes="check_game_end_triggers context; the only one that enables the nothing-sold test (R6b).")
api("scoring", "TRIGGER_NEXT_OR = 'next_or'", kind="constant", value="next_or", notes="end_trigger_pending value for a trigger during a stock round.")
api("scoring", "TRIGGER_OR_END = 'or_end'", kind="constant", value="or_end", notes="end_trigger_pending value: token on game-end cell during an OR.")
api("scoring", "TRIGGER_OR_SET_END = 'or_set_end'", kind="constant", value="or_set_end", notes="end_trigger_pending value: bank broken during an OR (also the converted next_or).")
api("scoring", "CONCESSION_DIVIDEND = 10", kind="constant", value=10, notes="const.concession_dividend (3.4.4).")
api("scoring", "check_game_end_triggers(state: GameState, context: str | None = None) -> None", ["act.check_game_end_triggers"],
    not_enforced=["no exception for unknown context strings (treated as None)", "does not check that a round of the matching type is running; the trigger kind comes from state.round_type", "never sets game_over except for the immediate nothing-sold trigger"],
    callers=["actions.apply_action", "operating._move_price"], given_name=True,
    notes="Callable with ONE argument (given callers). First trigger wins (10.1.2). Called with a context by shares.sell_shares, company_formation.convert_concession/float_minors, turn_order.move_token_up, bidding.resolve_stock_round, scoring.pay_*.")
api("scoring", "bank_broken(state: GameState) -> bool", ["drv.bank_broken"], returns="state.bank.cash < 0")
api("scoring", "player_wealth(state: GameState, player_id: str) -> int", ["drv.player_wealth"], [("ScoringError", "ERR_UNKNOWN_PLAYER", "player_id not in state.players")], enforced=[("player exists", "ERR_UNKNOWN_PLAYER")])
api("scoring", "final_ranking(state: GameState) -> list[tuple[str, int]]", ["drv.final_ranking"], returns="[(player_id, wealth)] richest first; ties keep player_order", aliases=["ranking"],
    notes="needs_owner: tie-break is not in the rulebook.")
api("scoring", "private_revenue(private_number: int, phase: int) -> int", ["drv.private_revenue"], [("ScoringError", "ERR_UNKNOWN_PRIVATE", "number not in PRIVATE_COMPANIES_BY_NUMBER")],
    enforced=[("private number exists in the data table", "ERR_UNKNOWN_PRIVATE")], returns="'£N' -> N; '£Nx phase' -> N*phase")
api("scoring", "pay_concession_dividends(state: GameState) -> None", ["act.pay_concession_dividends"], callers=[], not_enforced=["no exception; phase >= 5 is a no-op"], aliases=["pay_concession_revenue"])
api("scoring", "pay_private_revenues(state: GameState) -> None", ["act.pay_private_revenues"], not_enforced=["no exception; closed privates and zero revenue pay nothing"], aliases=["pay_private_revenue"])

# ================================================================ trains (layer 4)
exc("trains", "Raised by buy_train_from_bank, upgrade_l_train and export_train for rule violations.")
api("trains", "TRAIN_PHASE = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 'E': 7}", kind="constant", value={"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "E": 7}, notes="const.phase_table; 'L' deliberately absent (an L-train never starts a phase).")
api("trains", "TRAIN_GROUPS = (('L', '2'), ('3',), ('4',), ('5',), ('6',), ('7', 'E'))", kind="constant", value=[["L", "2"], ["3"], ["4"], ["5"], ["6"], ["7", "E"]], notes="Deck groups in buying order; a double-sided group is one physical pool (T12).")
api("trains", "SCAN_ORDER = ('L', '2', '3', '4', '5', '6', '7', 'E')", kind="constant", value=["L", "2", "3", "4", "5", "6", "7", "E"], notes="front_train scan order.")
api("trains", "EXPORT_L_ONLY = 'L_only'", kind="constant", value="L_only", notes="export_train mode for 4.11.6.")
api("trains", "EXPORT_NEXT_WITH_PHASE = 'next_with_phase'", kind="constant", value="next_with_phase", notes="export_train mode for 4.11.7.")
api("trains", "MAX_E_TRAINS_PER_COMPANY = 1", kind="constant", value=1, notes="5.13.11.")
api("trains", "phase_of_train(code: str) -> int | None", ["drv.phase_of_train"], returns="TRAIN_PHASE.get(code); None for 'L' and unknown codes", not_enforced=["no exception for unknown codes"])
api("trains", "front_train(state: GameState) -> str | None", ["drv.front_train"], returns="first code in SCAN_ORDER with state.bank.train_pool[code] > 0, else None")
api("trains", "front_group(state: GameState) -> tuple[str, ...] | None", ["drv.front_group"], returns="first group of TRAIN_GROUPS with remaining > 0, else None", aliases=["next_train_group"])
api("trains", "deck_remaining(state: GameState, group: tuple[str, ...]) -> int", ["drv.deck_remaining"], returns="sum of train_pool counts over the group's codes")
api("trains", "train_group(code: str) -> tuple[str, ...]", ["drv.train_group"], [("TrainError", "ERR_UNKNOWN_TRAIN", "code not in TRAIN_GROUPS")], enforced=[("code is a known train code", "ERR_UNKNOWN_TRAIN")])
api("trains", "train_cost(code: str) -> int", ["drv.train_cost"], [("TrainError", "ERR_UNKNOWN_TRAIN", "unknown code")], enforced=[("code is a known train code", "ERR_UNKNOWN_TRAIN")], returns="TRAIN_TYPES_BY_CODE[code].cost")
api("trains", "train_limit(kind: str, phase: int) -> int", ["drv.train_limit"], [("TrainError", "ERR_UNKNOWN_COMPANY", "kind not in {'major','minor'}")], enforced=[("kind in {'major','minor'}", "ERR_UNKNOWN_COMPANY")], returns="PHASES_BY_NUMBER[phase].minor_train_limit / major_train_limit")
api("trains", "phase_check(state: GameState, code: str) -> None", ["act.phase_check"], aliases=["advance_phase", "check_phase"],
    not_enforced=["no exception: unknown code or a code that does not raise the phase is a no-op", "does not require a round type"], notes="Order: phase, rust of every skipped phase, discard excess, clear concessions if old<5<=new, one audit log line.")
api("trains", "rust_trains(state: GameState, code: str) -> None", ["act.rust_trains"], not_enforced=["no exception; unknown code is a no-op"], aliases=["rust"])
api("trains", "discard_excess_trains(state: GameState) -> None", ["act.discard_excess_trains"], not_enforced=["no exception"], aliases=["enforce_train_limit"])
api("trains", "export_train(state: GameState, mode: str) -> None", ["act.export_train"], [("TrainError", "ERR_BAD_MODE", "mode not EXPORT_L_ONLY / EXPORT_NEXT_WITH_PHASE")],
    enforced=[("mode in (EXPORT_L_ONLY, EXPORT_NEXT_WITH_PHASE)", "ERR_BAD_MODE")], not_enforced=["an empty deck is a no-op, never an error"], callers=[])
api("trains", "buy_train_from_bank(state: GameState, company_id: str, kind: str, code: str, source: str | None = None) -> None", ["act.buy_train"],
    [("TrainError", "ERR_UNKNOWN_COMPANY", "kind invalid or company id not in the matching dict"), ("TrainError", "ERR_UNKNOWN_TRAIN", "code unknown"), ("TrainError", "ERR_BAD_SOURCE", "source not None/'new'/'pool'"),
     ("TrainError", "ERR_TRAIN_LIMIT", "company already at its train limit"), ("TrainError", "ERR_E_LIMIT", "code E and the company owns an E-train"),
     ("TrainError", "ERR_NOT_NEXT_TRAIN", "new train outside the front group"), ("TrainError", "ERR_NOT_IN_POOL", "pool train absent from the pool or phase < 3"), ("TrainError", "ERR_INSUFFICIENT_FUNDS", "treasury < face value")],
    enforced=[("kind in {'major','minor'} and company exists in state.majors / state.minors", "ERR_UNKNOWN_COMPANY"), ("code in TRAIN_PHASE or code == 'L'", "ERR_UNKNOWN_TRAIN"), ("source in (None, 'new', 'pool')", "ERR_BAD_SOURCE"),
              ("len(company.trains) < train_limit(kind, phase) (before buying)", "ERR_TRAIN_LIMIT"), ("code != 'E' or no 'E' in company.trains", "ERR_E_LIMIT"),
              ("new: train_group(code) == front_group(state); pool: code in bank.discarded_trains and phase >= 3", "ERR_NOT_NEXT_TRAIN / ERR_NOT_IN_POOL"), ("company.treasury >= train_cost(code)", "ERR_INSUFFICIENT_FUNDS")],
    not_enforced=["the company need NOT be floated (main.py debug and first_turn_housekeeping buy for companies in any state)", "no round_type / active-company / director check (actions.py does that)", "no 'must own a train' rule, no forced purchase (5.13.2 deferred)", "no company-to-company purchase (5.13.3 deferred)"],
    callers=["actions._apply_operate", "operating.first_turn_housekeeping"], given_name=True,
    notes="source None: new train if train_group(code) is the front group, else pool. L may be bought as long as the L/2 group is the front group. Orientation (L/2, 7/E) is the code passed.")
api("trains", "upgrade_l_train(state: GameState, company_id: str, kind: str) -> None", ["act.upgrade_l_train"], aliases=["upgrade_l_to_2"],
    raises=[("TrainError", "ERR_UNKNOWN_COMPANY", "unknown company/kind"), ("TrainError", "ERR_PHASE", "phase > 2"), ("TrainError", "ERR_NO_L_TRAIN", "company owns no L-train"), ("TrainError", "ERR_INSUFFICIENT_FUNDS", "treasury < 80")],
    enforced=[("company exists for kind", "ERR_UNKNOWN_COMPANY"), ("phase <= 2", "ERR_PHASE"), ("'L' in company.trains", "ERR_NO_L_TRAIN"), ("treasury >= 80", "ERR_INSUFFICIENT_FUNDS")], not_enforced=["company need not be floated"])

# ================================================================ shares (layer 5)
exc("shares", "Raised by sell_shares, buy_share, repay_loans.")
api("shares", "SOURCE_BANK = 'bank'", kind="constant", value="bank", notes="buy_share source string: the bank pool (same as 'pool').")
api("shares", "SOURCE_POOL = 'pool'", kind="constant", value="pool", notes="buy_share source string: the bank pool.")
api("shares", "SOURCE_TREASURY = 'treasury'", kind="constant", value="treasury", notes="buy_share source string: the company treasury.")
api("shares", "interest_amount(loans: int) -> int", ["drv.interest_amount"], returns="(loans + 1) // 2", aliases=["loan_interest"])
api("shares", "charge_interest(state: GameState) -> None", ["act.charge_interest"], aliases=["apply_interest"], not_enforced=["no exception; bank cash is unchanged (4.3.5)"])
api("shares", "sell_shares(state: GameState, player_id: str, company_id: str, count: int = 1) -> None", ["act.sell_shares"],
    [("ShareError", "ERR_UNKNOWN_PLAYER", "player_id not in state.players"), ("ShareError", "ERR_NOT_SELLABLE", "not a major / not floated / has not completed an OR"), ("ShareError", "ERR_BAD_COUNT", "count not an int >= 1"),
     ("ShareError", "ERR_POOL_FULL", "pool would exceed 5 units"), ("ShareError", "ERR_TOO_MANY", "sale_legal says illegal otherwise (holdings, no successor)")],
    enforced=[("player exists", "ERR_UNKNOWN_PLAYER"), ("company_id is a key of state.majors", "ERR_NOT_SELLABLE"), ("count is an int >= 1 (bool rejected)", "ERR_BAD_COUNT"),
              ("major.floated and major.has_operated", "ERR_NOT_SELLABLE"), ("shares_in_bank_pool + count <= 5", "ERR_POOL_FULL"), ("certificates.sale_legal(...).legal", "ERR_TOO_MANY")],
    not_enforced=["round type / active player (actions.py)", "loans (do not block selling)", "sold_this_round, certificate limit, turn stage"], callers=["actions._apply_sell_shares"], aliases=["sell_share"], given_name=True,
    notes="Sets any_sale_this_stock_round itself (actions.py does not for sells).")
api("shares", "buy_share(state: GameState, player_id: str, company_id: str, source: str | None = None) -> None", ["act.buy_share"],
    [("ShareError", "ERR_UNKNOWN_PLAYER", "unknown player"), ("ShareError", "ERR_BAD_SOURCE", "source not None/'treasury'/'pool'/'bank'"), ("ShareError", "ERR_LOANS", "player has loans"), ("ShareError", "ERR_MUST_SELL", "over the limit and able to sell"),
     ("ShareError", "ERR_NOT_STARTED", "not a floated major with a director"), ("ShareError", "ERR_NO_SHARE_AT_SOURCE", "chosen source (or both when None) holds no share"), ("ShareError", "ERR_INSUFFICIENT_CASH", "cash < price"),
     ("ShareError", "ERR_SOLD_THIS_ROUND", "player sold the company this round"), ("ShareError", "ERR_AT_60_PERCENT", "player holds >= 6 units"), ("ShareError", "ERR_CERT_LIMIT", "cert_count + 1 > limit and company not yellow")],
    enforced=[("player exists", "ERR_UNKNOWN_PLAYER"), ("source in (None, 'treasury', 'pool', 'bank')", "ERR_BAD_SOURCE"), ("player.loans == 0", "ERR_LOANS"), ("not certificates.must_sell", "ERR_MUST_SELL"),
              ("company is a major, floated, director not None", "ERR_NOT_STARTED"), ("source holds >= 1 certificate", "ERR_NO_SHARE_AT_SOURCE"), ("cash >= current_price", "ERR_INSUFFICIENT_CASH"),
              ("company not in sold_this_round[player]", "ERR_SOLD_THIS_ROUND"), ("units_held < 6", "ERR_AT_60_PERCENT"), ("in_yellow or cert_count + 1 <= cert_limit", "ERR_CERT_LIMIT")],
    not_enforced=["round type / active player (actions.py)", "money committed in leading bids (A7)", "one certificate per turn (guaranteed by the turn model)"], callers=["actions._apply_buy_share"], aliases=["buy_certificate"], given_name=True,
    notes="source None: 'pool' if the pool holds a share else 'treasury' (needs_owner, A12). 'bank' and 'pool' both mean the bank pool. Sets any_sale_this_stock_round itself.")
api("shares", "repay_loans(state: GameState, player_id: str, amount: int | None = None) -> None", ["act.repay_loans"],
    [("ShareError", "ERR_UNKNOWN_PLAYER", "unknown player"), ("ShareError", "ERR_NO_LOANS", "loans == 0"), ("ShareError", "ERR_BAD_AMOUNT", "amount not an int, <= 0 or > loans"), ("ShareError", "ERR_INSUFFICIENT_CASH", "cash < amount")],
    enforced=[("player exists", "ERR_UNKNOWN_PLAYER"), ("loans > 0", "ERR_NO_LOANS"), ("amount is None (= min(loans, cash)) or an int with 0 < amount <= loans", "ERR_BAD_AMOUNT"), ("cash >= amount", "ERR_INSUFFICIENT_CASH")],
    not_enforced=["no caller in the skeleton (wired=false); no round/stage check"], aliases=["repay_loan"])

# ================================================================ company_formation (layer 5)
exc("company_formation", "Raised by convert_concession.")
api("company_formation", "MAJOR_START_PRICES = (60, 70, 80, 90, 100)", kind="constant", value=[60, 70, 80, 90, 100], notes="const.start_values for majors.")
api("company_formation", "MINOR_START_PRICES = (50, 60, 70, 80, 90, 100)", kind="constant", value=[50, 60, 70, 80, 90, 100], notes="const.start_values for minors.")
api("company_formation", "convert_concession(state: GameState, player_id: str, abbr: str, start_price: int) -> None", ["act.convert_concession"],
    [("ConcessionError", "ERR_PHASE", "phase not in 2..4"), ("ConcessionError", "ERR_NOT_HELD", "abbr not in the player's concessions / unknown"), ("ConcessionError", "ERR_ALREADY_STARTED", "major already floated"),
     ("ConcessionError", "ERR_LOANS", "player has loans"), ("ConcessionError", "ERR_MUST_SELL", "must_sell"), ("ConcessionError", "ERR_BAD_START_PRICE", "start_price not in MAJOR_START_PRICES"), ("ConcessionError", "ERR_INSUFFICIENT_CASH", "non-LNWR: cash < 2*start_price - 100")],
    enforced=[("2 <= phase <= 4", "ERR_PHASE"), ("abbr in player.concessions (unknown abbr -> same code)", "ERR_NOT_HELD"), ("not major.floated", "ERR_ALREADY_STARTED"), ("player.loans == 0", "ERR_LOANS"),
              ("not certificates.must_sell", "ERR_MUST_SELL"), ("start_price in MAJOR_START_PRICES", "ERR_BAD_START_PRICE"), ("LNWR: nothing; else cash >= 2*start_price - 100", "ERR_INSUFFICIENT_CASH")],
    not_enforced=["round type / active player (actions.py)", "certificate limit (count unchanged)", "leading bids"], callers=["actions._apply_convert_concession"], given_name=True, aliases=["convert_concession_to_director"],
    notes="Sets any_sale_this_stock_round itself, sets concession_converted True, concession_holder None, has_operated False.")
api("company_formation", "minor_start_price(phase: int, bid: int) -> int", ["drv.minor_start_price"], returns="phase 1: 50; else max start value <= bid//2, min 50, max 100", not_enforced=["no exception"], aliases=["start_price_for_minor"])
api("company_formation", "minor_start_treasury(phase: int, bid: int, price: int | None = None) -> int", ["drv.minor_start_treasury"], returns="phase 1: 100; phase 2: 2*price; phase >= 3: bid; price None = minor_start_price(phase, bid)", not_enforced=["no exception"])
api("company_formation", "minor_float_order(pending: Iterable[tuple[int, int, int, str]]) -> list[tuple[int, int, int, str]]", ["drv.minor_float_order"], returns="bid descending, tie lower box_index first")
api("company_formation", "float_minors(state: GameState, pending: Iterable[tuple[int, int, int, str]] | None = None) -> None", ["act.float_minors"], not_enforced=["no exception; None or empty is a no-op"],
    notes="pending items are (minor_number, bid, box_index, buyer_player_id). Sets MinorCompanyState.floated, treasury, share_price. Calls check_game_end_triggers once after the loop.", aliases=["float_minor_companies"])

# ================================================================ bidding (layer 6)
exc("bidding", "Raised by place_or_move_bid, vacate_box_item.")
api("bidding", "FACE_VALUES = {'concession': 100, 'minor': 100, 'private': 0}", kind="constant", value={"concession": 100, "minor": 100, "private": 0}, notes="const.face_values")
api("bidding", "BID_MULTIPLE = 5", kind="constant", value=5, notes="const.bid_rules")
api("bidding", "MAX_BIDS_PER_TURN = 3", kind="constant", value=3, notes="const.bid_rules")
api("bidding", "ITEM_KINDS = ('minor', 'concession', 'private')", kind="constant", value=["minor", "concession", "private"], notes="Refill order and the kind order used as tie-break in item_resolution_order.")
api("bidding", "face_value(kind: str) -> int", ["drv.face_value"], [("BidError", "ERR_ITEM_NOT_IN_BOX", "kind not in ITEM_KINDS")], enforced=[("kind in ITEM_KINDS", "ERR_ITEM_NOT_IN_BOX")])
api("bidding", "highest_bid(item: BidBoxItem) -> int | None", ["drv.highest_bid"], returns="max(item.bids.values()) or None (a bid of 0 is a bid)")
api("bidding", "highest_bidder(item: BidBoxItem) -> str | None", ["drv.highest_bidder"], returns="argmax of item.bids or None")
api("bidding", "committed_money(state: GameState, player_id: str) -> int", ["drv.committed_money"], returns="sum of highest bids on items the player leads")
api("bidding", "items_led(state: GameState, player_id: str) -> int", ["drv.items_led"], returns="count of items the player leads")
api("bidding", "tokens_total(state: GameState) -> int", ["drv.tokens_total"], returns="SETUP_BY_PLAYER_COUNT[n].bidding_tokens")
api("bidding", "tokens_used(state: GameState, player_id: str) -> int", ["drv.tokens_used"], returns="items with the player in bids")
api("bidding", "min_legal_bid(item: BidBoxItem) -> int", ["drv.min_legal_bid"], returns="face value if no bids else highest + 5")
api("bidding", "bid_amount_error(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> str | None", ["drv.bid_amount_error"], returns="ERR_BAD_AMOUNT | ERR_BID_TOO_LOW | ERR_INSUFFICIENT_CASH | None", not_enforced=["returns a code, never raises"])
api("bidding", "bid_amount_valid(state: GameState, player_id: str, item: BidBoxItem, amount: int) -> bool", ["drv.bid_amount_valid"], returns="bid_amount_error(...) is None",
    notes="Kept for v1 compatibility; thin wrapper over bid_amount_error.")
api("bidding", "item_resolution_order(state: GameState) -> list[tuple[str, int]]", ["drv.item_resolution_order"], returns="(kind, box_index) of items with bids by (highest bid desc, box_index asc, kind order minor<concession<private)")
api("bidding", "place_or_move_bid(state: GameState, player_id: str, kind: str, box_index: int, amount: int) -> None", ["act.place_bid", "act.move_bid"],
    [("BidError", "ERR_ITEM_NOT_IN_BOX", "kind/box invalid, empty box, or concession while phase >= 5"), ("BidError", "ERR_TOO_MANY_BIDS", "bids_this_turn >= 3"), ("BidError", "ERR_LOANS", "player has loans"), ("BidError", "ERR_MUST_SELL", "must_sell"),
     ("BidError", "ERR_CERT_LIMIT", "cert_count >= limit"), ("BidError", "ERR_BAD_AMOUNT", "not an int multiple of 5"), ("BidError", "ERR_BID_TOO_LOW", "below min_legal_bid"), ("BidError", "ERR_INSUFFICIENT_CASH", "committed + amount > cash"),
     ("BidError", "ERR_NO_TOKENS", "place branch: no unallocated token"), ("BidError", "ERR_NOT_OUTBID", "move branch: the player already leads")],
    enforced=[("kind in ITEM_KINDS, 0 <= box_index < len(boxes), box not None, concession only if phase < 5", "ERR_ITEM_NOT_IN_BOX"), ("state.bids_this_turn < 3 (READ ONLY)", "ERR_TOO_MANY_BIDS"), ("player.loans == 0", "ERR_LOANS"),
              ("not must_sell", "ERR_MUST_SELL"), ("cert_count < cert_limit", "ERR_CERT_LIMIT"), ("bid_amount_error is None (int, not bool; multiple of 5)", "ERR_BAD_AMOUNT / ERR_BID_TOO_LOW / ERR_INSUFFICIENT_CASH"),
              ("place (player not in item.bids): tokens_used < tokens_total", "ERR_NO_TOKENS"), ("move (player in item.bids): player is not the highest bidder", "ERR_NOT_OUTBID")],
    not_enforced=["round type / active player (actions.py)", "never writes bids_this_turn (the caller increments it)", "no atomicity across the 3 bids of one action (the caller loops)"],
    callers=["actions._apply_bid"], given_name=True, aliases=["place_bid", "move_bid"], notes="Branch: player_id in item.bids -> move, else place.")
api("bidding", "shift_boxes(state: GameState) -> None", ["act.shift_boxes"], not_enforced=["no exception"])
api("bidding", "refill_boxes(state: GameState) -> None", ["act.refill_boxes"], not_enforced=["no exception; concession kind skipped when phase >= 5 (R9)"], callers=[])
api("bidding", "clear_concession_boxes(state: GameState) -> None", ["act.clear_concession_boxes"], not_enforced=["idempotent; no precondition on the phase"])
api("bidding", "vacate_box_item(state: GameState, kind: str, box_index: int, disposition: str, player_id: str | None = None) -> None", ["act.vacate_box_item"],
    [("BidError", "ERR_ITEM_NOT_IN_BOX", "box empty or invalid"), ("BidError", "ERR_BAD_DISPOSITION", "disposition not 'award'/'remove' or award without player_id")],
    enforced=[("box holds an item", "ERR_ITEM_NOT_IN_BOX"), ("disposition in {'award','remove'}; award needs player_id", "ERR_BAD_DISPOSITION")])
api("bidding", "resolve_bids(state: GameState) -> tuple[set[tuple[str, int]], list[tuple[int, int, int, str]]]", ["act.resolve_bids"], returns="(items_with_bids, pending_minor_floats)", not_enforced=["no exception; no sr_over check"],
    notes="Sets any_sale_this_stock_round when at least one item is WON (R6b).")
api("bidding", "unsold_minor_exports(state: GameState, items_with_bids: Iterable[tuple[str, int]] = ()) -> None", ["act.unsold_minor_exports"], not_enforced=["no exception"])
api("bidding", "remove_box1_minor_and_export(state: GameState) -> None", ["act.remove_box1_minor_and_export"], not_enforced=["no exception; no-op if minor box 1 is empty"])
api("bidding", "resolve_stock_round(state: GameState) -> None", ["act.resolve_stock_round"], not_enforced=["NO sr_over check, NO round_type check: callable whenever the caller invokes it (the round manager decides when)", "does not increment sr_completed, switch round type or reset round flags"],
    callers=["actions (imported, unused)", "round_manager.end_stock_round"], given_name=True)

# ================================================================ round_manager (layer 7)
exc("round_manager", "Raised for invalid player ids, game over and missing active company.")
api("round_manager", "sr_over(state: GameState) -> bool", ["drv.sr_over"], returns="state.consecutive_passes >= len(state.player_order)")
api("round_manager", "next_player(state: GameState, player_id: str) -> str", ["drv.next_player"], [("RoundError", "ERR_WRONG_PLAYER", "player_id not in player_order")], enforced=[("player_id in player_order", "ERR_WRONG_PLAYER")])
api("round_manager", "begin_turn(state: GameState, player_id: str) -> None", ["act.begin_turn"], [("RoundError", "ERR_WRONG_PLAYER", "player_id not in player_order")], enforced=[("player_id in player_order", "ERR_WRONG_PLAYER")],
    not_enforced=["that player_id is the correct successor (callers guarantee)"], notes="Sets active_player_id and bids_this_turn = 0.")
api("round_manager", "start_stock_round(state: GameState) -> None", ["act.start_stock_round"], [("RoundError", "ERR_GAME_OVER", "state.game_over")], enforced=[("not state.game_over", "ERR_GAME_OVER")],
    not_enforced=["no 'already running' check (main.py debug calls it at any time)"], callers=["main.debug_force_round"], given_name=True)
api("round_manager", "advance_stock_player(state: GameState) -> None", ["act.end_turn"], aliases=["end_turn"], not_enforced=["raises nothing; does not touch consecutive_passes; does not check must_sell"], returns="None",
    callers=["actions._apply_bid", "actions._apply_buy_share", "actions._apply_sell_shares", "actions._apply_convert_concession", "actions._apply_pass"], given_name=True)
api("round_manager", "end_stock_round(state: GameState) -> None", ["act.end_stock_round"], [("RoundError", "ERR_GAME_OVER", "game_over already set at entry")], enforced=[("not state.game_over", "ERR_GAME_OVER")],
    not_enforced=["NO sr_over check (the caller actions._apply_pass verified it; tests may call directly)", "no round_type check"], callers=["actions._apply_pass"], given_name=True,
    notes="Order: phase_before = phase; bidding.resolve_stock_round; stock_rounds_completed += 1; if game_over: stop; else start_operating_round(state, phase_before).")
api("round_manager", "active_company_id(state: GameState) -> str | None", ["drv.active_company"], returns="None unless round_type is OPERATING and 0 <= current_company_index < len(operating_order)", callers=["actions._apply_operate", "actions._apply_pass"], given_name=True, aliases=["active_company"])
api("round_manager", "advance_company(state: GameState) -> None", ["act.advance_company"], [("RoundError", "ERR_NO_ACTIVE_COMPANY", "no company is active")], enforced=[("active_company_id(state) is not None", "ERR_NO_ACTIVE_COMPANY")],
    callers=["actions._apply_operate", "actions._apply_pass"], given_name=True, notes="Sets has_operated True for a major that finished its turn.")
api("round_manager", "start_operating_round(state: GameState, phase_before: int | None = None) -> None", ["act.start_operating_round"], [("RoundError", "ERR_GAME_OVER", "state.game_over")], enforced=[("not state.game_over", "ERR_GAME_OVER")],
    not_enforced=["round_type of the caller"], notes="phase_before None = current phase (no 2.1.2 deferral).")
api("round_manager", "begin_operating_round(state: GameState) -> None", ["act.begin_operating_round"], not_enforced=["raises nothing"], aliases=["start_operating_set_round"])
api("round_manager", "end_operating_round(state: GameState) -> None", ["act.end_operating_round"], not_enforced=["raises nothing"])
api("round_manager", "operating_rounds_for_next_set(state: GameState, phase_before: int | None = None) -> int", ["drv.operating_rounds_for_next_set"], returns="1 or 2 with the 2.1.2 deferral; 1 if end_trigger_pending == 'next_or'", not_enforced=["raises nothing"])


# given-code actions: no api node, a given_symbol instead (checked by check_graph.py against the given files)
setattrs("act.setup_game", implementation="given", given_symbol="engine/setup.py:new_game")
setattrs("act.apply_action", implementation="given", given_symbol="engine/actions.py:apply_action")
setattrs("act.stock_turn_action", implementation="given", given_symbol="engine/actions.py:_apply_bid")
setattrs("act.pass_turn", implementation="given", given_symbol="engine/actions.py:_apply_pass")
setattrs("act.operate_company", implementation="given", given_symbol="engine/actions.py:_apply_operate")

# ##################################################################################################
# ################################  REPRESENTATION LAYER: repr nodes  ##############################
# ##################################################################################################
REPRS = {}


def reprn(id, concept, maps_to, rule, binds, source="skeleton", **extra):
    """Where a graph concept lives in the given data model. binds = ids of state/entity/constant/action/derived/api nodes."""
    nid = "repr." + id
    node(nid, "repr", concept, maps_to, concept=concept, maps_to=maps_to, rule_for_coder=rule, binds=list(binds), source=source, **extra)
    REPRS[nid] = list(binds)


reprn("units_vs_certificates", "Units vs certificates", "Player.shares[company_id] = UNITS of 10% INCLUDING the director's certificate (2 units; LNWR 1)",
      "units_held(p,c) = Player.shares.get(c,0); ordinary_certs(p,c) = units_held - cert_units(c) if p is the director else units_held; certs_held(p,c) = ordinary_certs + (1 if director). Always read with .get(c, 0); zero entries may exist. A swap_director changes NO Player.shares value.",
      ["st.ordinary_certs", "ent.share_certificate", "drv.units_held", "drv.certs_held", "api.certificates.ordinary_certs"], "BINDING T1, GAPS A13/B-1")
reprn("director_certificate", "Director's certificate", "MajorCompanyState.director_player_id (None until started) + cert_units units inside Player.shares[c]",
      "ONE certificate for the limit regardless of its units; the holder's Player.shares includes the units; it is never in shares_in_treasury or shares_in_bank_pool; LNWR director = 1 unit.",
      ["st.director_holder", "ent.director_certificate", "ent.lnwr", "drv.cert_units"], "BINDING A.1/T1")
reprn("minor_ownership", "Minor company ownership", "MinorCompanyState.director_player_id (non-None after award); NO entry in Player.shares; id 'M<n>'",
      "A minor counts 1 certificate for its director (certs_held dispatches on `cid in state.minors`). floated=True is set by float_minors; removed=True for a removed minor (director stays None). Follows the graph, not the models.py comment (decision GA10).",
      ["st.minor_director", "ent.minor_company"], "GAPS A10")
reprn("company_keys", "Company, item and player keys", "major = abbreviation str ('LNWR','GWR','L&YR',...), key of majors/stock_positions/Player.shares/Player.concessions; minor = 'M<n>' (str key) with bare int n in MinorCompanyState.number, minor_stack and BidBoxItem.ref; private = int n; concession = the major's abbr; player = 'p1'..'pN'",
      "Item kind strings are 'concession' | 'minor' | 'private'; company kind arguments are 'major' | 'minor'. A concession is NOT a separate object.",
      ["ent.major_company", "ent.minor_company", "ent.private_company", "ent.concession", "ent.player", "st.concession_stack", "st.minor_stack", "st.private_stack"], "BINDING A.0")
reprn("concession", "Concession", "Player.concessions: list[str] of major abbr; BidBoxItem(kind='concession', ref=abbr); MajorCompanyState.concession_holder_player_id mirrors the holder (None after conversion/clearing); concession_converted True after conversion",
      "Removal at phase 5 = absent from stack, boxes and players (no field). Writers keep the mirror fields consistent (vacate_box_item sets, convert_concession/clear_concession_boxes clear).",
      ["st.player_concessions", "ent.concession", "st.removed_items"], "BINDING A.1, GAPS B-5/B-7")
reprn("private_company", "Private company", "Player.private_companies: list[int]; PrivateCompanyState(number, owner_player_id mirror, owner_company_id, closed, treasury_credit)",
      "pay_private_revenues pays every open private: if owner_company_id is set -> that company's treasury, else the player holding it in Player.private_companies; closed privates pay nothing.",
      ["st.player_privates", "st.private_status", "ent.private_company", "const.private_revenue_table"], "BINDING A.1; v2")
reprn("boxes_zero_based", "Bid boxes", "state.concession_bid_boxes (len 3), state.minor_bid_boxes (len 4), state.private_bid_boxes (len 3): elements BidBoxItem | None, lists keep their length (None padding)",
      "Graph 'box number' = list index + 1 ('box 1' = index 0; 'lower box number wins' = lower index). An item's identity in function signatures is (kind, box_index). Box counts: engine.setup.NUM_*_BID_BOXES.",
      ["st.box_contents", "ent.bid_box", "const.box_counts"], "BINDING T3, GAPS A12")
reprn("bid_box_item", "Item sitting in a box", "BidBoxItem(kind, ref, bids): ref is str (abbr) for concession, int for minor and private (the int annotation in models.py is wrong for concessions)",
      "state.minors key = f'M{ref}'.", ["st.box_contents", "ent.item_stack"], "BINDING T4")
reprn("bids", "Bids and bidding tokens", "BidBoxItem.bids: dict[player_id, int] (one entry = one token on the item's track)",
      "highest_bid = max(bids.values()) if bids else None; a bid of 0 is a bid (never `if highest_bid:`). Tokens in use = items with the player in bids. Empty dict = no bid.",
      ["st.bids", "ent.bidding_token", "drv.highest_bid", "drv.highest_bidder", "drv.tokens_used"], "BINDING T11")
reprn("sr_order", "Stock-turn order", "state.player_order (list, index 0 = Player-1 card) AND state.priority_deal_player_id",
      "player_count = len(state.player_order) (3..7; no stored field). Invariant: priority_deal_player_id == player_order[0]. Writers of player_order (reorder_players_by_cash, setup) rewrite priority_deal_player_id too; start_stock_round re-asserts it.",
      ["st.sr_order", "st.player_count", "ent.player_order_card", "act.reorder_players_by_cash"], "BINDING A.1, GAPS A40")
reprn("sr_start_player", "Stock round start / priority player", "state.active_player_id = player_order[0] at the start of every stock round",
      "Round 1: set by setup.new_game (the first stock round is pre-started, start_stock_round is not called). Later rounds: start_stock_round -> begin_turn(player_order[0]). Order of play inside a round: next_player(state, pid) = player_order[(index+1) % n]; bids_this_turn reset by begin_turn.",
      ["st.turn", "act.start_stock_round", "act.begin_turn", "act.setup_game"], "GAPS A4")
reprn("turn_record", "Turn record", "state.active_player_id (turn.active_player) and state.bids_this_turn (turn.bids_made); NO fields for stage / c_used / acted (dropped in v2)",
      "SKELETON TURN MODEL: every successful sell_shares / buy_share / convert_concession / bid action ends the turn (actions.py calls advance_stock_player). bids_this_turn is incremented by actions.py after each place_or_move_bid and reset by begin_turn; the bidding module only READS it.",
      ["st.turn", "act.stock_turn_action", "act.end_turn"], "GAPS A1/A6")
reprn("pass_streak", "Consecutive passes", "state.consecutive_passes", "Written ONLY by actions.py (+=1 on pass; =0 after a turn-ending action) and reset by start_stock_round; advance_stock_player must not touch it. Round over when >= len(player_order).",
      ["st.pass_streak", "drv.sr_over", "act.pass_turn"], "BINDING T6")
reprn("sale_flag", "'A sale happened' flag", "state.any_sale_this_stock_round (bool)",
      "Set True by: sell_shares, buy_share, convert_concession (module functions themselves; actions.py also sets it after buy and convert), and resolve_bids when a bid-box item is WON (R6b). Reset to False by start_stock_round. Read by check_game_end_triggers(context='end_of_stock_round').",
      ["st.sale_happened", "ruling.R6b", "act.resolve_bids"], "GAPS A7")
reprn("sold_this_round", "sold_this_round", "state.sold_this_round: dict[player_id, list[company_id]] (lists without duplicates, NOT sets: rooms.serialize_state cannot encode sets)",
      "Readers: `company_id in state.sold_this_round.get(player_id, ())`. Reset to {} by start_stock_round.", ["st.sold_this_round"], "GAPS A11")
reprn("bank_pool_naming", "Bank pool naming", "SHARES: MajorCompanyState.shares_in_bank_pool (units, max 5) = 'the bank pool'; TRAINS: BankState.discarded_trains (list of codes) = 'the bank pool' of trains",
      "buy_share source strings: 'bank' and 'pool' BOTH mean the bank pool of shares; 'treasury' = MajorCompanyState.shares_in_treasury (ordinary units only, the director's certificate is never in it; LNWR 9, others 8 at flotation); None = module chooses (pool first, else treasury).",
      ["st.pool_shares", "st.treasury_shares", "ent.bank_pool", "ent.company_treasury", "st.bank_pool_trains", "api.shares.SOURCE_BANK", "api.shares.SOURCE_POOL", "api.shares.SOURCE_TREASURY"], "GAPS A22/A39")
reprn("money", "Cash, loans, bank, treasuries", "Player.cash, Player.loans (pounds), state.bank.cash (may be negative; initial 9900; the BankState default 12000 is unused), MajorCompanyState.treasury / MinorCompanyState.treasury",
      "Loans never touch bank.cash (4.3.5). Interest: loans += (loans + 1) // 2. Money is integer pounds, use //.",
      ["st.player_cash", "st.player_loans", "st.bank_cash", "st.company_cash", "ent.bank", "ent.loan", "const.interest", "const.bank_total", "const.start_money"], "BINDING A.1")
reprn("company_status", "Company status mirrors", "MajorCompanyState.floated / concession_converted / has_operated / share_price; MinorCompanyState.floated / share_price / removed / acquired_by_major",
      "floated=True and concession_converted=True on conversion; has_operated False at flotation, True after the first completed operating turn (advance_company); share_price is a display mirror nobody reads (read prices from the grid via current_price).",
      ["st.major_status", "st.has_completed_or", "st.removed_items"], "BINDING T15/T16, GAPS B-5")
reprn("market_cells", "Stock market cells and piles", "state.stock_positions[company_id] = (row, col); state.stock_stack[(row, col)] = list of company ids, index 0 = TOP; grid app.data.stock_market.STOCK_MARKET_BY_POSITION[(row, col)] -> StockCell(row, col, value, zone, game_end)",
      "Use stock_positions.place_token (removes from the old pile, APPENDS to the new = bottom) only when the cell changes; emptied piles remain as empty lists; down = (row+1, col), up = (row-1, col), absent cell = no move (R12); yellow = zone 'yellow'; game end = game_end True; start cells derived from zone in {'start','minor_start'}. Minors enter after the leading run of minor tokens (4.11.5).",
      ["st.market_stack", "ent.stock_market", "ent.market_cell", "ent.stock_token", "const.market_grid", "const.yellow_cells", "const.game_end_cells", "const.start_cells"], "BINDING T7-T9")
reprn("train_deck_counts", "Train deck", "state.bank.train_pool: dict[code, count]; setup: L 22, 2 0, 3 9, 4 6, 5 3, 6 3, 7 16, E 0",
      "Groups L/2 and 7/E are ONE physical pool each: remaining(group) = sum of the codes' counts; a card leaves by decrementing the first non-zero code of the group in order (L then 2; 7 then E) whatever side is bought or exported; the side chosen at purchase is recorded only as the code in the company's train list. front_train = first code in L,2,3,4,5,6,7,E with count > 0.",
      ["st.train_deck", "const.train_deck", "ent.train", "drv.front_train", "drv.front_group", "drv.deck_remaining"], "BINDING T12, GAPS A27")
reprn("company_trains", "Trains of companies and of the bank pool", "MajorCompanyState.trains / MinorCompanyState.trains: list[str] of codes ('L','2','3',...,'7','E'); BankState.discarded_trains: list[str] (bank pool, orientation kept)",
      "Purchase appends the code chosen; rust removes by code everywhere (companies, pool, deck counts); discard moves one code to discarded_trains; 'E' appears at most once per company.",
      ["st.company_trains", "st.bank_pool_trains"], "v2")
reprn("phase_state", "Phase", "state.phase: int 1..7; limits and rust from app.data.phases.PHASES_BY_NUMBER; trigger table trains.TRAIN_PHASE (module constant)",
      "phase only increases (2.2.1) and is written only by phase_check (plus debug code in main.py). PHASES_BY_NUMBER[n].trains_rusted gives ONE code per phase; skipped phases are rusted too (loop old+1..new).",
      ["st.phase", "const.phase_table", "const.rust_table", "api.trains.TRAIN_PHASE"], "BINDING A.1, GAPS A26")
reprn("round_type", "Round type", "state.round_type: Enum RoundType.STOCK / RoundType.OPERATING (compare with the Enum, not strings); no field for sr_status (dropped)",
      "STOCK from setup (round 1 is pre-started); OPERATING set by start_operating_round; STOCK again by start_stock_round.", ["st.round_type", "act.start_operating_round", "act.start_stock_round"], "GAPS A5")
reprn("sr_counter", "Stock-round counter", "state.stock_rounds_completed (starts 0); state.round_number (starts 1) is NOT maintained by the engine",
      "sr_completed = stock_rounds_completed; incremented by end_stock_round AFTER resolve_stock_round returned; the 10.1.1 'first stock round' test is stock_rounds_completed == 0 inside step 9.",
      ["st.sr_completed"], "GAPS A42")
reprn("game_end", "Game end", "state.game_over: bool and state.end_trigger_pending: None | 'next_or' | 'or_end' | 'or_set_end'",
      "graph trigger none = (False, None); immediate = game_over True; 'a trigger exists' = game_over or end_trigger_pending is not None. 'next_or': stock-round trigger, converted to 'or_set_end' with set size 1 when the next OR set starts; 'or_end': token on game-end cell in an OR (ends after that OR); 'or_set_end': bank broken in an OR (ends after the set). game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured).",
      ["st.game_end", "const.game_end_triggers", "act.end_operating_round"], "BINDING A.1")
reprn("operating_round_state", "Operating-round bookkeeping", "state.operating_rounds_this_set (set size, locked at set start; default 1), state.operating_round_index (0-based), state.operating_order (companies chosen so far), state.current_company_index",
      "active_company_id = operating_order[current_company_index] if round_type is OPERATING and the index is in range. The 2.1.2 deferral needs NO extra field: start_operating_round receives phase_before (a local value from end_stock_round) and the set size is ors_per_sr[phase_before], locked in operating_rounds_this_set.",
      ["st.or_set_size", "st.or_index", "st.or_order", "st.or_current", "ent.operating_round"], "GAPS A8")
reprn("phase_log", "Phase events", "one line per phase change appended to state.log: 'PHASE_EVENT from=<old> to=<new> rusted=<codes comma-separated or -> discarded=<n> or_per_sr=<n>'",
      "Audit only; there is no consumer; rust, discard and concession clearing happen inside phase_check.", ["st.phase_events"], "GAPS B-8")
reprn("call_scoped", "Values that live only inside one procedure", "items_with_bids -> set[(kind, box_index)] and pending_minor_floats -> list[(minor_number, bid, box_index, buyer_player_id)]: return value of resolve_bids, passed to unsold_minor_exports / float_minors; never stored",
      "float_minors(state, pending=None) and unsold_minor_exports(state, items_with_bids=()) therefore take them as parameters (signature change relative to v1).", ["st.items_with_bids", "st.pending_minor_floats"], "GAPS A14/B-9")
reprn("json_safety", "JSON-safe state", "rooms.serialize_state does dataclasses.asdict + json.dumps with a default for dataclasses and Enums only",
      "After every function the state must contain only int/str/bool/None, lists, dicts with str keys (the tuple-keyed stock_stack is handled by rooms), tuples, dataclasses, Enums: NO sets, NO new attributes on dataclasses.", ["ent.game"], "BINDING T13")
reprn("module_constants", "Constants not in any data table", "FACE_VALUES, BID_MULTIPLE, MAX_BIDS_PER_TURN (bidding); TOTAL_UNITS, POOL_CAP_UNITS, HOLD_CAP_UNITS (certificates); TRAIN_PHASE, TRAIN_GROUPS, SCAN_ORDER (trains); trigger strings (scoring)",
      "Values from the data tables (cert limit, tokens, market, trains, phases) are read from app.data.* and never re-typed.", ["const.face_values", "const.bid_rules", "const.share_structure", "const.stack_setup", "const.box_counts"], "GAPS A16")
reprn("private_revenue_parse", "Private revenue strings", "app.data.private_companies.PRIVATE_COMPANIES_BY_NUMBER[n].revenue: '£5', '£10', '£0', '£10x phase', '£5x phase'",
      "private_revenue(n, phase): strip '£'; if it ends with 'x phase' multiply by phase.", ["const.private_revenue_table", "drv.private_revenue", "const.concession_dividend"], "v2")
reprn("kind_args", "Company kind arguments", "'major' | 'minor' strings in buy_train_from_bank(state, company_id, kind, code), place_start_token(..., kind) and start_cell(price, kind)",
      "Given callers pass 'minor' if company_id in state.minors else 'major'.", ["api.trains.buy_train_from_bank", "api.turn_order.place_start_token"], "BINDING A.0")
reprn("setup_given", "Given setup", "engine.setup.new_game(game_id, player_names, seed): fills cash, bank 9900, stacks (tops LNWR / M24 / P1), train pool, random order, boxes (via _refill_bid_boxes) and returns a state already inside round 1",
      "Do not rewrite; new modules must tolerate its defaults ({} / False / 0).", ["act.setup_game"], "BINDING A.6")

# ##################################################################################################
# ################################  DECISIONS: v1 gaps and new-scope choices  ######################
# ##################################################################################################
DEC = {}


def decision(id, topic, gap, sev, kind, choice, reason, resolves=(), needs_owner=False):
    nid = "decision." + id
    node(nid, "decision", topic, choice, gap=gap, severity=sev, kind=kind, choice=choice, reason=reason, needs_owner=needs_owner, resolves=list(resolves))
    DEC[nid] = list(resolves)


# ---- Section A.1 (graph vs given code)
decision("GA01", "Turn state machine vs actions.py", "A.1.1", "S1", "graph_fix",
         "Follow the skeleton: every successful sell / buy / convert / bid action ends the turn. turn.stage, turn.c_used, turn.acted and the errors ERR_WRONG_STAGE / ERR_C_ALREADY_USED / ERR_NO_ACTION_TAKEN are removed; the order edges sell->repay->C are removed; repay_loans stays as an unwired action (wired=false, implemented and exported); a new given action stock_turn_action models actions.py (calls ONE module function, increments bids_this_turn, resets pass_streak, calls end_turn).",
         "actions.py is given and its docstring says the combination is 'not wired up yet'; a literal v1 implementation would have vacuous preconditions.", ["act.stock_turn_action", "act.end_turn", "st.turn", "act.repay_loans", "act.sell_shares", "act.buy_share", "act.convert_concession"])
decision("GA02", "pass / end_turn preconditions (must_sell)", "A.1.2", "S1", "decision",
         "A pass is NOT blocked when must_sell is true (actions.py increments the pass counter before any module code runs); R10 is enforced only for buy_share, convert_concession and bids. end_turn/advance_stock_player and begin_turn have no must_sell check.",
         "Not enforceable inside the new modules without editing actions.py. Suggested owner change: reject 'pass' in actions._apply_pass when certificates.must_sell(state, player_id).", ["act.pass_turn", "act.end_turn", "ruling.R10"], True)
decision("GA03", "check_game_end_triggers signature and OR meaning", "A.1.3", "S2", "graph_fix",
         "check_game_end_triggers(state, context=None). The kind of a deferred trigger comes from round_type: STOCK -> 'next_or'; OPERATING -> token on game-end cell 'or_end', bank broken 'or_set_end'. context only matters for 'end_of_stock_round' (nothing-sold test). Maturity (setting game_over) is written by end_operating_round.",
         "All given callers pass one argument; models.py comments define the three stored values.", ["act.check_game_end_triggers", "act.end_operating_round", "api.scoring.check_game_end_triggers", "const.game_end_triggers"])
decision("GA04", "setup_game vs given new_game", "A.1.4", "S1", "graph_fix",
         "setup_game effects now match new_game: boxes are filled by setup and the state is already inside stock round 1 (round_type STOCK, active player = order[0], sr_completed 0). start_stock_round is for rounds >= 2 and debug.",
         "setup.py is given.", ["act.setup_game", "act.start_stock_round", "repr.setup_given", "repr.sr_start_player"])
decision("GA05", "sr_status has no field", "A.1.5", "S2", "graph_fix",
         "st.sr_status is dropped; st.round_type (STOCK/OPERATING) replaces it. start_stock_round raises only ERR_GAME_OVER, never 'already running'.",
         "main.py calls start_stock_round at arbitrary times.", ["st.round_type", "act.start_stock_round", "repr.round_type"])
decision("GA06", "bids_this_turn increment", "A.1.6", "S1", "graph_fix",
         "place_bid / move_bid do NOT write turn.bids_made; they read it (< 3). The caller (stock_turn_action = actions.py) increments it after each bid; begin_turn resets it.",
         "avoids double counting.", ["act.place_bid", "act.move_bid", "act.stock_turn_action", "repr.turn_record"])
decision("GA07", "sale_happened writers", "A.1.7", "S2", "graph_fix",
         "sell_shares, buy_share and convert_concession all set the flag themselves (idempotent); actions.py's extra write after buy/convert is documented as redundant; resolve_bids sets it when an item is won (R6b).",
         "makes direct calls of module functions consistent; R15.", ["st.sale_happened", "act.sell_shares", "act.buy_share", "act.convert_concession", "act.resolve_bids", "repr.sale_flag"])
decision("GA08", "Operating-round machinery", "A.1.8", "S2", "graph_fix",
         "In scope now: active_company_id, advance_company, start/begin/end of operating rounds, set size lock, game_over maturity, has_completed_or writer (advance_company), start-of-OR revenues. States or_set_size, or_index, or_order, or_current, round_type added; phase_events is an audit log only.",
         "required by actions.py/main.py; without a writer of has_operated no share could ever be sold.", ["act.advance_company", "act.start_operating_round", "act.begin_operating_round", "act.end_operating_round", "st.has_completed_or", "drv.active_company"])
decision("GA09", "buy_train_from_bank has no node", "A.1.9", "S1", "graph_fix",
         "New node act.buy_train (+ upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit) derived from rules 5.13.4-5.13.11, 2.1.x; no floated requirement; forced purchase and company-to-company sales deferred (rules 5.13.2/5.13.3 as deferred nodes).",
         "task goal 1.", ["act.buy_train", "act.upgrade_l_train", "act.rust_trains", "act.discard_excess_trains", "api.trains.buy_train_from_bank"])
decision("GA10", "Minor representation conflict", "A.1.10", "S2", "repr",
         "Minor director lives only in MinorCompanyState.director_player_id; no Player.shares entry; counts 1 certificate (graph). The models.py comment is ignored.",
         "graph and A6.", ["repr.minor_ownership"])
decision("GA11", "sold_this_round set vs JSON", "A.1.11", "S2", "repr", "Stored as dict[player_id, list[company_id]] without duplicates.", "rooms.serialize_state cannot encode sets.", ["repr.sold_this_round"])
decision("GA12", "Box numbering and item identity", "A.1.12", "S2", "repr", "0-based indices; item = (kind, box_index); BidBoxItem.ref is str for concessions, int otherwise.", "given models and actions (field box_index).", ["repr.boxes_zero_based", "repr.bid_box_item"])
decision("GA13", "ordinary_certs vs Player.shares", "A.1.13", "S2", "repr", "Player.shares stores units including the director's certificate; ordinary_certs is derived; a director swap changes no Player.shares value.", "T1.", ["repr.units_vs_certificates", "repr.director_certificate"])
decision("GA14", "Local-only states", "A.1.14", "S2", "graph_fix", "items_with_bids and pending_minor_floats are call-scoped states: returned by resolve_bids and passed as parameters (float_minors(state, pending=None), unsold_minor_exports(state, items_with_bids=())).", "no field exists; signatures changed vs v1.", ["st.items_with_bids", "st.pending_minor_floats", "repr.call_scoped"])
decision("GA15", "States without fields / fields without states", "A.1.15", "S2", "repr", "Every state node is bound by at least one repr node; fields without states are listed in repr.company_status (mirrors), repr.sr_counter (round_number untouched) and repr.sr_order (priority_deal_player_id).", "coverage rule enforced by check_graph.py.", ["repr.company_status", "repr.sr_counter", "repr.sr_order"])
decision("GA16", "Constants marked missing", "A.1.16", "S3", "graph_fix", "const nodes cert_limit, bidding_tokens, market_grid, yellow_cells, game_end_cells, start_cells, train_deck now carry source_in_code and missing=False; new consts for train costs, limits, ORs per SR, private revenue, concession dividend; module constants (face values, bid rules, share structure) listed as api constants.", "values exist in app.data.*.", ["const.cert_limit", "const.bidding_tokens", "const.market_grid", "const.phase_table", "const.train_costs", "repr.module_constants"])
decision("GA17", "Market adjacency confidence", "A.1.17", "S3", "carried", "R12 stands (down = row+1 same column; absent cell = no move). operating._move_price (given) moves along rows for dividends and is independent of the new market functions; consistency risk noted, not a graph change.", "no new evidence.", ["ruling.R12", "act.move_token_down", "act.move_token_up"])
# ---- A.2
decision("GA18", "place_bid / move_bid merged", "A.2.18", "S2", "graph_fix", "One api function place_or_move_bid implements both actions; branch = player already has a token on the item; ERR_ALREADY_HAS_TOKEN and ERR_NO_TOKEN_ON_ITEM are removed from the graph.", "given API.", ["act.place_bid", "act.move_bid", "api.bidding.place_or_move_bid"])
decision("GA19", "ERR_BAD_AMOUNT covers three checks", "A.2.19", "S2", "graph_fix", "Three codes: ERR_BAD_AMOUNT (not an int multiple of 5), ERR_BID_TOO_LOW, ERR_INSUFFICIENT_CASH; derived bid_amount_error returns the code, bid_amount_valid = (error is None).", "distinguishable errors.", ["drv.bid_amount_error", "drv.bid_amount_valid", "api.bidding.bid_amount_error"])
decision("GA20", "sale_legal returns one record", "A.2.20", "S2", "graph_fix", "SaleCheck gains a reason field (None | ERR_NOT_SELLABLE | ERR_POOL_FULL | ERR_TOO_MANY); sell_shares maps reasons to the three codes.", "exposes the failing clause.", ["drv.sale_legal", "api.certificates.SaleCheck", "api.shares.sell_shares"])
decision("GA21", "Error precedence", "A.2.21", "S3", "graph_fix", "Every api node lists its enforced preconditions in an ORDERED list (attrs.enforced, field n); the first failing check raises. Order = listed order; unknown ids first, then argument validity, then rule checks.", "mechanical contracts need a total order.", ["api.shares.buy_share", "api.shares.sell_shares", "api.bidding.place_or_move_bid", "api.company_formation.convert_concession"])
decision("GA22", "buy_share source default", "A.2.22", "S2", "graph_fix", "buy_share(..., source=None). Accepted strings: 'treasury', 'pool', 'bank' ('bank' and 'pool' both = bank pool). None: pool if the pool holds a share, else treasury, else ERR_NO_SHARE_AT_SOURCE.", "given actions pass None when absent; A12 left the choice to the buyer.", ["act.buy_share", "api.shares.buy_share", "repr.bank_pool_naming"], True)
decision("GA23", "repay_loans errors", "A.2.23", "S3", "graph_fix", "repay_loans(state, player_id, amount=None): None = min(loans, cash); ERR_NO_LOANS, ERR_BAD_AMOUNT (<=0, > loans, non-int), ERR_INSUFFICIENT_CASH; no caller (wired=false).", "completeness.", ["act.repay_loans", "api.shares.repay_loans"])
decision("GA24", "Several triggers in one call", "A.2.24", "S3", "decision", "Within one call the order is: existing trigger (stop) -> immediate nothing-sold -> token on game-end cell -> bank broken; the first that fires wins; they cannot actually coincide because the check runs after every action.", "10.1.2.", ["act.check_game_end_triggers"])
decision("GA25", "Check once per loop", "A.2.25", "S3", "decision", "float_minors, pay_concession_dividends and pay_private_revenues call check_game_end_triggers ONCE after all payments.", "the bank-broken latch is monotone within a call.", ["act.float_minors", "act.pay_concession_dividends", "act.pay_private_revenues"])
decision("GA26", "phase_check details", "A.2.26", "S2", "graph_fix", "(a) concession clearing only when old < 5 <= new; (b) rust events of every skipped phase old+1..new are applied; (c) the 2.1.2 deferral is handled by operating_rounds_for_next_set with phase_before; (d) phase_events is an audit log, rust/discard/limits are applied immediately.", "rules 2.1.2-2.1.5, 2.2.1.", ["act.phase_check", "drv.operating_rounds_for_next_set", "act.rust_trains", "act.discard_excess_trains", "st.phase_events"])
decision("GA27", "export_train deck convention", "A.2.27", "S2", "graph_fix", "Deck = counts per code; groups L/2 and 7/E are one pool each; a card leaves by decrementing the first non-zero code of the group; effective type for the phase check: '2' for L/2 cards, the code for others ('7' for 7/E).", "T12.", ["act.export_train", "st.train_deck", "const.train_deck", "repr.train_deck_counts"])
decision("GA28", "Minor token placement", "A.2.28", "S3", "graph_fix", "Minor tokens are inserted directly after the leading run of minor tokens in the pile.", "satisfies 'above every major, below existing minors' when minors lead the pile.", ["act.place_start_token"])
decision("GA29", "A26 upper row first", "A.2.29", "S3", "decision", "A26 is withdrawn: descending_order uses the given stock_positions.descending_price_key unchanged.", "the case cannot occur on the given grid.", ["drv.descending_order"])
decision("GA30", "sale_legal for non-majors", "A.2.30", "S3", "decision", "sale_legal for an unknown, minor or unstarted company returns SaleCheck(False, False, None, 'ERR_NOT_SELLABLE'); can_sell_any scans only floated majors.", "total function.", ["drv.sale_legal", "drv.can_sell_any"])
decision("GA31", "Acquired minors in the operating order", "A.2.31", "S2", "graph_fix", "operating_order excludes minors with acquired_by_major set and removed minors; acquisition itself is out of scope.", "field exists in the model.", ["drv.operating_order"])
decision("GA32", "convert_concession limit effect and dead end", "A.2.32", "S3", "carried", "No certificate-limit effect (concession 1 -> director certificate 1); leading bids ignored (A7). A major whose concession was not converted before phase 5 can never start (R9 + R11, A25).", "R9/R11 consequence.", ["act.convert_concession", "ruling.R9", "ruling.R11"], True)
decision("GA33", "R6 open conflict", "A.2.33", "S3", "graph_fix", "Ruling R6b adopted (provisional): nothing sold = no share bought/sold, no concession converted, no bid-box item won at resolution. resolve_bids sets sale_happened only for WON items; an item nobody can pay (R8) is not won.", "task owner.", ["ruling.R6b", "act.resolve_bids", "act.check_game_end_triggers"])
decision("GA34", "Carried assumptions A4, A5, A9, A10, A11, A13, A15, A16, A17, A21-A24, A26, A28", "A.2.34", "S3", "carried", "All remain as in GRAPH_NOTES v1 (copied into v2 notes). Owner-open and worth a ruling: A4 (opening bid 0), A5 (one token per item, leader cannot raise), A9 (batch sale priced before the drop), A15 (unpaid box-1 minor is still removed), A16 (payment order).", "no new evidence.", ["act.sell_shares", "act.resolve_bids", "act.place_bid"], True)
decision("GA35", "Concession dividends and private revenue", "A.2.35", "S3", "graph_fix", "pay_concession_dividends no-ops at phase >= 5; new pay_private_revenues (3.1.2) pays every open private from the bank: player owners via Player.private_companies, company owners via owner_company_id. P15/P20 treasury credit accrual and closing of privates are out of scope.", "task goal 1.", ["act.pay_concession_dividends", "act.pay_private_revenues", "drv.private_revenue"], True)
decision("GA36", "Final scoring and game_over", "A.2.36", "S3", "graph_fix", "game_over is set by check_game_end_triggers (immediate) and by end_operating_round (matured or_end / or_set_end / next_or); drv.final_ranking added (ties keep player order).", "10.1.x.", ["drv.final_ranking", "act.end_operating_round"], True)
decision("GA37", "sr_over precondition on resolve_stock_round", "A.2.37", "S3", "decision", "resolve_stock_round and end_stock_round do NOT check sr_over or round_type; the round manager (actions._apply_pass) decides when. No ERR_NOT_OVER exists.", "callable whenever the caller invokes it; avoids lazy cross-component import.", ["act.resolve_stock_round", "act.end_stock_round", "api.bidding.resolve_stock_round", "api.round_manager.end_stock_round"])
decision("GA38", "Exception types", "A.2.38", "S3", "decision", "ONE exception class per module derived directly from Exception, no shared base, no subclasses: ShareError, CertificateError, ConcessionError, BidError, MarketError, TrainError, ScoringError, RoundError. Message '<ERR_CODE>: <text>', attribute .code. Given code catches per module class; actions.py wraps str(e).", "layering (no module for a shared base) and the given except clauses.", ["api.shares.ShareError", "api.certificates.CertificateError", "api.company_formation.ConcessionError", "api.bidding.BidError", "api.turn_order.MarketError", "api.trains.TrainError", "api.scoring.ScoringError", "api.round_manager.RoundError"])
decision("GA39", "Treasury shares units", "A.2.39", "S3", "repr", "shares_in_treasury counts ORDINARY units only (8; LNWR 9); the director's certificate is never in it; the models comment 'director cert = 2' does not apply.", "operating._pay_major_dividend counts them as plain units.", ["repr.bank_pool_naming", "st.treasury_shares"])
decision("GA40", "priority_deal_player_id writer", "A.2.40", "S3", "repr", "Always equal to player_order[0]: set by setup, rewritten by reorder_players_by_cash, re-asserted by start_stock_round.", "single source of truth.", ["repr.sr_order", "act.reorder_players_by_cash"])
decision("GA41", "Arrow rules and given price movement", "A.2.41", "S3", "carried", "Arrows stay out of scope (R11). Given operating._move_price (rows, ignores arrows) and the new vertical moves are independent code paths; a consistency risk noted for the owner.", "given code.", ["ruling.R11"])
decision("GA42", "Round-number accounting", "A.2.42", "S3", "repr", "st.sr_completed = stock_rounds_completed (0 during round 1); round_number untouched by the engine.", "the model default is never described.", ["st.sr_completed", "repr.sr_counter"])
# ---- Section B
decision("GB01", "Player.shares stores units incl. director's certificate", "B-1", "S2", "repr", "Now an explicit repr node.", "T1.", ["repr.units_vs_certificates"])
decision("GB02", "sr_count binding", "B-2", "S3", "graph_fix", "State renamed st.sr_completed (rounds completed); incremented by end_stock_round after resolution.", "GA42.", ["st.sr_completed"])
decision("GB03", "repay_loans exported though unreachable", "B-3", "S3", "decision", "Kept; action marked wired=false.", "GA01.", ["act.repay_loans"])
decision("GB04", "sold_this_round values as lists", "B-4", "S3", "repr", "See GA11.", "JSON.", ["repr.sold_this_round"])
decision("GB05", "Mirrors without graph state", "B-5", "S3", "repr", "Documented in repr.concession, repr.private_company, repr.company_status; private_status is a new state.", "coverage.", ["repr.concession", "repr.private_company", "repr.company_status", "st.private_status"])
decision("GB06", "has_operated writer", "B-6", "S2", "graph_fix", "advance_company writes has_completed_or for a major (now a graph effect, state no longer external).", "GA08.", ["act.advance_company", "st.has_completed_or"])
decision("GB07", "removed_items", "B-7", "S3", "repr", "Minors: removed=True; concessions and privates: absent everywhere.", "no field.", ["st.removed_items", "repr.concession"])
decision("GB08", "phase_events representation", "B-8", "S3", "repr", "One audit line in state.log (repr.phase_log); no consumer needed.", "GA26.", ["st.phase_events", "repr.phase_log"])
decision("GB09", "Local states as return values", "B-9", "S2", "graph_fix", "See GA14.", "GA14.", ["st.items_with_bids"])
decision("GB10", "Train pool convention", "B-10", "S2", "graph_fix", "See GA27; const.train_deck now states the convention.", "T12.", ["const.train_deck"])
decision("GB11", "start_cell gains a kind parameter", "B-11", "S3", "graph_fix", "Derived start_cell(price, kind='major') in the graph itself.", "1.6.3.", ["drv.start_cell"])
decision("GB12", "place/move branch", "B-12", "S2", "graph_fix", "See GA18.", "GA18.", ["act.place_bid", "act.move_bid"])
decision("GB13", "buy_share source None default", "B-13", "S2", "graph_fix", "See GA22 (pool first).", "GA22.", ["act.buy_share"], True)
decision("GB14", "buy_train_from_bank interim behaviour", "B-14", "S1", "graph_fix", "Replaced by the rule-derived act.buy_train (order, limit before buying, E limit, face value, side choice, phase check); extra optional parameter source=None.", "GA09.", ["act.buy_train"])
decision("GB15", "Operating-round sequencing interim", "B-15", "S1", "graph_fix", "Now explicit actions start_operating_round / begin_operating_round / advance_company / end_operating_round with the 2.1.2 deferral via phase_before.", "GA08.", ["act.start_operating_round", "act.begin_operating_round", "act.end_operating_round"])
decision("GB16", "check_game_end_triggers optional context", "B-16", "S2", "graph_fix", "See GA03.", "GA03.", ["act.check_game_end_triggers"])
decision("GB17", "end_stock_round stops when game_over", "B-17", "S3", "graph_fix", "Now an effect line of act.end_stock_round.", "10.1.1.", ["act.end_stock_round"])
decision("GB18", "No ERR_SR_ALREADY_RUNNING", "B-18", "S3", "decision", "See GA05.", "GA05.", ["act.start_stock_round"])
decision("GB19", "Import layering", "B-19", "S3", "decision", "Layers: 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares + company_formation, 6 bidding, 7 round_manager; upward calls are lazy imports (api node attrs.layer; lazy edges: turn_order->scoring.check_game_end_triggers, turn_order->certificates.fully_sold, certificates->bidding.items_led, trains->bidding.clear_concession_boxes, bidding->nothing upward now that resolve_stock_round has no sr_over check).", "circular imports.", ["api.turn_order.move_token_up", "api.certificates.cert_count", "api.trains.phase_check"])
decision("GB20", "Message format", "B-20", "S3", "decision", "See GA38.", "GA38.", ["api.shares.ShareError"])
decision("GB21", "Game-end check once per loop", "B-21", "S3", "decision", "See GA25.", "GA25.", ["act.float_minors"])
decision("GB22", "Concession clearing trigger", "B-22", "S3", "graph_fix", "See GA26 (old < 5 <= new).", "GA26.", ["act.phase_check"])
decision("GB23", "advance_stock_player does not touch the pass counter", "B-23", "S3", "graph_fix", "Explicit in act.end_turn effects.", "GA01.", ["act.end_turn"])
decision("GB24", "Error precedence orders", "B-24", "S3", "graph_fix", "See GA21.", "GA21.", ["api.shares.buy_share"])
decision("GB25", "Minor token index", "B-25", "S3", "graph_fix", "See GA28.", "GA28.", ["act.place_start_token"])
# ---- new-scope decisions
decision("DN01", "Deferral of the second operating round (2.1.2)", "new", "S2", "decision", "The set after a stock round has ors_per_sr[phase_before] rounds, phase_before = phase at the start of that stock round's resolution (a local value of end_stock_round); next_or forces 1. A phase 2 that starts during resolution (export) therefore gives 1 OR after that stock round and 2 after the next; a phase 2 that starts in an operating round gives 2 after the next stock round. No new field is needed.", "'applies after the following stock round' (2.1.2, 5.1.1, 2.2.3).", ["drv.operating_rounds_for_next_set", "act.end_stock_round"])
decision("DN02", "Which train is discarded", "new", "S3", "decision", "Companies above the limit discard the lowest-face-value trains first, in descending share price order of companies. A director's real choice cannot be expressed through the skeleton actions.", "2.1.4/2.1.5 give the director the choice.", ["act.discard_excess_trains"], True)
decision("DN03", "Train purchase conventions", "new", "S2", "decision", "Buying from the bank takes the front group or a pool train; the code passed is the orientation; L may be bought while L/2 is the front group; L->2 upgrade allowed in phases 1-2 for 80 and counts as a purchase.", "5.13.4-5.13.10.", ["act.buy_train", "act.upgrade_l_train"])
decision("DN04", "buy_train has no floated / round / director precondition", "new", "S2", "decision", "buy_train_from_bank does not require the company to be floated and checks no round, active company or director (callers do).", "first_turn_housekeeping buys L trains for companies mid-setup; main.py debug.", ["api.trains.buy_train_from_bank"])
decision("DN05", "Forced train purchase and company-to-company sales", "new", "S3", "out_of_scope", "5.13.2 (must own a train, 5.14 forced purchase) and 5.13.3 (buy from another company) are deferred rule nodes; insufficient funds raise ERR_INSUFFICIENT_FUNDS.", "skeleton operate action has no such flow.", ["rule.5.13.2", "rule.5.13.3"], True)
decision("DN06", "Minors owning E-trains", "new", "S3", "out_of_scope", "A minor may own an E-train (5.13.11) but running it is out of scope.", "5.12/operating code.", ["rule.5.13.11"])
decision("DN07", "Bank-pool trains", "new", "S3", "decision", "Trains in bank_pool_trains can be bought from phase 3 on (2.2.4) at face value without a phase check.", "5.13.4.", ["act.buy_train", "st.bank_pool_trains"])
decision("DN08", "Company-owned privates and P15/P20", "new", "S3", "out_of_scope", "Privates owned by companies (owner_company_id) are paid to the company treasury; the P15/P20 treasury credit and closing at phase 7 are out of scope.", "3.1.2; R11-style deferral.", ["act.pay_private_revenues", "st.private_status"], True)
decision("DN09", "An operating round with no company", "new", "S3", "decision", "begin_operating_round still pays step A, then ends immediately; the set continues.", "5.2.1 step A applies at the start of EACH OR.", ["act.begin_operating_round"])
decision("DN10", "Atomicity", "new", "S2", "decision", "Every public function validates all preconditions before its first mutation; the given multi-bid loop in actions._apply_bid is not atomic and out of our control.", "state must not be corrupted by a rejected call.", ["api.bidding.place_or_move_bid"])
decision("DN11", "Component to module mapping", "new", "S3", "decision", "comp.market -> turn_order; comp.certificates -> certificates; comp.share_trading -> shares + company_formation (convert_concession); comp.bidding and comp.bid_boxes -> bidding; comp.phase_trains -> trains; comp.sr_flow -> round_manager + scoring (+ given setup/actions); comp.sr_resolution -> bidding (resolve_*), company_formation (float_minors, minor_*), shares (charge_interest), turn_order (raise_sold_out_prices, reorder_players_by_cash).", "8 components, 8 modules; each api names its module.", ["comp.sr_flow", "comp.sr_resolution"])
decision("DN12", "Order of start-of-OR revenues", "new", "S3", "decision", "Privates pay before concessions (both step A); the order is irrelevant for money, only the bank-broken latch could differ.", "5.2.1 A.", ["act.begin_operating_round"])
decision("DN13", "Unpaid winner and the sale flag", "new", "S2", "decision", "An item that nobody can pay for (R8) stays in its box, counts as having had a bid for exports (A15) but is NOT won, so it does not set sale_happened (R6b).", "R6b wording 'won'.", ["ruling.R6b", "act.resolve_bids"], True)
decision("DN14", "Unsold minor exports are not sales", "new", "S3", "decision", "Train exports at resolution never set sale_happened (A17 kept).", "else the first-round rule could never fire.", ["act.unsold_minor_exports", "act.export_train"])
decision("DN15", "Game state after game_over", "new", "S3", "decision", "After game_over actions.apply_action refuses all actions; round managers raise ERR_GAME_OVER in start_stock_round / start_operating_round / end_stock_round.", "10.1.2.", ["act.apply_action", "act.start_stock_round"])


# ---------------------------------------------------------------- order edges
ORDER = {
    "resolve": ["resolve_bids", "float_minors", "unsold_minor_exports", "remove_box1_minor_and_export", "refill_boxes", "charge_interest", "raise_sold_out_prices", "reorder_players_by_cash", "check_game_end_triggers"],
    "end_sr": ["resolve_stock_round", "start_operating_round"],
    "phase": ["rust_trains", "discard_excess_trains", "clear_concession_boxes"],
    "or_start": ["pay_private_revenues", "pay_concession_dividends"],
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
        edge("act." + seq_names[i], "act." + seq_names[i + 1], "order", "%s: seq %d runs before seq %d" % (k, i + 1, i + 2), seq=i + 1)

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
edge("ruling.R6b", "ruling.R6", "supersedes", "R6b replaces the provisional tail of R6 (precise meaning of 'nothing sold')")

# ---------------------------------------------------------------- v2 edges: implements / binds / resolves
for aid, a in API.items():
    for t in a["implements"]:
        assert t in N, (aid, t)
        edge(aid, t, "implements", "")
for rid_, targets in REPRS.items():
    for t in targets:
        assert t in N, (rid_, t)
        edge(rid_, t, "binds", "")
for did, targets in DEC.items():
    for t in targets:
        assert t in N, (did, t)
        edge(did, t, "resolves", "")

# api callers (given callers + callers derived from graph call/trigger edges) and raised_by
api_of = collections.defaultdict(list)
for aid, a in API.items():
    for t in a["implements"]:
        api_of[t].append("%s.%s" % (a["module"], a["name"]))
for e in E:
    if e["type"] in ("calls", "triggers"):
        for dst_api in api_of.get(e["dst"], []):
            for aid, a in API.items():
                if "%s.%s" % (a["module"], a["name"]) == dst_api and e["dst"] in a["implements"]:
                    srcs = api_of.get(e["src"], [])  # callers from GIVEN code are listed explicitly in given_callers
                    for s_ in srcs:
                        if s_ != dst_api:
                            a.setdefault("graph_callers", set()).add(s_)
for aid, a in API.items():
    a["graph_callers"] = sorted(a.get("graph_callers", []))
    a["callers"] = sorted(set(a["given_callers"]) | set(a["graph_callers"]))
    N[aid]["attrs"]["graph_callers"] = a["graph_callers"]
    N[aid]["attrs"]["callers"] = a["callers"]
    N[aid]["attrs"]["implements"] = a["implements"]
for aid, a in API.items():
    if a["kind"] == "exception":
        cls = a["name"]
        N[aid]["attrs"]["raised_by"] = sorted("%s.%s" % (b["module"], b["name"]) for b in API.values() if any(r["class"] == cls for r in b["raises"]))

# ---------------------------------------------------------------- annotate states with accessor components
acc = collections.defaultdict(lambda: {"readers": set(), "writers": set()})
for e in E:
    if e["type"] in ("reads", "writes") and e["dst"].startswith("st."):
        acc[e["dst"]]["readers" if e["type"] == "reads" else "writers"].add(comp_of[e["src"]])
for sid in STATE_OWNER:
    a = acc[sid]
    N[sid]["attrs"]["reader_components"] = sorted(a["readers"])
    N[sid]["attrs"]["writer_components"] = sorted(a["writers"])
    N[sid]["attrs"]["shared"] = len(a["readers"] | a["writers"] | {STATE_OWNER[sid]}) > 1

OUT = os.path.dirname(os.path.abspath(__file__))
out = {"nodes": list(N.values()), "edges": E}
json.dump(out, open(os.path.join(OUT, "graph.json"), "w"), indent=1, ensure_ascii=False)
cnt = collections.Counter(n["type"] for n in N.values())
ecnt = collections.Counter(e["type"] for e in E)
print("nodes", dict(cnt), sum(cnt.values()))
print("edges", dict(ecnt), sum(ecnt.values()))

# ---------------------------------------------------------------- GAP_RESOLUTION.md
def _gap_md():
    L = ["# GAP_RESOLUTION - how graph v2 closes the gaps of GAPS.md (sections A and B) and what is new", "",
         "Generated by build_graph.py from the `decision` nodes. Kinds: graph_fix = the graph nodes were changed; repr = a `repr` node fixes the mapping to the model; decision = a choice recorded without graph change; carried = unchanged v1 assumption; out_of_scope = deferred.",
         "`needs_owner` = a conservative default was chosen but the rules owner should rule.", ""]
    owners = [d for d in N.values() if d["type"] == "decision" and d["attrs"]["needs_owner"]]
    L.append("## needs_owner (%d)" % len(owners))
    for d in owners:
        L.append("- **%s** (%s): %s" % (d["id"].split(".")[1], d["attrs"]["gap"], d["label"]))
    L.append("")
    sections = [("A.1 Conflicts between graph and given code", lambda g: g.startswith("A.1.")), ("A.2 Missing or ambiguous behaviour", lambda g: g.startswith("A.2.")),
                ("B What BINDING had to guess", lambda g: g.startswith("B-")), ("New-scope decisions (this task)", lambda g: g == "new")]
    for title, pred in sections:
        L += ["## " + title, "", "| id | gap | sev | kind | topic | resolution | owner? | nodes |", "|---|---|---|---|---|---|---|---|"]
        for d in N.values():
            if d["type"] == "decision" and pred(d["attrs"]["gap"]):
                a = d["attrs"]
                L.append("| %s | %s | %s | %s | %s | %s (%s) | %s | %s |" % (d["id"].split(".")[1], a["gap"], a["severity"], a["kind"], d["label"].replace("|", "/"), a["choice"].replace("|", "/"), a["reason"].replace("|", "/"),
                                                                       "needs_owner" if a["needs_owner"] else "", ", ".join(a["resolves"][:6]) + (" ..." if len(a["resolves"]) > 6 else "")))
        L.append("")
    L += ["## Section C (three most serious gaps)", "",
          "1. Operating-round / phase / train side outside the graph: closed by new scope (GA08, GA09, GB14, GB15).",
          "2. Turn model contradicting actions.py: closed by following the skeleton (GA01, GA02, GA06, GA07).",
          "3. State-to-model mismatches: closed by the `repr` layer (GA10-GA15, GB01-GB08) and the `api` layer.", "",
          "## Not closed", "",
          "- A2/GA02: must_sell cannot block a pass (needs a change in given actions.py).",
          "- R11 deferrals stay deferred (P16, P9, 4.8 direct formation from phase 5, arrows); consequence GA32 (a major whose concession is unconverted at phase 5 can never start).",
          "- Forced train purchase (5.13.2/5.14), company-to-company train sales (5.13.3), P15/P20 credit and privates closing, dividends 5.12 (given code): out of scope by the task."]
    return "\n".join(L) + "\n"


open(os.path.join(OUT, "GAP_RESOLUTION.md"), "w").write(_gap_md())
json.dump({"nodes": dict(cnt), "edges": dict(ecnt), "api_by_module": {m: [("%s%s" % (a["name"], "" if a["kind"] != "function" else "")) for a in API.values() if a["module"] == m] for m in MODULES}},
          open(os.path.join(OUT, "stats.json"), "w"), indent=1)


# ---------------------------------------------------------------- GRAPH_NOTES.md
def _notes_md():
    cnt_ = collections.Counter(n["type"] for n in N.values())
    ecnt_ = collections.Counter(e["type"] for e in E)
    L = []
    L.append("# GRAPH_NOTES v2 - 1822 stock round + trains/phases + round flow, with interface (api), representation (repr) and decision layers")
    L.append("")
    L.append("Files: `graph.json` (complete graph, not a diff), `build_graph.py` (generator; all data lives in it; also writes GAP_RESOLUTION.md and stats.json), `check_graph.py` (verifier, `python3 check_graph.py [graph.json] [given_code_dir]`, exit 1 on violations), `GAP_RESOLUTION.md` (every v1 gap with its resolution).")
    L.append("Inputs read: graph v1 (graph.json, notes, builder, checker), RULES.md, RULINGS.md, RULES_v3.md, the v1 contracts/BINDING.md/GAPS.md, and the given code (models, data tables, setup, actions, operating, stock_positions, main, rooms, db). The eight module files that exist in the skeleton directory were NOT read.")
    L.append("")
    L.append("## 1. Schema (v1 + v2)")
    L.append("- v1 node types: rule, ruling, entity, state, action, derived, component, constant (see v1 notes; attrs unchanged). New node ids: `api.<module>.<name>`, `repr.<name>`, `decision.<GA|GB|DN><nn>`, `ruling.R6b`.")
    L.append("- `api` (one per public function, per exception class, per shared constant of the 8 modules): attrs module, name, kind (function|exception|class|constant), signature (python text WITH defaults, syntax-checked), params, defaults (explicit dict), returns, raises [{class, code, when}], enforced [{n, check, code}] (ORDERED: the first failing check raises = error precedence), not_enforced [text] (what the function must NOT check), given_callers, graph_callers (derived from calls/triggers edges), callers (union), aliases (the module must export every alias), given_name (name fixed by given code), layer (import layering), implements (ids), notes.")
    L.append("- `repr` (where a concept lives in the given data model): concept, maps_to, rule_for_coder, binds [ids], source. Every `state` node is bound by at least one repr node (checked).")
    L.append("- `decision` (resolution of a v1 gap or a new-scope choice): gap id, severity, kind (graph_fix | repr | decision | carried | out_of_scope), choice, reason, needs_owner, resolves [ids].")
    L.append("- New edge types: `implements` (api -> action/derived/state), `binds` (repr -> any), `resolves` (decision -> any), `supersedes` (ruling R6b -> ruling R6).")
    L.append("- Given-code actions have no api: `act.setup_game`, `act.apply_action`, `act.stock_turn_action`, `act.pass_turn`, `act.operate_company` carry `implementation=given` and a `given_symbol` that the checker verifies in the given files.")
    L.append("")
    L.append("## 2. Counts (generated)")
    L.append("Nodes: " + ", ".join("%s %d" % (k, v) for k, v in sorted(cnt_.items())) + ", TOTAL %d" % sum(cnt_.values()))
    L.append("Edges: " + ", ".join("%s %d" % (k, v) for k, v in sorted(ecnt_.items())) + ", TOTAL %d" % sum(ecnt_.values()))
    L.append("")
    L.append("## 3. Turn model: the graph follows the skeleton (decision GA01)")
    L.append("actions.py ends the turn after EVERY successful sell_shares / buy_share / convert_concession / bid action. v2 therefore has NO turn stage, no c_used, no acted; the graph node `act.stock_turn_action` (given) models the wrapper: one module call, `bids_this_turn += 1` per bid (by the wrapper, never by bidding), `pass_streak = 0`, then `end_turn` (= advance_stock_player). `act.pass_turn` (given): `pass_streak += 1`, then `end_stock_round` if `sr_over` else `end_turn`. `repay_loans` exists (wired=false). A pass cannot be blocked by must_sell (GA02, needs_owner).")
    L.append("")
    L.append("## 4. Round flow")
    L.append("- Stock round 1 is pre-started by setup (round_type STOCK, active player = player_order[0]). `start_stock_round` serves rounds >= 2 and debug: refill boxes, STOCK, reset flags, priority player := order[0], begin_turn.")
    L.append("- Who acts: `turn.active_player`; next = player_order[(i+1) % n]. Turn ends after any turn-ending action or a non-final pass. Round ends when `consecutive_passes >= n` -> `end_stock_round`: phase_before := phase; `resolve_stock_round` (1 resolve_bids, 2 float_minors, 3 unsold_minor_exports, 4 remove_box1_minor_and_export, 5 refill_boxes, 6 charge_interest, 7 raise_sold_out_prices, 8 reorder_players_by_cash, 9 check_game_end_triggers('end_of_stock_round')); `sr_completed += 1`; stop if game_over; else `start_operating_round(phase_before)`.")
    L.append("- Operating-round set: size = ors_per_sr[phase_before] (locked; 1 if trigger next_or; the second OR starts only after the following stock round, 2.1.2). Each OR: step A `pay_private_revenues` then `pay_concession_dividends` (5.2.1 A, 3.1.2, 3.4.4), then the next company is chosen one at a time by `next_operating_company` (minors, then majors, descending share price; recomputed after each company, 5.2.2). `advance_company` marks a major `has_operated`. When nobody is left: `end_operating_round`: matured trigger -> game_over; next OR of the set; else `start_stock_round`.")
    L.append("- Game end (10.1.x): immediate (first SR nothing sold, R6b) sets game_over in step 9; token on a game-end cell: STOCK -> `next_or`, OPERATING -> `or_end`; bank broken: STOCK -> `next_or`, OPERATING -> `or_set_end`; first trigger stands (10.1.2); `next_or` becomes `or_set_end` with set size 1 when the next set starts; `end_operating_round` sets game_over. `final_ranking` implements 10.1.3.")
    L.append("- R6b (provisional ruling, node `ruling.R6b`): 'nothing sold in the first stock round' = no share bought or sold, no concession converted, and no bid-box item WON at resolution. An item nobody can pay for (R8) is not won.")
    L.append("")
    L.append("## 5. Trains and phases")
    L.append("Deck = counts per code (L/2 and 7/E are one physical pool each); buying from the bank must follow the front group (5.13.4), face value, train limit checked BEFORE buying (5.13.6/7), at most one E (5.13.11), orientation = the code passed (5.13.8/5.13.10), L->2 upgrade 80 in phases 1-2 (5.13.9), pool trains from phase 3. `phase_check` applies at once: phase, rust of every skipped phase, discard of excess trains (descending share price order, lowest face value first - needs_owner), concession clearing when old < 5 <= new. No floated requirement on purchases. Forced purchase (5.13.2) and company-to-company sales (5.13.3) are deferred rule nodes.")
    L.append("")
    L.append("## 6. Interface policy")
    L.append("- Names: every name given code imports or calls is kept exactly (given_name=True): ShareError, buy_share, sell_shares, ConcessionError, convert_concession, BidError, place_or_move_bid, resolve_stock_round, TrainError, buy_train_from_bank, check_game_end_triggers, active_company_id, advance_company, advance_stock_player, end_stock_round, start_stock_round. Other names are the v1 BINDING names; v2 additions: begin_operating_round, end_operating_round, pay_private_revenues, private_revenue, final_ranking, upgrade_l_train, rust_trains, discard_excess_trains, front_group, deck_remaining, train_group, train_cost, train_limit, bid_amount_error, operating_rounds_for_next_set. Aliases are listed per api (attrs.aliases) and must be exported.")
    L.append("- Exceptions (GA38): one class per module, derived directly from Exception, message `<ERR_CODE>: <text>`, attribute `.code`: " + ", ".join("%s.%s" % (m, EXC_OF[m]) for m in MODULES) + ".")
    L.append("- Atomicity (DN10): validate everything before the first mutation. Preconditions NOT enforced on purpose: resolve_stock_round and end_stock_round do not check sr_over or round type (GA37); buy_train_from_bank does not require a floated company (DN04); module functions do not check round type / active player (actions.py does); start_stock_round has no 'already running' check (GA05).")
    L.append("- Import layering: " + ", ".join("%d %s" % (LAYER[m], m) for m in sorted(MODULES, key=lambda x: LAYER[x])) + "; upward calls are lazy imports.")
    L.append("- Component -> module mapping: decision DN11.")
    L.append("")
    L.append("## 7. Public API per module (generated; functions, classes, constants)")
    for m in MODULES:
        L.append("")
        L.append("### %s (layer %d)" % (m, LAYER[m]))
        for a in API.values():
            if a["module"] == m:
                L.append("- `%s`%s%s" % (a["signature"], "  [given name]" if a["given_name"] else "", ("  aliases: " + ", ".join(a["aliases"])) if a["aliases"] else ""))
    L.append("")
    L.append("## 8. Rules not modelled")
    L.append("- 5.12.x (dividends, price movement of operating): given code operating.py. 5.13.1 is an index fragment. 2.2.7 is empty in the excerpt. 5.13.2 (forced purchase) and 5.13.3 (company-to-company) are deferred nodes. 5.3.1 is modelled only for who decides and step H (buy trains). Private powers and closing (3.1.1, 3.1.7-3.1.10), P15/P20 credit: out of scope. All v1 skips (1.7.x physical set-up, 3.2.x/3.3.x operating details, 4.9.2-4.9.4) stay skipped; 4.8.x/4.6.4 stay deferred (R11).")
    L.append("")
    L.append("## 9. Carried v1 assumptions")
    L.append("Assumptions A1-A40 of the v1 notes remain valid unless a decision in GAP_RESOLUTION.md overrides them: A1 (missing data) is closed by the given data tables; A13 (pass definition) is replaced by the skeleton turn model; A6/A7/A9-A11/A14-A17/A21-A24/A26/A28-A30 are unchanged; A18 (phase effects belong to the operating-round module) is now in scope; A29/A30 are refined by the OR-maturity actions.")
    L.append("")
    L.append("## 10. needs_owner")
    for d in N.values():
        if d["type"] == "decision" and d["attrs"]["needs_owner"]:
            L.append("- %s (%s): %s" % (d["id"].split(".")[1], d["attrs"]["gap"], d["label"]))
    L.append("")
    L.append("## 11. Checker result")
    L.append("`python3 check_graph.py` -> see the end of this run (0 violations required); warnings: entities without states (lnwr, stock_market, stock_token), intentional.")
    return "\n".join(L) + "\n"


open(os.path.join(OUT, "GRAPH_NOTES.md"), "w").write(_notes_md())
