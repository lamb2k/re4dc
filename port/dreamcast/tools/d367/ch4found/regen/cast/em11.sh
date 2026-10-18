#!/bin/bash
# ch4regen: aica-c4c em11 (target 9c1e2cae). Chain: r117 prep11.sh (10-10, empty hot) report -> hot.sh motion_hot
# (land/t17-pak17-motion, ch4found z1 Flycast logs) -> hotab.sh trim b -> prep-em11b -> q38.sh prep-em11c (compact)
# -> splice (prep-em11b header, unconverted) -> aica_search4k.py (castle layout) against the target sha.
set -euo pipefail
L=/root/probe/lanes-20261018/ch4regen; H=$L/ch4found/hot11; T=$L/tree/port/dreamcast/tools
SRC=/root/probe/lanes/ps2cast/inputs/em11.drs
TEX=$L/ch4found/emtex4/tex-em11
mkdir -p $H; cd $H
echo '{"source_complete": false, "profile": "diagnostic: no hot set (every streamed clip loads on first use)", "union": {"source_arc_indices": []}}' > em11-hot.json
rm -rf r117-prep-em11; python3 $T/prepare_enemy_motions.py --source $SRC --output r117-prep-em11 --hot-audit em11-hot.json --diagnostic-incomplete-prefetch --textures $TEX > r117-prep-em11.log 2>&1 || { tail -3 r117-prep-em11.log; exit 1; }
git -C $L/tree show origin/land/t17-pak17-motion:port/dreamcast/tools/d367/motion/motion_hot.py > motion_hot.py
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-cxc4zmW/scenarios
python3 motion_hot.py r117-prep-em11/motion-residency-report.json em11-ch4.json $E/cx-r226-walk-z1/capture/run-output.txt $E/cx-r222-walk-z1/capture/run-output.txt $E/cx-r212-walk-z1/capture/run-output.txt --profile "run-derived hot set: chapter 4 em11 (r226 dec3 kill rig + B3/B5, r222 / r212 kill rigs; ch4found16 z1, Flycast, MOTION_COLD_POOL_CASTLE=131072)" | tail -1
python3 - <<'P'
import json
d=json.load(open('em11-ch4.json'))
for tag,lo in (('a',2),('b',3)):
    c={k:v for k,v in d['clips'].items() if v['misses']>=lo}
    e=dict(d); e['clips']=c; e['union']={'source_arc_indices':sorted(int(k) for k in c)}
    e['hot_payload_bytes']=sum(v['bytes'] for v in c.values())
    e['profile']=d['profile']+'; trimmed to clips that missed >= %d times (the slab-cycling set)'%lo
    json.dump(e,open('em11-ch4%s.json'%tag,'w'),indent=1); print(tag,e['union'],e['hot_payload_bytes'])
P
rm -rf prep-em11b; python3 $T/prepare_enemy_motions.py --source $SRC --output prep-em11b --hot-audit em11-ch4b.json --diagnostic-incomplete-prefetch --textures $TEX > prep-em11b.log 2>&1 || { tail -3 prep-em11b.log; exit 1; }
rm -rf prep-em11c; python3 $T/prepare_enemy_motions.py --source $SRC --output prep-em11c --hot-audit em11-ch4b.json --diagnostic-incomplete-prefetch --textures $TEX --compact-effects > prep-em11c.log 2>&1 || { tail -3 prep-em11c.log; exit 1; }
python3 - <<'P'
import struct
def rec(d): return [struct.unpack_from('<8I',d,0x20+32*i) for i in range(2)]
a=open('prep-em11b/em11.drs','rb').read(); c=open('prep-em11c/em11.drs','rb').read()
ra,rc=rec(a)[0],rec(c)[0]
assert ra[3]+ra[1]==len(a)
body=c[rc[3]:rc[3]+rc[1]]; out=bytearray(a[:ra[3]])+body
struct.pack_into('<I',out,0x20+4,len(body))
open('/root/probe/lanes-20261018/ch4regen/aica-cand/em11.drs','wb').write(out); print('candidate',len(out))
P
O=$L/ch4found/snd/aica-c4c/em/em11.drs; SHA=9c1e2cae76a5f03050665f36c583df35f24d840893f7e809bc2cb4b28338b0f5
( cd /tmp && nice python3 /root/probe/lanes-20261018/ch3regen/aica_search4k.py $T $L/aica-cand/em11.drs $SHA $L/aica-cache $O --layout 127936,253856,72544,264576,0,0,0,32736,1004192 2>&1 | tail -2 )
[ -e $O ] && sha256sum $O | cut -c1-16
