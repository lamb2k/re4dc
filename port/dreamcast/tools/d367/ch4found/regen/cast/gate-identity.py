# ch4regen gate 1: for the latest ch4found run per room, every fixture replace path must exist now with the sha the
# recorded staged payload had (payload-manifest.json). Writes the restored fixture to $OUT/<room>/.
import json, glob, os, sys, hashlib
E='/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016'
OUT='/root/probe/lanes-20261018/ch4regen/gatefix'
cache={}
def sha(p):
    if p not in cache:
        h=hashlib.sha256()
        with open(p,'rb') as f:
            for b in iter(lambda:f.read(1<<22),b''): h.update(b)
        cache[p]=h.hexdigest()
    return cache[p]
best={}
for s in glob.glob(E+'/h-*c4*/scenarios/cx-r2*'):
    st=s+'/stage.json'
    if not os.path.exists(st) or not os.path.exists(s+'/payload-manifest.json'): continue
    r=os.path.basename(s).split('-')[1]; t=os.path.getmtime(st)
    if r not in best or t>best[r][0]: best[r]=(t,s)
tot={}
for r in sorted(best):
    s=best[r][1]; d=json.load(open(s+'/stage.json')); pm=json.load(open(s+'/payload-manifest.json'))
    fx=d['fixture']; ok=miss=bad=0; probs=[]
    for k,p in fx['replace'].items():
        want=pm.get(k,{}).get('sha256')
        if not os.path.exists(p): miss+=1; probs.append(('MISS',k,p)); continue
        if want and sha(p)!=want: bad+=1; probs.append(('SHA',k,p)); continue
        ok+=1
    os.makedirs(f'{OUT}/{r}',exist_ok=True)
    json.dump(fx,open(f'{OUT}/{r}/cx-{r}-g.armed.json','w'),indent=1,sort_keys=True)
    print(r, os.path.relpath(s,E), d['arm'], 'ok',ok,'missing',miss,'sha',bad, flush=True)
    for x in probs[:8]: print('   ',*x)
