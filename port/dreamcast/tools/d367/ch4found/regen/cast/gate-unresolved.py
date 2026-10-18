import json, glob
G='/root/probe/lanes-20261018/ch4regen/gatefix'
res=json.load(open(G+'/resolve.json')); un={p for p,v in res.items() if v is None}
for f in sorted(glob.glob(G+'/*/cx-*-g.armed.json')):
    fx=json.load(open(f))['replace']; u=[(k,p) for k,p in fx.items() if p in un]
    print(f.split('/')[-2], len(u), ' '.join(k for k,p in u)[:600])
print('---'); [print(p) for p in sorted(un)]
