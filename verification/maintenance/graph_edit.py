import json, sys, copy
CHANGES = {
 "M1": {"const.interest": [("ceil(loans/2)", "ceil(loans/4)"), ("SET", "attrs.rate_percent", 25)],
        "drv.interest_amount": [("ceil(L/2) = (L+1)//2", "ceil(L/4) = (L+3)//4")],
        "ruling.R14": [("ceil(loans/2)", "ceil(loans/4)")],
        "rule.4.11.10": [("50% interest", "25% interest")],
        "rule.4.3.4": [("50% interest", "25% interest")],
        "act.charge_interest": [("Add 50% interest", "Add 25% interest")],
        "api.shares.interest_amount": [("(loans + 1) // 2", "(loans + 3) // 4")],
        "repr.money": [("(loans + 1) // 2", "(loans + 3) // 4")]},
 "M2": {"const.share_structure": [("Pool cap 5 units", "Pool cap 6 units"), ("SET", "attrs.pool_cap_units", 6)],
        "api.certificates.POOL_CAP_UNITS": [("POOL_CAP_UNITS = 5", "POOL_CAP_UNITS = 6"), ("SET", "attrs.value", 6), ("at most 5 units", "at most 6 units")],
        "api.shares.sell_shares": [("pool would exceed 5 units", "pool would exceed 6 units")],
        "act.sell_shares": [("pool_shares[c] + s <= 5 (50% of the company)", "pool_shares[c] + s <= 6 (60% of the company)")],
        "st.pool_shares": [("Max 5 (50%)", "Max 6 (60%)")],
        "ent.bank_pool": [("max 50% of a company's stock (5 units)", "max 60% of a company's stock (6 units)")],
        "rule.4.4.2": [("pool <= 50%", "pool <= 60%")]},
 "M3": {"ruling.R3": [("Phase 3+: treasury = bid.", "Phase 3+: treasury = half the bid, rounded down (bid // 2).")],
        "drv.minor_start_treasury": [("phase >=3: bid", "phase >=3: bid // 2")],
        "api.company_formation.minor_start_treasury": [("phase >= 3: bid;", "phase >= 3: bid // 2;")],
        "rule.4.11.4": [("treasury = bid.", "treasury = bid // 2 (half the bid, rounded down).")]},
}
k, src, dst = sys.argv[1:4]
g = json.load(open(src)); N = {n['id']: i for i, n in enumerate(g['nodes'])}
def sub(x, old, new):
    if isinstance(x, str): return x.replace(old, new)
    if isinstance(x, list): return [sub(i, old, new) for i in x]
    if isinstance(x, dict): return {kk: sub(v, old, new) for kk, v in x.items()}
    return x
for nid, reps in CHANGES[k].items():
    node = g['nodes'][N[nid]]
    for rep in reps:
        if rep[0] == "SET":
            _, path, val = rep; d = node; parts = path.split('.')
            for p in parts[:-1]: d = d[p]
            assert parts[-1] in d, (k, nid, path); d[parts[-1]] = val
        else:
            old, new = rep
            before = json.dumps(node, ensure_ascii=False)
            node = sub(node, old, new)
            assert json.dumps(node, ensure_ascii=False) != before, (k, nid, old)
    g['nodes'][N[nid]] = node
json.dump(g, open(dst, 'w'), ensure_ascii=False, indent=1)
print(k, "nodes edited:", len(CHANGES[k]))
