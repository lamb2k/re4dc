"""For every lane's chosen targets whose fixture source is under codex-cx-fixtures-20261013, record
(source path, sha, size, harvested?) -> cx-targets.tsv (dedup by source path; conflicts flagged)."""
import sqlite3, json, os, collections
c = sqlite3.connect(r'file:C:/Game Dev/Emulators/re4dc-recovery/harvest.db?mode=ro', uri=True)
have = set(r[0] for r in c.execute('select sha from files'))
lanes = [r[0] for r in c.execute('select distinct lane from targets')]
EV = r'C:/Flycast-Evidence/re4-dreamcast/'
out = {}
conf = 0
stagecache = {}
for lane in lanes:
    rows = list(c.execute('select path,sha,size,run from targets where lane=? and chosen=1', (lane,)))
    for p, s, z, run in rows:
        sj = os.path.join(EV, lane, run.replace(chr(92), '/'), 'stage.json')
        if sj not in stagecache:
            try:
                stagecache[sj] = json.load(open(sj))['fixture'].get('replace', {})
            except Exception:
                stagecache[sj] = None
        rep = stagecache[sj]
        if not rep:
            continue
        src = rep.get(p, '')
        if 'codex-cx-fixtures-20261013' not in src:
            continue
        if src in out and out[src][0] != s:
            conf += 1
        out[src] = (s, z, s in have, lane, p)
print('lanes', len(lanes), 'cx sources', len(out), 'conflicts', conf)
cnt = collections.Counter((v[2], v[3]) for v in out.values())
for k, n in sorted(cnt.items()):
    print(k, n)
with open('cx-targets.tsv', 'w') as f:
    for src, (s, z, h, lane, p) in sorted(out.items()):
        f.write('\t'.join([src, s, str(z), 'H' if h else 'M', lane, p]) + '\n')
