#!/bin/bash
# ch4regen: dc/tex.pak (tex-z9, target 5ed4ba5a) once ch3 delivers tex-c34b.pak (7398aaaa).
# usage: c4r-texpak.sh <tex-c34b.pak>
# Chain: vqp2.sh (vq16c-texpak.sh, keys = committed vram/vq16-c42.txt; loose keys from the replayed emtex4 / cx-fixtures
# dirs) -> fc3f265e -> st8.sh statue merge (codex r226 tex, statue/keys.txt) -> r21a merge (codex r21a tex) -> tex-z9.
set -euo pipefail
BASE=${1:?tex-c34b.pak}
L=/root/probe/lanes-20261018/ch4regen; F=$L/ch4found; D=$L/tree/port/dreamcast/tools/d367
[ "$(sha256sum "$BASE" | cut -c1-8)" = 7398aaaa ] || { echo "base is not 7398aaaa"; exit 1; }
O=$L/texpak; rm -rf "${O:?}"; mkdir -p $O
grep -v '^#' $D/vram/vq16-c42.txt | awk '{print $1}' > $O/keys.txt
python3 - $BASE $O/fix.json $O/keys.txt <<'P'
import json, struct, sys, glob, os
base=open(sys.argv[1],'rb').read(); magic,ver,count,ioff,doff=struct.unpack_from('<8s4I',base,0)
idx={'%08x-%08x'%struct.unpack_from('<2I',base,ioff+16*i) for i in range(count)}
rep={'dc/tex.pak':sys.argv[1]}
roots=['/root/probe/lanes-20261018/ch4regen/ch4found/emtex4','/root/probe/codex-cx-fixtures-20261013/output']
for k in open(sys.argv[3]).read().split():
    if k in idx: continue
    hit=[p for r in roots for p in glob.glob(f'{r}/**/{k}.re4tex',recursive=True)]
    if not hit: print('LOOSE MISSING',k); continue
    rep[f'dc/tex/{k[0]}/{k}.re4tex']=hit[0]
json.dump({'replace':rep},open(sys.argv[2],'w'),indent=1); print('loose',len(rep)-1)
P
bash $D/vram/vq16c-texpak.sh $O/fix.json $O/keys.txt $O/vq-c42 | tail -1
X=$O/statue; mkdir -p $X/src
python3 - $F/compact4/r226/compact-room-report.json $F/compact5/r226/compact-room-report.json $F/statue/keys.txt <<'P'
import json,sys
# the 10-16 19:45 compact4/r226 (84 keys) predates the r226 #28 statue TPL patch; the replayed compact4 already has it,
# so the 10-17 statue set = compact5's #28 keys not selected by another context (st6.sh printed 'new 10').
sel=json.load(open(sys.argv[2]))['selected']
ka={s['key'] for s in sel if not s['context'].startswith('st2/r226.arc#28')}
new=[s for s in sel if s['key'] not in ka]
open(sys.argv[3],'w').write(''.join(s['key']+'\n' for s in new)); print('statue keys',len(new))
P
A=/root/probe/codex-cx-fixtures-20261013/output/r226/ancillary/tex
for k in $(cat $F/statue/keys.txt); do cp $A/$k.re4tex $X/src/; done
python3 $D/texpack.py $X/src $X/statue.pak | tail -1
python3 $D/tex_merge.py $O/vq-c42/tex-vq16c.pak $X/tex-st.pak $X/statue.pak | tail -1
A=/root/probe/codex-cx-fixtures-20261013/output/r21a/ancillary/tex; [ -d $A ] || A=$L/cxextra/r21a/ancillary/tex; mkdir -p $O/src21a
python3 - $X/tex-st.pak $F/compact4/r21a/compact-room-report.json $O/r21a-miss.txt <<'P'
import struct,json,sys
pak=open(sys.argv[1],'rb').read(); magic,ver,count,ioff,doff=struct.unpack_from('<8s4I',pak,0)
idx={'%08x-%08x'%struct.unpack_from('<2I',pak,ioff+16*i) for i in range(count)}
keys=sorted({s['key'] for s in json.load(open(sys.argv[2]))['selected']})
open(sys.argv[3],'w').write('\n'.join(k for k in keys if k not in idx)+'\n')
P
for k in $(cat $O/r21a-miss.txt); do cp $A/$k.re4tex $O/src21a/; done
python3 $D/texpack.py $O/src21a $O/r21a.pak | tail -1
python3 $D/tex_merge.py $X/tex-st.pak $O/tex-z9.pak $O/r21a.pak | tail -1
sha256sum $O/vq-c42/tex-vq16c.pak $O/tex-z9.pak | cut -c1-16
