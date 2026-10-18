"""Scan all Codex rollouts for exec_command cmds that mention a path pattern; write them in time order."""
import json, glob, sys, os
BS = chr(92)
pat = sys.argv[1]
outdir = sys.argv[2]
os.makedirs(outdir, exist_ok=True)


def cmds(inp):
    k = 0
    while True:
        i = inp.find('cmd:"', k)
        if i < 0:
            return
        i += 5
        j = i
        while True:
            ch = inp[j]
            if ch == BS:
                j += 2
                continue
            if ch == '"':
                break
            j += 1
        try:
            yield json.loads('"' + inp[i:j] + '"')
        except Exception as e:
            yield 'UNPARSED ' + inp[i:j]
        k = j + 1


rows = []
for f in sorted(glob.glob('C:/Users/lambd/.codex/sessions/2026/10/1[3-7]/*.jsonl')):
    for l in open(f, encoding='utf-8'):
        if pat not in l:
            continue
        d = json.loads(l)
        p = d.get('payload', {})
        if p.get('type') not in ('custom_tool_call', 'function_call'):
            continue
        inp = p.get('input') or p.get('arguments') or ''
        for c in cmds(inp):
            if pat in c:
                rows.append((d['timestamp'], os.path.basename(f)[:40], c))
rows.sort()
for n, (t, f, c) in enumerate(rows):
    w = any(x in c for x in ('WriteAllText', 'Replace(', 'write_text', 'apply_patch', 'Substring', 'sed -i', 'Set-Content'))
    open(os.path.join(outdir, '%03d.txt' % n), 'w', encoding='utf-8', newline='').write(c)
    print('%03d' % n, t, f, 'W' if w else '-', c[:110].replace('\n', ' '))
