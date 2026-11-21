#!/usr/bin/env python3
"""Verify graph.json v2.  Usage: python3 check_graph.py [graph.json] [given_code_dir]   (exit 1 on violations)

v1 requirements (1)-(4) are kept; v2 adds:
 (5) every action/derived node has an api node (edge `implements`), or is marked implementation=internal with an owner_api,
     or implementation=given with a given_symbol that exists in the given code;
 (6) every api node has module, signature (valid python, defaults explicit), raises list, enforced/not_enforced lists, callers;
 (7) every module's api list covers every name that the GIVEN code imports from it (AST scan of the given files, the 8 new
     module files themselves are NOT read), and given call sites are compatible with the api signatures (argument counts);
 (8) no two api nodes (names + aliases) share a name inside one module; one exception class per module, raises use it;
 (9) every state node is bound by a repr node; every v1 gap id (A.1.1-17, A.2.18-42, B-1..B-25) has a decision node.
"""
import json, re, sys, os, ast, collections

here = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "graph.json")
GIVEN = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/sandbox_g/backend/app"
g = json.load(open(path))
nodes = {}
viol, warn = [], []
NT = {"rule", "ruling", "entity", "state", "action", "derived", "component", "constant", "api", "repr", "decision"}
ET = {"constrains", "reads", "writes", "calls", "triggers", "overrides", "refers", "member_of", "uses_constant", "part_of", "order", "implements", "binds", "resolves", "supersedes"}
MODULES = ["shares", "certificates", "company_formation", "bidding", "turn_order", "trains", "scoring", "round_manager"]
for n in g["nodes"]:
    if n["id"] in nodes:
        viol.append("duplicate node id " + n["id"])
    nodes[n["id"]] = n
    if n["type"] not in NT:
        viol.append("bad node type %s (%s)" % (n["type"], n["id"]))
    for k in ("id", "type", "label", "text"):
        if k not in n or n[k] in (None, ""):
            viol.append("node %s missing %s" % (n.get("id"), k))
edges = g["edges"]
for e in edges:
    if e["type"] not in ET:
        viol.append("bad edge type %s" % e)
    for k in ("src", "dst"):
        if e[k] not in nodes:
            viol.append("dangling edge endpoint %s in %s->%s (%s)" % (e[k], e["src"], e["dst"], e["type"]))
    if e["type"] == "order" and not isinstance(e.get("seq"), int):
        viol.append("order edge without numeric seq %s->%s" % (e["src"], e["dst"]))
edges = [e for e in edges if e["src"] in nodes and e["dst"] in nodes]
T = lambda i: nodes[i]["type"]

ANY = set(NT)
SIG = {
    "constrains": ({"rule", "ruling"}, {"action", "derived", "state", "constant"}),
    "overrides": ({"ruling"}, {"rule"}),
    "supersedes": ({"ruling"}, {"ruling"}),
    "refers": ({"rule"}, {"rule"}),
    "reads": ({"action", "derived"}, {"state"}),
    "writes": ({"action"}, {"state"}),
    "calls": ({"action", "derived"}, {"action", "derived"}),
    "triggers": ({"action"}, {"action"}),
    "order": ({"action"}, {"action"}),
    "member_of": ({"action", "derived"}, {"component"}),
    "uses_constant": ({"action", "derived"}, {"constant"}),
    "part_of": ({"state"}, {"entity"}),
    "implements": ({"api"}, {"action", "derived", "state"}),
    "binds": ({"repr"}, ANY - {"repr"}),
    "resolves": ({"decision"}, ANY - {"decision"}),
}
for e in edges:
    s, d = SIG[e["type"]]
    if T(e["src"]) not in s or T(e["dst"]) not in d:
        viol.append("edge type signature violated: %s %s(%s) -> %s(%s)" % (e["type"], e["src"], T(e["src"]), e["dst"], T(e["dst"])))

# (1)
touch = collections.Counter()
for e in edges:
    if e["type"] in ("constrains", "overrides", "refers", "supersedes"):
        touch[e["src"]] += 1
        touch[e["dst"]] += 1
for n in nodes.values():
    if n["type"] in ("rule", "ruling") and touch[n["id"]] == 0:
        viol.append("(1) %s %s has no constrains/overrides/refers edge" % (n["type"], n["id"]))
for n in nodes.values():
    if n["type"] == "rule":
        outs = [e for e in edges if e["src"] == n["id"] and e["type"] == "constrains"]
        if not outs and not n["attrs"].get("deferred"):
            warn.append("rule %s constrains nothing (only refers)" % n["id"])

# (2)
rd = collections.defaultdict(set); wr = collections.defaultdict(set)
for e in edges:
    if e["type"] == "reads":
        rd[e["dst"]].add(e["src"])
    if e["type"] == "writes":
        wr[e["dst"]].add(e["src"])
for n in nodes.values():
    if n["type"] != "state":
        continue
    a = n["attrs"]
    for k in ("type", "scope", "unit", "owner_component"):
        if not a.get(k):
            viol.append("(2) state %s missing attr %s" % (n["id"], k))
    ext = a.get("external")
    if not wr[n["id"]] and not ext:
        viol.append("(2) state %s never written and not external" % n["id"])
    if not rd[n["id"]] and not ext:
        viol.append("(2) state %s never read and not external" % n["id"])
    if ext and not a.get("external_note"):
        viol.append("(2) external state %s lacks external_note" % n["id"])
    if not any(e["type"] == "part_of" and e["src"] == n["id"] for e in edges):
        viol.append("state %s has no part_of edge" % n["id"])
    if "comp." + str(a.get("owner_component")) not in nodes:
        viol.append("state %s owner_component unknown" % n["id"])

# (3)
membership = collections.defaultdict(list)
for e in edges:
    if e["type"] == "member_of":
        membership[e["src"]].append(e["dst"])
comps = [n["id"] for n in nodes.values() if n["type"] == "component"]
if not 5 <= len(comps) <= 8:
    viol.append("(3) component count %d not in 5..8" % len(comps))
for n in nodes.values():
    if n["type"] in ("action", "derived"):
        m = membership[n["id"]]
        if len(m) != 1:
            viol.append("(3) %s belongs to %d components" % (n["id"], len(m)))
        elif m[0] != "comp." + str(n["attrs"].get("component")):
            viol.append("(3) %s member_of disagrees with attrs.component" % n["id"])
comp_of = {k: v[0][5:] for k, v in membership.items() if v}
for c in comps:
    if not any(v and v[0] == c for v in membership.values()):
        viol.append("component %s is empty" % c)
cross = 0
for e in edges:
    if e["type"] in ("reads", "writes", "calls", "triggers"):
        sc = comp_of.get(e["src"])
        dc = nodes[e["dst"]]["attrs"]["owner_component"] if e["dst"].startswith("st.") else comp_of.get(e["dst"])
        isx = sc != dc
        cross += isx
        if bool(e.get("cross_component")) != isx:
            viol.append("(3) edge %s %s->%s cross_component flag wrong (src %s dst %s)" % (e["type"], e["src"], e["dst"], sc, dc))
for n in nodes.values():
    if n["type"] == "state":
        a = n["attrs"]
        accessors = {comp_of[e["src"]] for e in edges if e["dst"] == n["id"] and e["type"] in ("reads", "writes")} | {a["owner_component"]}
        if bool(a.get("shared")) != (len(accessors) > 1):
            viol.append("(3) state %s shared flag inconsistent" % n["id"])
        if set(a.get("writer_components", [])) != {comp_of[e["src"]] for e in edges if e["dst"] == n["id"] and e["type"] == "writes"}:
            viol.append("(3) state %s writer_components stale" % n["id"])

ruleids = {n["text"] for n in nodes.values() if n["type"] in ("rule", "ruling")}
REF = re.compile(r"\[([^\]]*)\]")
RID = re.compile(r"^(R\d+b?|\d+\.\d+\.\d+)$")
for n in nodes.values():
    if n["type"] == "action":
        a = n["attrs"]
        for k in ("preconditions", "effects", "errors", "signature"):
            if k not in a:
                viol.append("(4) action %s missing %s" % (n["id"], k))
        if not a.get("effects"):
            viol.append("(4) action %s has no effects" % n["id"])
        if not a.get("preconditions"):
            viol.append("(4) action %s has no preconditions" % n["id"])
        for p in a.get("preconditions", []):
            if p.get("rule") and p["rule"] not in ruleids:
                viol.append("(4) action %s precondition cites unknown rule %s" % (n["id"], p["rule"]))
            if not p.get("rule"):
                warn.append("action %s has a precondition without a rule id: %s" % (n["id"], p["check"][:50]))
        if not a.get("errors"):
            warn.append("action %s has an empty errors list" % n["id"])
        if not any(e["type"] == "constrains" and e["dst"] == n["id"] for e in edges):
            warn.append("action %s constrained by no rule" % n["id"])
    if n["type"] in ("action", "derived"):
        txt = json.dumps(n["attrs"]) + n["text"]
        for grp in REF.findall(txt):
            for part in re.split(r"[,;/ ]+", grp):
                if RID.match(part) and part not in ruleids:
                    viol.append("%s cites unknown rule %s" % (n["id"], part))
    if n["type"] == "derived" and not n["attrs"].get("formula"):
        viol.append("derived %s has no formula" % n["id"])
used = {e["dst"] for e in edges if e["type"] in ("uses_constant", "constrains")} | {e["src"] for e in edges if e["type"] == "constrains"}
for n in nodes.values():
    if n["type"] == "constant" and n["id"] not in used:
        warn.append("constant %s unused" % n["id"])
    if n["type"] == "constant" and n["attrs"].get("missing"):
        warn.append("constant %s still marked missing" % n["id"])
    if n["type"] == "entity" and not any(e["dst"] == n["id"] and e["type"] == "part_of" for e in edges):
        warn.append("entity %s has no state" % n["id"])

# ---------------------------------------------------------------- v2 checks
apis = {n["id"]: n for n in nodes.values() if n["type"] == "api"}
impl_by = collections.defaultdict(list)
for e in edges:
    if e["type"] == "implements":
        impl_by[e["dst"]].append(e["src"])

# (5) every action/derived has an api, or internal + owner_api, or given + existing given symbol
for n in nodes.values():
    if n["type"] not in ("action", "derived"):
        continue
    a = n["attrs"]
    mode = a.get("implementation", "api")
    if mode == "api":
        if not impl_by[n["id"]]:
            viol.append("(5) %s has no api node (no implements edge) and is not marked internal/given" % n["id"])
    elif mode == "internal":
        if a.get("owner_api") not in apis:
            viol.append("(5) internal %s has no valid owner_api" % n["id"])
    elif mode == "given":
        sym = a.get("given_symbol", "")
        fn, _, name = sym.partition(":")
        fp = os.path.join(GIVEN, fn)
        if not os.path.isfile(fp) or not re.search(r"^def %s\b" % re.escape(name), open(fp).read(), re.M):
            viol.append("(5) given %s: symbol %s not found in given code" % (n["id"], sym))
    else:
        viol.append("(5) %s unknown implementation mode %s" % (n["id"], mode))

# (6) api attributes
exc_by_module = collections.defaultdict(list)
for aid, n in apis.items():
    a = n["attrs"]
    for k in ("module", "name", "kind", "signature", "raises", "enforced", "not_enforced", "callers", "aliases", "implements", "defaults", "params"):
        if k not in a:
            viol.append("(6) api %s missing attr %s" % (aid, k))
    if a.get("module") not in MODULES:
        viol.append("(6) api %s module %s not one of the 8" % (aid, a.get("module")))
    if not a.get("signature"):
        viol.append("(6) api %s has no signature" % aid)
    if a.get("kind") == "function":
        try:
            ast.parse("def " + a["signature"] + ": pass")
        except SyntaxError:
            viol.append("(6) api %s signature is not valid python: %s" % (aid, a["signature"]))
        if not a.get("implements"):
            viol.append("(6) api function %s implements nothing" % aid)
        if not a.get("raises") and not a.get("not_enforced") and not a.get("returns"):
            warn.append("api %s documents neither raises, not_enforced nor returns" % aid)
    for r in a.get("raises", []):
        if not (r.get("class") and r.get("code") and r.get("when")):
            viol.append("(6) api %s raises entry incomplete: %s" % (aid, r))
    if a.get("kind") == "exception":
        exc_by_module[a["module"]].append(a["name"])
    if a.get("kind") == "constant" and "value" not in a:
        viol.append("(6) api constant %s has no value" % aid)
    if aid != "api.%s.%s" % (a.get("module"), a.get("name")):
        viol.append("(6) api id %s disagrees with module/name" % aid)
for m in MODULES:
    if len(exc_by_module[m]) != 1:
        viol.append("(8) module %s has %d exception classes (expected exactly 1)" % (m, len(exc_by_module[m])))
for aid, n in apis.items():
    a = n["attrs"]
    for r in a.get("raises", []):
        if r["class"] not in exc_by_module[a["module"]]:
            viol.append("(8) api %s raises %s which is not the exception class of module %s" % (aid, r["class"], a["module"]))
    for p in a.get("enforced", []):
        if not p.get("check"):
            viol.append("(6) api %s enforced entry without check" % aid)
    codes_enf = " ".join((p.get("code") or "") for p in a.get("enforced", []))
    for r in a.get("raises", []):
        if a.get("enforced") and r["code"] not in codes_enf:
            warn.append("api %s raises %s but no enforced precondition lists it" % (aid, r["code"]))

# (8) names unique inside a module (names + aliases)
seen = {}
for aid, n in apis.items():
    a = n["attrs"]
    for nm in [a["name"]] + list(a.get("aliases", [])):
        key = (a["module"], nm)
        if key in seen and seen[key] != aid:
            viol.append("(8) name %s.%s used by both %s and %s" % (a["module"], nm, seen[key], aid))
        seen[key] = aid

# (7) names imported / called by the given code
given_files = []
for root, _d, fs in os.walk(GIVEN):
    for f in fs:
        if f.endswith(".py") and not (os.path.basename(root) == "engine" and f[:-3] in MODULES):
            given_files.append(os.path.join(root, f))
imported = collections.defaultdict(dict)   # module -> name -> [(file, lineno)]
calls_seen = []                            # (module, name, nargs, nkw, file, lineno)
for fp in sorted(given_files):
    src = open(fp).read()
    tree = ast.parse(src)
    local = {}   # local name -> (module, name)
    modalias = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[-1]
            in_engine = (node.level >= 1 and os.path.basename(os.path.dirname(fp)) == "engine") or (node.module or "").startswith("app.engine.")
            if mod in MODULES and in_engine:
                for al in node.names:
                    imported[mod].setdefault(al.name, []).append((os.path.relpath(fp, GIVEN), node.lineno))
                    local[al.asname or al.name] = (mod, al.name)
            else:
                for al in node.names:
                    if al.name in MODULES and (node.module or "").endswith("engine"):
                        modalias[al.asname or al.name] = al.name
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f_ = node.func
            if isinstance(f_, ast.Name) and f_.id in local:
                calls_seen.append(local[f_.id] + (len(node.args), [k.arg for k in node.keywords], os.path.relpath(fp, GIVEN), node.lineno))
            elif isinstance(f_, ast.Attribute) and isinstance(f_.value, ast.Name) and f_.value.id in modalias:
                imported[modalias[f_.value.id]].setdefault(f_.attr, []).append((os.path.relpath(fp, GIVEN), node.lineno))
api_names = collections.defaultdict(dict)
for aid, n in apis.items():
    a = n["attrs"]
    api_names[a["module"]][a["name"]] = n
    for al in a.get("aliases", []):
        api_names[a["module"]][al] = n
n_imports = 0
for mod, names in imported.items():
    for nm, locs in names.items():
        n_imports += 1
        if nm not in api_names[mod]:
            viol.append("(7) given code %s:%s imports %s.%s but no api node covers it" % (locs[0][0], locs[0][1], mod, nm))
        elif not api_names[mod][nm]["attrs"].get("given_name") and api_names[mod][nm]["attrs"]["name"] == nm:
            viol.append("(7) api %s.%s is used by given code but not flagged given_name" % (mod, nm))
for mod, nm, nargs, kws, f, ln in calls_seen:
    if nm not in api_names[mod]:
        continue
    a = api_names[mod][nm]["attrs"]
    if a["kind"] != "function":
        continue
    params = a["params"]
    required = [p for p in params if p not in a["defaults"]]
    if nargs > len(params):
        viol.append("(7) call %s.%s at %s:%d passes %d positional args, api accepts %d" % (mod, nm, f, ln, nargs, len(params)))
    elif nargs + len(kws) < len(required):
        viol.append("(7) call %s.%s at %s:%d passes %d args, api requires %d" % (mod, nm, f, ln, nargs + len(kws), len(required)))
    for k in kws:
        if k not in params:
            viol.append("(7) call %s.%s at %s:%d uses keyword %s unknown to the api" % (mod, nm, f, ln, k))
# the stated defaults of the task
want = {("shares", "buy_share"): ("source", "None"), ("round_manager", "start_operating_round"): ("phase_before", "None"), ("scoring", "check_game_end_triggers"): ("context", "None")}
for (m, nm), (p, d) in want.items():
    a = api_names[m].get(nm)
    if not a or a["attrs"]["defaults"].get(p) != d:
        viol.append("(7) %s.%s must default %s=%s" % (m, nm, p, d))
# resolve_stock_round / buy_train_from_bank must not carry the forbidden preconditions
for nm_, forbidden in (("api.bidding.resolve_stock_round", ("ERR_NOT_OVER",)), ("api.trains.buy_train_from_bank", ("ERR_NOT_FLOATED", "ERR_NOT_STARTED"))):
    a = apis.get(nm_)
    if a and any(r["code"] in forbidden for r in a["attrs"]["raises"]):
        viol.append("(7) %s raises a forbidden precondition" % nm_)

# (9) repr coverage and gap coverage
bound = collections.Counter(e["dst"] for e in edges if e["type"] == "binds")
for n in nodes.values():
    if n["type"] == "state" and not bound[n["id"]]:
        viol.append("(9) state %s is bound by no repr node" % n["id"])
    if n["type"] == "repr":
        for k in ("concept", "maps_to", "binds", "rule_for_coder"):
            if not n["attrs"].get(k):
                viol.append("(9) repr %s missing %s" % (n["id"], k))
gaps = {n["attrs"]["gap"] for n in nodes.values() if n["type"] == "decision"}
need = ["A.1.%d" % i for i in range(1, 18)] + ["A.2.%d" % i for i in range(18, 43)] + ["B-%d" % i for i in range(1, 26)]
for gid in need:
    if gid not in gaps:
        viol.append("(9) GAPS item %s has no decision node" % gid)
for n in nodes.values():
    if n["type"] == "decision":
        a = n["attrs"]
        for k in ("gap", "choice", "reason", "kind"):
            if not a.get(k):
                viol.append("(9) decision %s missing %s" % (n["id"], k))
        if not a.get("resolves"):
            viol.append("(9) decision %s resolves no node" % n["id"])
if "ruling.R6b" not in nodes:
    viol.append("ruling R6b missing")

cn = collections.Counter(n["type"] for n in nodes.values()); ce = collections.Counter(e["type"] for e in edges)
print("nodes:", dict(cn), "total", sum(cn.values()))
print("edges:", dict(ce), "total", sum(ce.values()), "| cross-component state/call edges:", cross)
print("given-code imports from the 8 modules checked: %d names, %d call sites" % (n_imports, len(calls_seen)))
for w in warn:
    print("WARN", w)
for v in viol:
    print("VIOLATION", v)
print("%d violation(s), %d warning(s)" % (len(viol), len(warn)))
sys.exit(1 if viol else 0)
