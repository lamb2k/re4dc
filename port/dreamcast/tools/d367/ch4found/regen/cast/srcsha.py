"""Recorded shas for given source paths (from every lane's chosen targets + stage.json fixture.replace).
usage: python c4r-srcsha.py <source path substring>..."""
import sqlite3, json, os, sys
c = sqlite3.connect(r'file:C:/Game Dev/Emulators/re4dc-recovery/harvest.db?mode=ro', uri=True)
EV = r'C:/Flycast-Evidence/re4-dreamcast/'
pats = sys.argv[1:]
seen = {}
cache = {}
for lane, run, p, s in c.execute('select lane,run,path,sha from targets'):
    sj = os.path.join(EV, lane, run.replace(chr(92), '/'), 'stage.json')
    if sj not in cache:
        try: cache[sj] = json.load(open(sj))['fixture'].get('replace', {})
        except Exception: cache[sj] = {}
    src = cache[sj].get(p, '')
    if any(x in src for x in pats):
        seen.setdefault((src, s), []).append(lane + '/' + run)
for (src, s), runs in sorted(seen.items()):
    print(s, src, len(runs), runs[0])
