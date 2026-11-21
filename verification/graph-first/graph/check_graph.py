#!/usr/bin/env python3
"""Verify graph.json: requirements (1)-(3), dangling edges, action contract attrs. Exit 1 on violations."""
import json, re, sys, os, collections

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph.json")
g = json.load(open(path))
nodes = {}
viol, warn = [], []
NT = {"rule", "ruling", "entity", "state", "action", "derived", "component", "constant"}
ET = {"constrains", "reads", "writes", "calls", "triggers", "overrides", "refers", "member_of", "uses_constant", "part_of", "order"}
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

SIG = {
    "constrains": ({"rule", "ruling"}, {"action", "derived", "state", "constant"}),
    "overrides": ({"ruling"}, {"rule"}),
    "refers": ({"rule"}, {"rule"}),
    "reads": ({"action", "derived"}, {"state"}),
    "writes": ({"action"}, {"state"}),
    "calls": ({"action", "derived"}, {"action", "derived"}),
    "triggers": ({"action"}, {"action"}),
    "order": ({"action"}, {"action"}),
    "member_of": ({"action", "derived"}, {"component"}),
    "uses_constant": ({"action", "derived"}, {"constant"}),
    "part_of": ({"state"}, {"entity"}),
}
for e in edges:
    s, d = SIG[e["type"]]
    if T(e["src"]) not in s or T(e["dst"]) not in d:
        viol.append("edge type signature violated: %s %s(%s) -> %s(%s)" % (e["type"], e["src"], T(e["src"]), e["dst"], T(e["dst"])))

# (1)
touch = collections.Counter()
for e in edges:
    if e["type"] in ("constrains", "overrides", "refers"):
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
RID = re.compile(r"^(R\d+|\d+\.\d+\.\d+)$")
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
    if n["type"] == "entity" and not any(e["dst"] == n["id"] and e["type"] == "part_of" for e in edges):
        warn.append("entity %s has no state" % n["id"])

cn = collections.Counter(n["type"] for n in nodes.values()); ce = collections.Counter(e["type"] for e in edges)
print("nodes:", dict(cn), "total", sum(cn.values()))
print("edges:", dict(ce), "total", sum(ce.values()), "| cross-component state/call edges:", cross)
for w in warn:
    print("WARN", w)
for v in viol:
    print("VIOLATION", v)
print("%d violation(s), %d warning(s)" % (len(viol), len(warn)))
sys.exit(1 if viol else 0)
