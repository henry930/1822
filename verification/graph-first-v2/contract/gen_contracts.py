#!/usr/bin/env python3
"""Mechanical contract generator: graph.json (v2) -> contract/<module>.md, COMMON.md, BINDING.md.

Usage: python3 gen_contracts.py [graph.json] [out_dir]
Writes a UNRENDERED.txt report listing anything it could not render.
"""
import json, sys, os, collections, re

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/graphrun2/graph.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else HERE
MODULES = ["shares", "certificates", "company_formation", "bidding", "turn_order", "trains", "scoring", "round_manager"]

g = json.load(open(GRAPH))
N = {n["id"]: n for n in g["nodes"]}
E = g["edges"]
problems = []

out_e = collections.defaultdict(list)
in_e = collections.defaultdict(list)
for e in E:
    out_e[(e["src"], e["type"])].append(e)
    in_e[(e["dst"], e["type"])].append(e)

impl_nodes = collections.defaultdict(list)   # api id -> [node ids]
api_of = collections.defaultdict(list)        # node id -> [api ids]
for e in E:
    if e["type"] == "implements":
        impl_nodes[e["src"]].append(e["dst"])
        api_of[e["dst"]].append(e["src"])

APIS = [n for n in g["nodes"] if n["type"] == "api"]
by_mod = collections.defaultdict(list)
for a in APIS:
    by_mod[a["attrs"]["module"]].append(a)

def mod_of_node(nid):
    """module(s) that implement a node (by api implements edges)."""
    return sorted({N[a]["attrs"]["module"] for a in api_of.get(nid, [])})

def api_names(nid):
    return [N[a]["attrs"]["module"] + "." + N[a]["attrs"]["name"] for a in api_of.get(nid, [])]

def nodelabel(nid):
    n = N[nid]
    return "%s (%s)" % (nid, n["label"])

def rule_ref(rid):
    """rule id like 4.4.2 / R5 -> 'id: summary'."""
    for pre in ("rule.", "ruling."):
        if pre + rid in N:
            n = N[pre + rid]
            return "%s: %s" % (rid, n["attrs"].get("summary", n["label"]))
    return rid

def rid_of(nid):
    return N[nid]["text"]

def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ")

def render_attr_value(v):
    if isinstance(v, (dict, list)):
        return "`" + json.dumps(v, ensure_ascii=False) + "`"
    return str(v)

def bullets(lines, ind=""):
    return "".join("%s- %s\n" % (ind, l) for l in lines)

# ---------------------------------------------------------------- repr / decisions lookups
repr_binds = collections.defaultdict(list)  # node id -> repr ids
for e in E:
    if e["type"] == "binds":
        repr_binds[e["dst"]].append(e["src"])
for n in N.values():
    if n["type"] == "repr":
        for b in n["attrs"].get("binds", []):
            if n["id"] not in repr_binds[b]:
                repr_binds[b].append(n["id"])
dec_res = collections.defaultdict(list)
for e in E:
    if e["type"] == "resolves":
        if e["src"] not in dec_res[e["dst"]]:
            dec_res[e["dst"]].append(e["src"])
for n in N.values():
    if n["type"] == "decision":
        for b in n["attrs"].get("resolves", []):
            if n["id"] not in dec_res[b]:
                dec_res[b].append(n["id"])

def render_decision(did, ind=""):
    d = N[did]
    a = d["attrs"]
    flag = "  **[INTERIM, follow as written - needs_owner: the rules owner has not ruled yet]**" if a.get("needs_owner") else ""
    s = "%s- **%s** (gap %s, severity %s, kind %s): %s%s\n" % (ind, did.split(".", 1)[1], a.get("gap"), a.get("severity"), a.get("kind"), a.get("choice"), flag)
    if a.get("reason"):
        s += "%s  reason: %s\n" % (ind, a["reason"])
    return s

def render_repr(rid, ind=""):
    r = N[rid]
    a = r["attrs"]
    s = "%s- **%s** [%s]: maps to: %s\n" % (ind, a.get("concept"), rid, a.get("maps_to"))
    s += "%s  rule for coder: %s\n" % (ind, a.get("rule_for_coder"))
    return s

# ---------------------------------------------------------------- node rendering
def render_node(nid, modname):
    n = N[nid]
    t = n["type"]
    a = n["attrs"]
    s = "#### Graph node `%s` (%s) - %s\n" % (nid, t, n["label"])
    s += "%s\n\n" % n["text"]
    sig = a.get("signature")
    if isinstance(sig, dict):
        s += "- graph signature (abstract): params = %s; returns = %s\n" % (sig.get("params"), sig.get("returns"))
    if a.get("wired") is False:
        s += "- wired = false: exported and implemented, but no given code calls it\n"
    # preconditions
    if t == "action":
        pre = a.get("preconditions", [])
        s += "\n**Preconditions** (rule id in brackets; the ORDER that decides which error is raised first is the api `enforced` list above):\n"
        if not pre:
            s += "- (none)\n"
        for p in pre:
            if isinstance(p, dict):
                rr = p.get("rule")
                s += "- [%s] %s\n" % (rr, p.get("check"))
                if rr and rr not in ("", None):
                    for r1 in re.split(r"[,; ]+", str(rr)):
                        if r1 and (("rule." + r1) in N or ("ruling." + r1) in N):
                            pass
            else:
                s += "- %s\n" % p
        s += "\n**Effects, in order** (execute exactly in this order):\n"
        for i, ef in enumerate(a.get("effects", []), 1):
            s += "%d. %s\n" % (i, ef)
        if not a.get("effects"):
            s += "(none)\n"
        s += "\n**Errors listed by the graph node**:\n"
        for er in a.get("errors", []):
            s += "- %s\n" % er
        if not a.get("errors"):
            s += "- (none)\n"
    elif t == "derived":
        s += "\n**Formula**: %s\n" % a.get("formula")
    if a.get("notes"):
        s += "\n**Node notes**: %s\n" % a["notes"]
    # order edges
    ords = []
    for e in out_e[(nid, "order")]:
        ords.append("`%s` runs before `%s` (seq %s; %s)" % (nid, e["dst"], e.get("seq"), e.get("note", "")))
    for e in in_e[(nid, "order")]:
        ords.append("`%s` runs before `%s` (seq %s; %s)" % (e["src"], nid, e.get("seq"), e.get("note", "")))
    if ords:
        s += "\n**Order edges**:\n" + bullets(ords)
    # calls
    calls = []
    for et in ("calls", "triggers"):
        for e in out_e[(nid, et)]:
            d = e["dst"]
            ap = api_names(d)
            if ap:
                desc = ", ".join("`%s`" % x for x in ap)
                sigs = "; ".join("`%s`" % N[x]["attrs"]["signature"] for x in api_of[d])
                cross = "CROSS-MODULE" if any(N[x]["attrs"]["module"] != modname for x in api_of[d]) else "same module"
                calls.append("%s %s -> %s [%s] signature: %s %s" % (et, d, desc, cross, sigs, ("(" + e["note"] + ")") if e.get("note") else ""))
            elif N[d]["attrs"].get("implementation") == "given":
                calls.append("%s %s -> GIVEN code (%s)" % (et, d, N[d]["attrs"].get("given_symbol")))
            else:
                calls.append("%s %s -> (no api node)" % (et, d))
                problems.append("call target without api: %s -> %s" % (nid, d))
    if calls:
        s += "\n**Calls it must make / may trigger** (callee api in brackets):\n" + bullets(calls)
    # states
    rd = [e["dst"] for e in out_e[(nid, "reads")]]
    wr = [e["dst"] for e in out_e[(nid, "writes")]]
    if rd or wr:
        s += "\n**State touched**:\n"
        for lbl, lst in (("reads", rd), ("writes", wr)):
            for st in lst:
                sn = N[st]
                s += "- %s `%s` (%s): %s [type %s; unit %s; scope %s]\n" % (lbl, st, sn["label"], sn["text"], sn["attrs"].get("type"), sn["attrs"].get("unit"), sn["attrs"].get("scope"))
    # constants
    uc = [e["dst"] for e in out_e[(nid, "uses_constant")]]
    if uc:
        s += "\n**Constants used**:\n"
        for c in uc:
            cn = N[c]
            s += "- `%s` (%s): %s; data: %s\n" % (c, cn["label"], cn["text"], render_attr_value({k: v for k, v in cn["attrs"].items() if k not in ("source", "source_in_code", "missing")}))
            if cn["attrs"].get("source_in_code"):
                s += "  (in code: %s)\n" % cn["attrs"]["source_in_code"]
    # rules constraining
    rs = []
    for e in in_e[(nid, "constrains")]:
        r = e["src"]
        rs.append("%s%s" % (rule_ref(rid_of(r)), (" [" + e["note"] + "]") if e.get("note") else ""))
    if rs:
        s += "\n**Rules constraining this node**:\n" + bullets(rs)
    # repr
    rp = []
    for st in rd + wr:
        for r in repr_binds.get(st, []):
            if r not in rp:
                rp.append(r)
    for r in repr_binds.get(nid, []):
        if r not in rp:
            rp.append(r)
    if rp:
        s += "\n**Representation notes (repr nodes bound to touched states / this node)**:\n"
        for r in rp:
            s += render_repr(r)
    # decisions
    ds = []
    for x in [nid] + rd + wr:
        for d in dec_res.get(x, []):
            if d not in ds:
                ds.append(d)
    return s, ds

def render_api(a, modname, ctx):
    at = a["attrs"]
    nid = a["id"]
    s = "### `%s.%s` (%s)\n\n" % (modname, at["name"], at["kind"])
    s += "```python\n%s\n```\n\n" % at["signature"]
    if at["kind"] == "constant":
        s += "- value: `%s`\n" % json.dumps(at.get("value"), ensure_ascii=False)
    if at["kind"] == "class" and at.get("fields"):
        s += "- fields (in this order): %s\n" % ", ".join("`%s`" % f for f in at["fields"])
    if at["kind"] == "exception":
        s += "- bases: %s; message `<ERR_CODE>: <text>`; attribute `.code` = ERR_CODE\n" % at.get("bases")
        if at.get("raised_by"):
            s += "- raised by: %s\n" % ", ".join(at["raised_by"])
    s += "- parameters: %s\n" % (at["params"] if at["params"] else "(none)")
    s += "- defaults (explicit): %s\n" % (json.dumps(at["defaults"]) if at["defaults"] else "(none)")
    s += "- returns: %s\n" % (at["returns"] or "(see signature)")
    s += "- layer: %s\n" % at["layer"]
    s += "- given name (fixed by given code, never rename): %s\n" % ("YES" if at["given_name"] else "no")
    if at["aliases"]:
        s += "- **aliases that MUST also be exported** (same object / same behaviour): %s\n" % ", ".join("`%s`" % x for x in at["aliases"])
    else:
        s += "- aliases: none\n"
    s += "- callers in given code: %s\n" % (", ".join(at["given_callers"]) or "none")
    s += "- callers from graph (calls/triggers): %s\n" % (", ".join(at["graph_callers"]) or "none")
    if at["notes"]:
        s += "- api notes: %s\n" % at["notes"]
    if at["raises"]:
        s += "\n**Exceptions**:\n\n| class | code | when |\n|---|---|---|\n"
        for r in at["raises"]:
            s += "| %s | %s | %s |\n" % (r["class"], r["code"], md_escape(r["when"]))
    elif at["kind"] == "function":
        s += "\n**Exceptions**: none raised.\n"
    if at["enforced"]:
        s += "\n**Enforced checks, in precedence order (first failing check raises its code; validate EVERYTHING before the first mutation - atomicity, DN10)**:\n\n"
        for en in at["enforced"]:
            s += "%s. %s -> `%s`\n" % (en["n"], en["check"], en["code"])
    if at["not_enforced"]:
        s += "\n**Must NOT be checked by this function**:\n" + bullets(at["not_enforced"])
    impls = impl_nodes.get(nid, [])
    decs_all = []
    if impls:
        s += "\n**Implements graph node(s)**: %s\n\n" % ", ".join("`%s`" % x for x in impls)
        for x in impls:
            body, ds = render_node(x, modname)
            s += body + "\n"
            for d in ds:
                if d not in decs_all:
                    decs_all.append(d)
    ds2 = [d for d in dec_res.get(nid, []) if d not in decs_all]
    decs_all += ds2
    if decs_all:
        s += "\n**Related decisions** (a decision marked INTERIM is the conservative default pending an owner ruling: follow it as written):\n"
        for d in decs_all:
            s += render_decision(d)
    s += "\n"
    return s

# ---------------------------------------------------------------- module rules / flags / hooks
def module_nodes(mod):
    ns = []
    for a in by_mod[mod]:
        for x in impl_nodes.get(a["id"], []):
            if x not in ns:
                ns.append(x)
    return ns

def module_contract(mod):
    apis = by_mod[mod]
    nodes_ = module_nodes(mod)
    s = "# Contract: `backend/app/engine/%s.py`\n\n" % mod
    s += "Generated mechanically from graph v2 by gen_contracts.py. Read COMMON.md first, then this file; BINDING.md lists the representation rules and the cross-module call matrix.\n\n"
    layer = apis[0]["attrs"]["layer"] if apis else "?"
    s += "Import layering: this module is layer %s (1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares and company_formation, 6 bidding, 7 round_manager). Calls to a HIGHER layer must be lazy imports inside the function body; never import upward at module level.\n\n" % layer
    # export list
    s += "## 1. Export list (every name below, plus every alias, must exist at module level)\n\n"
    exp = []
    for a in apis:
        at = a["attrs"]
        exp.append("`%s` (%s)%s" % (at["name"], at["kind"], "  aliases: " + ", ".join(at["aliases"]) if at["aliases"] else ""))
    s += bullets(exp) + "\n"
    s += "Public API count: %d\n\n" % len(apis)
    # module-level obligations
    s += "## 2. Module-level obligations\n\n"
    wr = collections.OrderedDict()
    hooks = []
    for x in nodes_:
        for e in out_e[(x, "writes")]:
            wr.setdefault(e["dst"], []).append(x)
        for e in out_e[(x, "triggers")]:
            hooks.append("`%s` triggers `%s` (%s)%s" % (x, e["dst"], ", ".join("`" + y + "`" for y in api_names(e["dst"])) or "given/no api", " - " + e["note"] if e.get("note") else ""))
    s += "### States this module writes (flags and data it is responsible for)\n"
    if wr:
        for st, srcs in wr.items():
            sn = N[st]
            s += "- `%s` (%s): %s -- written by %s\n" % (st, sn["label"], sn["text"], ", ".join("`%s`" % q for q in srcs))
    else:
        s += "- (none)\n"
    s += "\n### Hooks / triggers fired by this module's nodes\n"
    s += bullets(hooks) if hooks else "- (none)\n"
    s += "\n### Notes that name 'sets ... itself' / flags (from api notes)\n"
    fl = [("`%s`" % a["attrs"]["name"], a["attrs"]["notes"]) for a in apis if a["attrs"]["notes"]]
    s += bullets(["%s: %s" % x for x in fl]) if fl else "- (none)\n"
    s += "\n### Module-level decisions (resolve any api or node of this module)\n"
    seen = []
    for a in apis:
        for d in dec_res.get(a["id"], []):
            if d not in seen:
                seen.append(d)
    for x in nodes_:
        for d in dec_res.get(x, []):
            if d not in seen:
                seen.append(d)
    if seen:
        for d in seen:
            s += render_decision(d)
    else:
        s += "- (none)\n"
    # per-function
    s += "\n## 3. API contracts\n\n"
    ctx = {}
    for a in apis:
        s += render_api(a, mod, ctx)
    # rules
    s += "## 4. Rules this module is responsible for (id + text, verbatim from the graph)\n\n"
    rids = collections.OrderedDict()
    for x in nodes_:
        for e in in_e[(x, "constrains")]:
            rids.setdefault(e["src"], []).append(x)
    for r, xs in sorted(rids.items(), key=lambda kv: kv[0]):
        n = N[r]
        s += "- **%s** (%s): %s -- constrains %s\n" % (n["text"], n["type"], n["attrs"].get("summary", n["label"]), ", ".join("`%s`" % q for q in xs))
    if not rids:
        s += "- (none: constants / exception only)\n"
    s += "\n"
    return s

# ---------------------------------------------------------------- COMMON
COMMON = """# COMMON contract (read first)

Eight modules of the 1822 rules engine are missing and are written in parallel by eight coders: shares, certificates, company_formation, bidding, turn_order, trains, scoring, round_manager. Each coder works from this directory (contract/) and the given code in backend/app only. Per-module contracts (contract/<module>.md) are generated mechanically from the rule graph; BINDING.md holds the representation notes and the call matrix.

## Environment and conventions
- Python >= 3.11. Run everything from `/home/claude/sandbox_g2/backend/` with `PYTHONPATH=.` (example: `cd /home/claude/sandbox_g2/backend && PYTHONPATH=. python3 -c "from app.engine import shares"`).
- Money is integer pounds everywhere (no floats). Share units are integers of 10%.
- Modules live at `backend/app/engine/<module>.py` and are imported as `app.engine.<module>`.

## What you may read and write
- Read ONLY `/home/claude/sandbox_g2` (the contract/ directory and backend/app, including the given models, data tables, setup, actions, operating, stock_positions, main, rooms, db). Do not read anything else on the machine; no network, no git.
- Write ONLY your own module file `backend/app/engine/<your_module>.py`. Never edit given files or other coders' modules.
- Scratch tests go under `/home/claude/sandbox_g2/my_tests/<name>_*` (name = your module name).

## Hard requirements
1. Export EVERY api name and EVERY alias exactly as listed in your contract (functions, exception class, classes, constants). Aliases are the same callable under another name.
2. Keep exact call compatibility with the given code: given names, argument order, defaults and return types as in the contract signature; the given files (actions.py, setup.py, main.py, operating.py, stock_positions.py ...) call your functions and must keep working unchanged.
3. Exceptions: one exception class per module, derived directly from `Exception` (no shared base, no subclasses); message `"<ERR_CODE>: <text>"`; attribute `.code` = ERR_CODE (the string). Raise only the codes listed.
4. Atomicity: validate everything first (in the listed precedence order: the first failing `enforced` check raises); do not mutate state before the last check has passed.
5. Do not check what the contract says a function must NOT check (round type, active player etc. belong to actions.py).
6. Use the graph text of the contract verbatim; do not invent behaviour. Where the contract is ambiguous or contradictory, choose the most conservative reading, record it as an ambiguity in your report, and do not silently diverge.
7. Decisions marked INTERIM (needs_owner) are conservative defaults pending an owner ruling: follow them as written.
8. Import layering (lower number may be imported at module level by higher): 1 turn_order, 2 certificates, 3 scoring, 4 trains, 5 shares, 5 company_formation, 6 bidding, 7 round_manager. A call to a higher layer must be a lazy import inside the function. Do not create import cycles.
9. Cross-module calls must go through the callee's public api names exactly as listed in the call matrix (BINDING.md section 2).

## Final report format (your last message)
1. Implemented summary (functions/constants/aliases, deviations if any).
2. Numbered ambiguities (each: what is unclear, what you chose).
3. Contract problems (contradictions, missing information, signatures that cannot work with given code).
4. Integration check: once all eight module files exist (poll the directory for up to about 3 minutes), run an integration check through `new_game` (setup) plus `actions.apply_action` (for example a few passes / bids / buys / sells in a stock round and the transition to an operating round) and report the outcome; if the other files do not appear within about 3 minutes, say so and report what you could test alone.

## Shared names
Exception classes: shares.ShareError, certificates.CertificateError, company_formation.ConcessionError, bidding.BidError, turn_order.MarketError, trains.TrainError, scoring.ScoringError, round_manager.RoundError.

## Names fixed by given code (never rename)
@@GIVEN@@

## Module summary (api count)
@@COUNTS@@
"""

def common():
    given = []
    for a in APIS:
        at = a["attrs"]
        if at["given_name"]:
            given.append("`%s.%s` -- called from: %s" % (at["module"], at["name"], ", ".join(at["given_callers"]) or "(imported)"))
    counts = ["- %s: %d apis (%d functions, %d constants, %d exception/class)" % (
        m, len(by_mod[m]), sum(1 for a in by_mod[m] if a["attrs"]["kind"] == "function"),
        sum(1 for a in by_mod[m] if a["attrs"]["kind"] == "constant"),
        sum(1 for a in by_mod[m] if a["attrs"]["kind"] in ("class", "exception"))) for m in MODULES]
    return COMMON.replace("@@GIVEN@@", "\n".join(given)).replace("@@COUNTS@@", "\n".join(counts))

# ---------------------------------------------------------------- BINDING
def binding():
    s = "# BINDING: representation notes and call matrix (generated)\n\n"
    s += "## 1. Representation (repr nodes grouped by area)\n\nEach entry: concept, where it lives in the given data model, and the rule the coder must follow. `binds` lists the graph nodes it applies to.\n\n"
    reprs = [n for n in g["nodes"] if n["type"] == "repr"]
    # grouping by source/area: use id prefix keywords
    area_of = {}
    def area(r):
        key = (r["id"] + " " + r["attrs"]["concept"] + " " + r["attrs"]["maps_to"]).lower()
        rules = [
            ("Certificates, shares and ownership", ["unit", "certificate", "director", "ownership", "treasury", "pool", "share", "loan", "minor"]),
            ("Bid boxes and concessions", ["bid", "box", "concession", "private"]),
            ("Stock market and token pile", ["market", "token", "price", "pile", "cell"]),
            ("Trains and phases", ["train", "phase", "deck"]),
            ("Rounds, turns and order", ["round", "turn", "order", "sr_", "priority", "operating", "setup", "game", "or_"]),
        ]
        for name, kws in rules:
            if any(k in key for k in kws):
                return name
        return "Other"
    groups = collections.OrderedDict()
    for r in reprs:
        groups.setdefault(area(r), []).append(r)
    for ar, rs in groups.items():
        s += "### %s\n\n" % ar
        for r in rs:
            a = r["attrs"]
            s += "- **%s** (`%s`)\n  - maps to: %s\n  - rule for coder: %s\n  - binds: %s\n  - source: %s\n" % (
                a["concept"], r["id"], a["maps_to"], a["rule_for_coder"], ", ".join("`%s`" % b for b in a["binds"]) or "-", a["source"])
        s += "\n"
    s += "## 2. Call matrix (cross-module edges: calls and triggers between graph nodes implemented in different modules)\n\n"
    s += "Caller module.function -> callee module.api (edge type, graph nodes). A call into a higher layer must be a lazy import.\n\n"
    s += "| caller api | callee api | edge | nodes | callee signature |\n|---|---|---|---|---|\n"
    rows = set()
    given_rows = set()
    for e in E:
        if e["type"] not in ("calls", "triggers"):
            continue
        ca = api_of.get(e["src"], [])
        da = api_of.get(e["dst"], [])
        if not da:
            continue
        for c in ca:
            for d in da:
                if N[c]["attrs"]["module"] != N[d]["attrs"]["module"]:
                    rows.add((N[c]["attrs"]["module"] + "." + N[c]["attrs"]["name"], N[d]["attrs"]["module"] + "." + N[d]["attrs"]["name"], e["type"], e["src"] + " -> " + e["dst"], N[d]["attrs"]["signature"]))
        if not ca and N[e["src"]]["attrs"].get("implementation") == "given":
            for d in da:
                given_rows.add((N[e["src"]]["attrs"].get("given_symbol"), N[d]["attrs"]["module"] + "." + N[d]["attrs"]["name"], e["type"], e["src"] + " -> " + e["dst"], N[d]["attrs"]["signature"]))
    for r in sorted(rows):
        s += "| " + " | ".join(md_escape(x) for x in r) + " |\n"
    s += "\n### Calls made by GIVEN code (graph nodes with implementation=given)\n\n| given symbol | callee api | edge | nodes | callee signature |\n|---|---|---|---|---|\n"
    for r in sorted(given_rows):
        s += "| " + " | ".join(md_escape(x) for x in r) + " |\n"
    s += "\n### Callers per module (api-level callers fields: given code + graph)\n\n"
    for m in MODULES:
        s += "#### %s\n" % m
        for a in by_mod[m]:
            at = a["attrs"]
            if at["callers"]:
                s += "- `%s`: %s\n" % (at["name"], ", ".join(at["callers"]))
        s += "\n"
    return s

# ---------------------------------------------------------------- main
os.makedirs(OUT, exist_ok=True)
files = {}
for m in MODULES:
    files[m + ".md"] = module_contract(m)
files["COMMON.md"] = common()
files["BINDING.md"] = binding()
for fn, txt in files.items():
    open(os.path.join(OUT, fn), "w").write(txt)

# unrendered check
bad = []
for fn, txt in files.items():
    for pat in ("None\n", "{'", "[{", "<built-in", "object at 0x"):
        pass
    for m in re.finditer(r"(\{\w+\})|(%\()|(\bNone\b: )|(\[\])", txt):
        bad.append("%s: suspicious %r" % (fn, m.group(0)))
for n in g["nodes"]:
    if n["type"] in ("action", "derived"):
        if not api_of.get(n["id"]) and n["attrs"].get("implementation") != "given":
            bad.append("node without api and not given: " + n["id"])
for mnode in problems:
    bad.append(mnode)
covered_attrs = {
    "action": {"signature", "preconditions", "effects", "errors", "notes", "component", "implementation", "given_symbol", "wired"},
    "derived": {"signature", "formula", "notes", "component"},
}
open(os.path.join(OUT, "UNRENDERED.txt"), "w").write("\n".join(sorted(set(bad))) + "\n")
print("written:", ", ".join(sorted(files)))
print("apis:", {m: len(by_mod[m]) for m in MODULES})
print("problems:", len(set(bad)))
