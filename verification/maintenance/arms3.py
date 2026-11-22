import json, os, re, sys, time, shutil, subprocess, difflib, urllib.request, concurrent.futures as cf
KEY=open('/home/claude/.or_key').read().strip()
MODEL='deepseek/deepseek-v4-flash'
ARM,CH=sys.argv[1],sys.argv[2]   # arm in A,B,C,D ; change M1..M3
MODS=['shares','certificates','company_formation','bidding','turn_order','trains','scoring','round_manager']
BASE='/home/claude/maint/base'; ENG='backend/app/engine'
REQ={'M1':"Rule change: loan interest is now 25% of the loans (rounded up to a whole unit) instead of 50%.",
 'M2':"Rule change: the bank pool may hold up to 6 share units (previously 5).",
 'S1':"Rule change: a 5% brokerage fee (rounded up) is charged to the buyer on every share purchase and on every winning bid on a bid-box item, and is paid to the bank. Add a function shares.brokerage_fee(amount) returning it.",'M3':"Rule change: in phase 3 and later a minor company's starting treasury is half of the winning bid (rounded down) instead of the full bid."}[CH]
GIVEN=['models.py','setup.py','stock_positions.py','actions.py','operating.py']
def rd(p): return open(p).read()
given="\n\n".join(f"### FILE {ENG}/{g}\n```python\n{rd(f'{BASE}/{ENG}/{g}')}\n```" for g in GIVEN)
for p in ['phases','trains','stock_market','private_companies','major_companies','minor_companies','bid_box_tracks']:
    given+=f"\n\n### FILE backend/app/data/{p}.py\n```python\n{rd(f'{BASE}/backend/app/data/{p}.py')}\n```"
CB,CN=f'/home/claude/maint/contract_b2',f'/home/claude/maint/contract_{CH}b'
def cdiff(m):
    return "".join(difflib.unified_diff(rd(f'{CB}/{m}.md').splitlines(1),rd(f'{CN}/{m}.md').splitlines(1),'old','new',n=2))
changed=[m for m in MODS if rd(f'{CB}/{m}.md')!=rd(f'{CN}/{m}.md')]
bind_changed=rd(f'{CB}/BINDING.md')!=rd(f'{CN}/BINDING.md')
import re as _re, math as _m
def _top(k=2):
    q=set(_re.findall(r'[a-z]+',REQ.lower()))-{'the','a','of','is','and','to','in','on','it','or','by','up','as','than','instead','now','every','for','with','be','add','function','returning','later','that','are','its','half','whole','unit','paid','charged'}
    sc={}
    for m in MODS:
        words=_re.findall(r'[a-z]+',rd(f'{BASE}/{ENG}/{m}.py').lower())
        sc[m]=sum(words.count(w)/ (1+_m.log(1+len(words))) for w in q)
    return sorted(sc,key=lambda m:-sc[m])[:k]
RET=_top() if ARM=='E' else None
tgt = MODS if ARM in 'AD' else (RET if ARM=='E' else changed)
if ARM=='D': tgt=MODS
OUT=f'/home/claude/maint/run3_{ARM}_{CH}'; shutil.rmtree(OUT,ignore_errors=True); shutil.copytree(BASE,OUT)
if CH=='S1': shutil.copy('/home/claude/maint/tests/test_maint.py',OUT+'/verification/rule-tests/test_maint.py')
TAIL="Reply with the COMPLETE updated file in a single ```python code block and nothing else."
def prompt(m):
    old=rd(f'{BASE}/{ENG}/{m}.py')
    if ARM in 'AB':
        return (f"You are a coder. Write ONE Python module `{ENG}/{m}.py` for a 1822 board-game rules engine. Your ONLY specification is the contract below. Other modules are written by other coders; call them only via BINDING. Export every api name exactly as listed. Use lazy imports for circular calls. {TAIL}\n\n## COMMON.md\n{rd(CN+'/COMMON.md')}\n\n## BINDING.md\n{rd(CN+'/BINDING.md')}\n\n## {m}.md\n{rd(f'{CN}/{m}.md')}\n\n## GIVEN CODE\n{given}\n")
    if ARM=='C':
        return (f"You maintain module `{ENG}/{m}.py` of a 1822 rules engine. The specification (contract) of this module changed. Below are the contract DIFF and the current code. Update the code so it satisfies the new contract; change nothing else. {TAIL}\n\n## BINDING diff\n{cdiff('BINDING') if bind_changed else '(none)'}\n\n## {m}.md contract diff\n{cdiff(m)}\n\n## CURRENT CODE\n```python\n{old}\n```\n")
    if ARM=='E':
        src="\n\n".join(f"### FILE {ENG}/{x}.py\n```python\n{rd(f'{BASE}/{ENG}/{x}.py')}\n```" for x in RET)
        return (f"You maintain a 1822 board-game rules engine. {REQ}\nBelow is the source of the modules most likely affected (found by keyword search). Return ONLY the file `{ENG}/{m}.py` updated if it needs a change for this request (return it unchanged if no change is needed). {TAIL}\n\n{src}\n\n## GIVEN CODE\n{given}\n")
    if ARM=='D':
        src="\n\n".join(f"### FILE {ENG}/{x}.py\n```python\n{rd(f'{BASE}/{ENG}/{x}.py')}\n```" for x in MODS)
        return (f"You maintain a 1822 board-game rules engine. {REQ}\nBelow is the full source of the engine modules. Return ONLY the file `{ENG}/{m}.py` updated if it needs a change for this request (return it unchanged if no change is needed). {TAIL}\n\n{src}\n")
def call(p):
    body={"model":MODEL,"messages":[{"role":"user","content":p}],"max_tokens":40000,"reasoning":{"effort":"low"},"temperature":0}
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=json.dumps(body).encode(),headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(req,timeout=900) as r: return json.load(r)
        except Exception as e: err=e; time.sleep(5)
    raise err
def go(m):
    t=time.time(); r=call(prompt(m)); txt=r['choices'][0]['message']['content'] or ''
    mm=re.findall(r"```python\n(.*?)```",txt,re.S); code=max(mm,key=len) if mm else txt
    open(f'{OUT}/{ENG}/{m}.py','w').write(code); u=r.get('usage',{})
    return m,dict(secs=round(time.time()-t),prompt=u.get('prompt_tokens'),completion=u.get('completion_tokens'),cost=u.get('cost'))
with cf.ThreadPoolExecutor(8) as ex: res=dict(ex.map(go,tgt))
res_tests=subprocess.run(f'bash /home/claude/maint/run_tests.sh {OUT}',shell=True,capture_output=True,text=True).stdout
open(f'{OUT}.tests.txt','w').write(res_tests)
orc=set(rd(f'/home/claude/maint/oracle_{CH}.txt').split('\n'))-{''}; got=set(res_tests.split('\n'))-{''}
summ=dict(arm=ARM,change=CH,modules=tgt,bind_changed=bind_changed,tokens_in=sum(v['prompt'] or 0 for v in res.values()),tokens_out=sum(v['completion'] or 0 for v in res.values()),
  cost=round(sum(v['cost'] or 0 for v in res.values()),4),secs_max=max(v['secs'] for v in res.values()),
  oracle_match=orc==got,pass_n=sum(l.startswith('PASSED') for l in got),oracle_pass=sum(l.startswith('PASSED') for l in orc),
  diff_vs_oracle=sorted(orc^got)[:12])
json.dump(summ,open(f'{OUT}.summary.json','w'),indent=1); print(json.dumps(summ))
