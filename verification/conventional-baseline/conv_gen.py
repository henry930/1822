import json, os, re, sys, time, urllib.request, concurrent.futures as cf, shutil
KEY=open('/home/claude/.or_key').read().strip(); MODEL='deepseek/deepseek-v4-flash'
VAR=sys.argv[1]  # A: rulebook only ; B: + interface list
BASE='/home/claude/maint/base'; ENG='backend/app/engine'
OUT=f'/home/claude/conv/run_{VAR}'; shutil.rmtree(OUT,ignore_errors=True); shutil.copytree(BASE,OUT)
os.remove(f'{OUT}/verification/rule-tests/test_maint.py')
MODS=['shares','certificates','company_formation','bidding','turn_order','trains','scoring','round_manager']
DESC={'shares':'buying and selling shares, share sources (treasury/bank pool), loan interest','certificates':'certificate limit and counting, director certificate, director swaps',
'company_formation':'starting minor and major companies from bid-box items and concessions, floating, treasuries','bidding':'bid boxes, placing/moving bids, resolving bids at the end of a stock round',
'turn_order':'stock market prices and token movement, player order by cash','trains':'train purchase, availability, phase changes and rusting','scoring':'player wealth, final ranking, game-end triggers',
'round_manager':'starting and ending stock rounds and operating rounds, round bookkeeping'}
GIVEN=['models.py','setup.py','stock_positions.py','actions.py','operating.py']
def rd(p): return open(p).read()
given="\n\n".join(f"### FILE {ENG}/{g}\n```python\n{rd(f'{BASE}/{ENG}/{g}')}\n```" for g in GIVEN)
for p in ['phases','trains','stock_market','private_companies','major_companies','minor_companies','bid_box_tracks']:
    given+=f"\n\n### FILE backend/app/data/{p}.py\n```python\n{rd(f'{BASE}/backend/app/data/{p}.py')}\n```"
rules=rd('/tmp/rules.txt'); rulings=rd('/home/claude/1822/verification/RULINGS.md')
iface=rd('/home/claude/conv/iface.txt') if VAR=='B' else ''
mods="\n".join(f"- {m}: {DESC[m]}" for m in MODS)
def call(p):
    body={"model":MODEL,"messages":[{"role":"user","content":p}],"max_tokens":40000,"reasoning":{"effort":"low"},"temperature":0}
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=json.dumps(body).encode(),headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(req,timeout=900) as r: return json.load(r)
        except Exception as e: err=e; time.sleep(5)
    raise err
def gen(m):
    p=(f"You are a developer. Write ONE Python module `{ENG}/{m}.py` of a 1822 board-game rules engine (stock-round scope). The engine consists of these modules, written by other developers in parallel:\n{mods}\n"
       "The given code below already exists and cannot be changed; it calls into these modules. Implement the rules of the rulebook and the rulings for your module's responsibility. Reply with the COMPLETE file in a single ```python code block and nothing else.\n"
       +(f"\n## Interface list (names, signatures and aliases the other modules and the tests use)\n{iface}\n" if VAR=='B' else "")
       +f"\n## RULEBOOK\n{rules}\n\n## RULINGS\n{rulings}\n\n## GIVEN CODE\n{given}\n")
    t=time.time(); r=call(p); txt=r['choices'][0]['message']['content'] or ''
    mm=re.findall(r"```python\n(.*?)```",txt,re.S); code=max(mm,key=len) if mm else txt
    open(f'{OUT}/{ENG}/{m}.py','w').write(code); u=r.get('usage',{})
    return m,dict(secs=round(time.time()-t),prompt=u.get('prompt_tokens'),completion=u.get('completion_tokens'),cost=u.get('cost'),lines=code.count('\n'))
with cf.ThreadPoolExecutor(8) as ex: res=dict(ex.map(gen,MODS))
json.dump(res,open(f'{OUT}.usage.json','w'),indent=1); print(json.dumps(res))
print('TOTAL in',sum(v['prompt'] or 0 for v in res.values()),'out',sum(v['completion'] or 0 for v in res.values()),'cost',round(sum(v['cost'] or 0 for v in res.values()),4))
