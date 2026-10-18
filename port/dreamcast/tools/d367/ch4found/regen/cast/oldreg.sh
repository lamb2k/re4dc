#!/bin/bash
# ch4regen: the pre-08:38Z versions of r211/r214/r218/r227 (em14-09p / em1c-09g, before the flag-2 accessory rename) for ch3.
set -euo pipefail
C=/root/probe/lanes-20261016/cast16; W=$C/conv4; OUT=/root/probe/lanes-20261018/ch4regen/c16old
M=$C/c4m/port/dreamcast/tools/d367/model-registry
mkdir -p $OUT/spec
python3 - $M $OUT/spec $W <<'P'
import json,sys
M,O,W=sys.argv[1:4]
ren={'zealot-em14-09q':'zealot-em14-09p','zealot-em1c-09h':'zealot-em1c-09g'}
for r in ('211','214','218','227'):
    s=json.load(open(f'{M}/ps2-ch4-r{r}.json'))
    s['cast_dir']=W+'/regcast-old'
    for d in s['descriptors']:
        if d['name'] in ren:
            new=ren[d['name']]; d['name']=new
            d['mask_runs']={k:f'{W}/mask-{new}-s{k}' for k in d.get('mask_runs',{}) if k!='22'}
    for v in s['room_packages'].values(): v['descriptors']=[ren.get(x,x) for x in v['descriptors']]
    json.dump(s,open(f'{O}/ps2-ch4-r{r}.json','w',newline='\n'),indent=1)
P
for r in 211 214 218 227; do
  for v in a b c; do
    o=$OUT/$v/reg-$r; rm -rf "${o:?}"; mkdir -p $OUT/$v
    case $v in
      a) T=/root/probe/lanes-20261016/ch4found/tree; X="--pack-bones 64 $( [ $r = 227 ] && echo --roles5 || true)"; cd $C/tree;;
      b) T=$C/c4m; X="--pack-bones 96 --roles5"; cd $C/c4m;;
      c) T=/root/probe/lanes-20261016/ch4found/tree; X="--pack-bones 96 --roles5"; cd $C/tree;;
    esac
    python3 port/dreamcast/tools/d367/model_registry.py $OUT/spec/ps2-ch4-r$r.json $o --tree $T --package-room $r --pool --wide-identity $X > $o.log 2>&1 \
      && echo "$r $v $(sha256sum $o/package/r$r/registry.re4nmr | cut -c1-8)" || echo "$r $v FAIL $(tail -1 $o.log | cut -c1-120)"
  done
done
