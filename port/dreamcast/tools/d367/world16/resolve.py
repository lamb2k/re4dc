import importlib.util, json, hashlib, os, sys
spec = importlib.util.spec_from_file_location('t11fix', sys.argv[1]); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
rooms = (sys.argv[3] if len(sys.argv)>3 else 'r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b').split()
res = {r: {} for r in rooms}; src = {r: {} for r in rooms}
extra = json.load(open(sys.argv[4]))['replace'] if len(sys.argv)>4 else {}
for key, items in [(k, m.DATA[k]) for k in m.T15_DATA.split(',')] + [('ch2', extra)]:
    for dst, path in items.items():
        if not isinstance(dst, str) or not dst.startswith('dc/native/'): continue
        r = dst.split('/')[2]; f = dst.split('/')[3]
        if r in res and (f.startswith('ps2-world') or f.startswith('ps2-wv')):
            res[r][f] = path; src[r][f] = key
out = {}
for r in rooms:
    out[r] = {}
    for f, p in sorted(res[r].items()):
        b = open(p, 'rb').read()
        out[r][f] = dict(path=p, set=src[r][f], bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
json.dump(dict(T15_DATA=m.T15_DATA, rooms=out), open(sys.argv[2], 'w'), indent=1)
for r in rooms:
    print(r, ' '.join('%s:%s:%d' % (f, v['set'], v['bytes']) for f, v in out[r].items()))
