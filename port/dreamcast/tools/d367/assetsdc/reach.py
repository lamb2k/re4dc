#!/usr/bin/env python3
# assets-dc part A: classify every gc/unknown GC-ASSET catalog row by static reachability on the shipped route.
# reach classes:
#   room-loaded      : payload lives in a route room's archive (st1/rXXX.*) -> loaded at room entry
#   room-offroute    : room archive not on the disc's route list
#   actor-route      : em/<id>.drs where <id> is spawned/used by a route room (member census of the disc's ESL/EVD refs)
#   actor-unref      : em/<id>.drs with no route reference found
#   common           : ss/, op/, etc/, font, dc/ shared packs (loaded globally)
import json, sys, re, collections, os
cat, tree, routef, out = sys.argv[1:5]
rows = json.load(open(cat))['entries']
route = set(open(routef).read().split())
# actor ids referenced per route room: grep the room's .esl/.evd/.arc bytes for "emXX"/"plXX"/"wepXX" strings
ref = collections.defaultdict(set)
for d in ('st1', 'st2', 'evd', 'event'):
    p = os.path.join(tree, d)
    if not os.path.isdir(p): continue
    for f in os.listdir(p):
        m = re.match(r'(r[0-9a-f]{3})', f.lower())
        if not m or m.group(1) not in route: continue
        b = open(os.path.join(p, f), 'rb').read()
        for x in set(re.findall(rb'(em[0-9a-f]{2}|pl[0-9a-f]{2}|wep[0-9a-f]{2})', b.lower())):
            ref[x.decode()].add(m.group(1))
res = collections.Counter(); byt = collections.Counter(); ex = {}
for r in rows:
    if r['provenance'] not in ('gc', 'unknown'): continue
    s = r['source'].lower()
    m = re.match(r'st[12]/(r[0-9a-f]{3})', s); a = re.match(r'em/((?:em|pl|wep)[0-9a-f]{2})\.', s)
    if m: rc = 'room-loaded' if m.group(1) in route else 'room-offroute'
    elif a: rc = 'actor-route' if a.group(1) in ref or a.group(1) in ('pl00',) else 'actor-unref'
    elif s.startswith('dc/tex.pak'): rc = 'texpack'
    elif s.startswith('runtime'): rc = 'runtime-harvest(seen drawn)'
    else: rc = 'common:' + s.split('/')[0]
    k = (r['kind'], r['provenance'], rc); res[k] += 1
    ex.setdefault(k, r['source'])
with open(out, 'w') as o:
    o.write('kind\tprov\treach\trows\texample\n')
    for k, v in sorted(res.items(), key=lambda x: -x[1]):
        o.write('%s\t%s\t%s\t%d\t%s\n' % (k + (v, ex[k])))
        print('%-12s %-8s %-28s %5d  %s' % (k + (v, ex[k])))
print('total', sum(res.values()))
