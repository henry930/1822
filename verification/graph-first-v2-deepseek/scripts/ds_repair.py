import json, os, re, subprocess, sys
sys.argv_backup = sys.argv
EVAL = sys.argv[1]; ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 3
sys.argv = [sys.argv[0], '/tmp/_unused']
exec(open('/home/claude/work/ds/ds_gen.py').read().split("os.makedirs(OUT, exist_ok=True)\nwith cf")[0])
ENG = os.path.join(EVAL, 'backend/app/engine')
def smoke():
    p = subprocess.run(['python3', '/home/claude/work/ds/smoke.py'], cwd=EVAL, capture_output=True, text=True)
    return p.stdout + p.stderr
tot = dict(prompt=0, completion=0, cost=0.0, calls=0)
for rnd in range(1, ROUNDS + 1):
    out = smoke()
    print(f"--- round {rnd} smoke:\n{out[:1500]}")
    if 'SMOKE OK' in out: break
    mods = [m for m in MODS if re.search(r'engine/' + m + r'\.py', out) or re.search(r'\b' + m + r'\b', out)]
    mods = mods[:4] or MODS[:2]
    parts = []
    for m in mods:
        parts.append(f"### CONTRACT {m}.md\n{rd(f'contract/{m}.md')}\n### CURRENT CODE {m}.py\n```python\n{open(os.path.join(ENG, m + '.py')).read()}\n```")
    prompt = ("Several engine modules were written by different coders from their own contracts and do not fit together. Running a smoke scenario "
        "(no tests, only the engine through actions.apply_action) fails as below. Fix the modules so the scenario runs and each module follows its contract "
        "and BINDING (call matrix). Decide which file is wrong from the contracts; shared constants/mode names must match what the CALLEE's contract defines. "
        "Reply with every file you changed COMPLETE, each as a ```python block whose first line is `# FILE: <module>.py`. Only the eight engine modules may be changed; the GIVEN CODE (models.py, setup.py, actions.py, data tables ...) can NOT be changed, so if a module uses a state field or name that the given code does not have, change the module. Do not change a file you do not need to.\n\n"
        f"## SMOKE OUTPUT\n{out}\n\n## BINDING.md\n{rd('contract/BINDING.md')}\n\n" + "\n\n".join(parts) + f"\n\n## GIVEN CODE\n{given}\n")
    r = call(prompt, 'low')
    u = r.get('usage', {}); tot['prompt'] += u.get('prompt_tokens', 0); tot['completion'] += u.get('completion_tokens', 0); tot['cost'] += u.get('cost') or 0; tot['calls'] += 1
    txt = r['choices'][0]['message']['content'] or ''
    open(f'/home/claude/ds_repair_raw_{rnd}.txt','w').write(txt)
    for blk in re.findall(r"```python\n(.*?)```", txt, re.S):
        mm = re.match(r"# FILE: (\w+)\.py", blk.strip())
        if mm and mm.group(1) in MODS:
            open(os.path.join(ENG, mm.group(1) + '.py'), 'w').write(blk)
            print('patched', mm.group(1))
print('final smoke:', smoke()[:800])
print(tot)
