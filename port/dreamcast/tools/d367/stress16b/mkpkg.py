# mkpkg.py: the stress disc fixture (pkg-s16brW.json) from test 16's (pkg-t16rcrP.json): this build's overlays,
# em31 (overlay, prepared archive, its 45 GC texture keys), the r119 Saddler registry package and its two PS2 atlases.
import json, os, glob
S='/root/probe/lanes-20261016/stress16b'
O='/root/probe/lanes/route/out-s16brW'
d=json.load(open('/root/probe/lanes-20261016/t16rc/fix/pkg-t16rcrP.json'))
r=d['replace']
for m in ('em22','em2b','em2f','pl0f','pl11','sscrn','em31'):
    r['dc/%s.ovl'%m]=O+'/%s.ovl'%m
r['em/em31.drs']=S+'/em31/prep-pose/em31.drs'
r['dc/native/r119/registry.re4nmr']=S+'/reg/reg-r119/package/r119/registry.re4nmr'
n=0
for f in sorted(glob.glob(S+'/em31/tex-em31/*.re4tex')+glob.glob(S+'/reg/reg-r119/tex/*.re4tex')):
    b=os.path.basename(f); r['dc/tex/%s/%s'%(b[0],b)]=f; n+=1
for k,v in r.items():
    assert os.path.exists(v), (k,v)
d['remove']=[x for x in d['remove'] if x not in r]
d['provenance']['stress16b']='Saddler stress disc (NOT THE GAME): test 16 data + em31 + r119 Saddler registry; %d loose textures'%n
json.dump(d,open(S+'/fix/pkg-s16brW.json','w'),indent=1,sort_keys=True)
print('ok textures',n,'replace',len(r))
