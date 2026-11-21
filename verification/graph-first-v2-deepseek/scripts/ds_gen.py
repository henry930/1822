import json, os, re, sys, time, urllib.request, concurrent.futures as cf
KEY = open('/home/claude/.or_key').read().strip()
MODEL = os.environ.get('DS_MODEL', 'deepseek/deepseek-v4-flash')
SB = '/home/claude/sandbox_g2'
OUT = sys.argv[1]
MODS = os.environ.get('DS_MODS','shares,certificates,company_formation,bidding,turn_order,trains,scoring,round_manager').split(',')
GIVEN = ['backend/app/engine/models.py','backend/app/engine/setup.py','backend/app/engine/stock_positions.py','backend/app/engine/actions.py',
 'backend/app/engine/operating.py','backend/app/data/phases.py','backend/app/data/trains.py','backend/app/data/stock_market.py',
 'backend/app/data/private_companies.py','backend/app/data/major_companies.py','backend/app/data/minor_companies.py','backend/app/data/bid_box_tracks.py']
def rd(p): return open(os.path.join(SB, p)).read()
given = "\n\n".join(f"### FILE {p}\n```python\n{rd(p)}\n```" for p in GIVEN)
def call(prompt, effort=os.environ.get('DS_EFFORT','medium')):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 60000,
            "reasoning": {"effort": effort}, "temperature": 0}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(req, timeout=900) as r: return json.load(r)
        except Exception as e:
            err = e; time.sleep(5)
    raise err
def gen(m):
    prompt = (f"You are a coder. Write ONE Python module `backend/app/engine/{m}.py` for a 1822 board-game rules engine.\n"
      "Your ONLY specification is the contract below (COMMON, BINDING, and the contract of your module). The other seven modules "
      "(shares, certificates, company_formation, bidding, turn_order, trains, scoring, round_manager) are written by other coders from their own contracts; "
      "call them only through the APIs listed in BINDING. The given code (not to be changed) follows the contract. "
      "Export every api name and alias exactly as listed. Use lazy imports inside functions for upward/circular calls. "
      "Reply with the COMPLETE file in a single ```python code block and nothing else.\n\n"
      f"## COMMON.md\n{rd('contract/COMMON.md')}\n\n## BINDING.md\n{rd('contract/BINDING.md')}\n\n## {m}.md (your module)\n{rd(f'contract/{m}.md')}\n\n## GIVEN CODE\n{given}\n")
    t = time.time(); r = call(prompt); dt = time.time() - t
    txt = r['choices'][0]['message']['content'] or ''
    mm = re.findall(r"```python\n(.*?)```", txt, re.S)
    code = max(mm, key=len) if mm else txt
    os.makedirs(os.path.join(OUT, 'engine'), exist_ok=True)
    open(os.path.join(OUT, 'engine', m + '.py'), 'w').write(code)
    open(os.path.join(OUT, f'{m}.raw.txt'), 'w').write(txt)
    u = r.get('usage', {})
    return m, dict(secs=round(dt), prompt=u.get('prompt_tokens'), completion=u.get('completion_tokens'), cost=u.get('cost'), lines=code.count('\n'))
os.makedirs(OUT, exist_ok=True)
with cf.ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(gen, MODS))
json.dump(res, open(os.path.join(OUT, 'usage.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
