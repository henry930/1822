import json, os, re, subprocess, sys, time, urllib.request
VAR=sys.argv[1]; ROUNDS=int(sys.argv[2]) if len(sys.argv)>2 else 5
EVAL=f'/home/claude/conv/run_{VAR}'; ENG=EVAL+'/backend/app/engine'
KEY=open('/home/claude/.or_key').read().strip()
MODS=['shares','certificates','company_formation','bidding','turn_order','trains','scoring','round_manager']
GIVEN=['models.py','setup.py','stock_positions.py','actions.py','operating.py']
def rd(p): return open(p).read()
given="\n\n".join(f"### FILE backend/app/engine/{g}\n```python\n{rd(f'{ENG}/{g}')}\n```" for g in GIVEN)
iface=rd('/home/claude/conv/iface.txt') if VAR=='B' else ''
def call(p):
    body={"model":"deepseek/deepseek-v4-flash","messages":[{"role":"user","content":p}],"max_tokens":40000,"reasoning":{"effort":"low"},"temperature":0}
    req=urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",data=json.dumps(body).encode(),headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
    for a in range(3):
        try:
            with urllib.request.urlopen(req,timeout=900) as r: return json.load(r)
        except Exception as e: err=e; time.sleep(5)
    raise err
def smoke():
    p=subprocess.run(['python3','/home/claude/work/ds/smoke.py'],cwd=EVAL,capture_output=True,text=True); return p.stdout+p.stderr
tot=dict(prompt=0,completion=0,cost=0.0,calls=0)
for rnd in range(1,ROUNDS+1):
    out=smoke(); print(f"--- round {rnd} smoke:\n{out[:1200]}")
    if 'SMOKE OK' in out: break
    mods=[m for m in MODS if re.search(r'engine/'+m+r'\.py',out) or re.search(r'\b'+m+r'\b',out)][:4] or MODS[:2]
    parts="\n\n".join(f"### CURRENT CODE {m}.py\n```python\n{rd(f'{ENG}/{m}.py')}\n```" for m in mods)
    p=("Several engine modules were written by different developers from the rulebook and do not fit together. Running a smoke scenario (no tests, only the engine through actions.apply_action) fails as below. Fix the modules so the scenario runs. Reply with every file you changed COMPLETE, each as a ```python block whose first line is `# FILE: <module>.py`. Only the eight engine modules may be changed; the GIVEN CODE can NOT be changed. Do not change a file you do not need to.\n\n"
       +(f"## Interface list\n{iface}\n\n" if iface else "")+f"## SMOKE OUTPUT\n{out}\n\n{parts}\n\n## GIVEN CODE\n{given}\n")
    r=call(p); u=r.get('usage',{}); tot['prompt']+=u.get('prompt_tokens',0); tot['completion']+=u.get('completion_tokens',0); tot['cost']+=u.get('cost') or 0; tot['calls']+=1
    txt=r['choices'][0]['message']['content'] or ''
    for blk in re.findall(r"```python\n(.*?)```",txt,re.S):
        mm=re.match(r"# FILE: (\w+)\.py",blk.strip())
        if mm and mm.group(1) in MODS: open(f'{ENG}/{mm.group(1)}.py','w').write(blk); print('patched',mm.group(1))
print('final smoke:',smoke()[:600]); print(json.dumps(tot))
