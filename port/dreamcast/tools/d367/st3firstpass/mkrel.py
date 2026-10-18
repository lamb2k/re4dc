# mkrel.py <room> <view> <src-variant> <new-variant>: replace st3/<room>.arc/.dar with rel33 outputs; check compact identities are on the disc.
import json,sys,os
R,V,S,N=sys.argv[1:5]
D='/root/probe/lanes-20261014/st3/fixtures/%s'%R
d=json.load(open('%s/cx-%s-%s-%s.armed.json'%(D,R,V,S)))
L='/root/probe/lanes-20261014/st3/rel33/rel-%s/st3'%R
for e in ('arc','dar'):
    d['replace']['st3/%s.%s'%(R,e)]=L+'/%s.%s'%(R,e)
rep=json.load(open('/root/probe/lanes-20261014/st3/rel33/compact-%s/compact-room-report.json'%R))
keys={s['key'] for s in rep['selected']}
have={os.path.basename(k)[:-7] for k in d['replace'] if k.startswith('dc/tex/')}
miss=sorted(keys-have)
print(R,'identities',len(keys),'not in fixture replace',len(miss),miss[:5])
d.setdefault('provenance',{})
if isinstance(d['provenance'],dict): d['provenance']['st3_rel33']='compact-room --compact-room-mips + room_smd release (castle release31 method)'
out='%s/cx-%s-%s-%s.armed.json'%(D,R,V,N)
assert not os.path.exists(out)
json.dump(d,open(out,'w'),indent=1)
print(out)
