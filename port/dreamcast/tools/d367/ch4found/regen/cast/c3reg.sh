#!/bin/bash
# ch4regen: cast16 conv3 castle registries r209/r20c/r20d/r20f (c16r3.sh, 10-16 22:0xZ). Spec = c16r3 template
# (generated, "g") and the committed specs at 9b4cb31f / dd9e7fe1; trees t9b4 / tdd9. Targets: b1afcad5 3144a2d8 9988d452 315c0449.
set -euo pipefail
C=/root/probe/lanes-20261016/cast16; W=$C/conv3; OUT=/root/probe/lanes-20261018/ch4regen/c16c3
mkdir -p $OUT/spec-g
python3 - $W $OUT/spec-g <<'P'
import json,glob,os,sys
W,O=sys.argv[1:3]
for a,rooms in (('em14',['20f']),('em19',['20d']),('em1a',['209']),('em1b',['201','20c'])):
    ds=[]
    for d in sorted(glob.glob(f'{W}/zealot-{a}-0?p')):
        if not os.path.isdir(d+'/runtime'): continue
        n=os.path.basename(d); t=n.split('-')[2][:2]
        ds.append(dict(name=n,archive=a,model_id='0x'+a[2:],source_types=[int(t,16)],
            module=f'src/{a}/{a}_set.cpp {a.capitalize()}Set type {int(t,16)} + em10ModelInit / em10HeadSet / em10HandSet / em10SetAccesory',
            partial_sections=True,pool=True,source_drops=['bump'],
            mask_runs={'2':f'{W}/mask-{a}-06-extra','5':f'{W}/mask-{a}-06-s5','6':f'{W}/mask-{a}-06-s6'} if t=='06' else {'13':f'{W}/mask-{a}-{t}-hood','16':f'{W}/mask-{a}-{t}-acc1','20':f'{W}/mask-{a}-{t}-acc5'}))
    s=dict(registry=f'ps2-ch3-{a}p',about=f'lane cast16 (2026-10-16): castle Zealot {a} types {[d["source_types"][0] for d in ds]} as POOL descriptors (zealot-em11-07p layout, own archive). Render only.',
        cast_dir=f'{W}/regcast-{a}',revision_overlay='ps2-overlay',level='conservative',archive_audit='source/archive-audit.json',
        lighting='lit preset (normals kept); the runtime decides flat vs source lighting',descriptors=ds,
        room_packages={r:dict(descriptors=[d['name'] for d in ds],evidence=f'ch3found16 census: r{r} {a} plan G declined (GC)') for r in rooms})
    json.dump(s,open(f'{O}/ps2-ch3-{a}p.json','w',newline='\n'),indent=1)
P
for x in em14:20f em19:20d em1a:209 em1b:20c; do a=${x%%:*}; r=${x##*:}
  for t in t9b4 tdd9; do for sp in g $t; do
    if [ $sp = g ]; then f=$OUT/spec-g/ps2-ch3-${a}p.json; else f=$C/$t/port/dreamcast/tools/d367/model-registry/ps2-ch3-${a}p.json; fi
    [ -f $f ] || { echo "$r $t $sp nospec"; continue; }
    o=$OUT/$t-$sp/reg-$r; rm -rf "${o:?}"; mkdir -p $OUT/$t-$sp; cd $C/$t
    python3 port/dreamcast/tools/d367/model_registry.py $f $o --tree $C/$t --package-room $r --pool --wide-identity --pack-bones 96 > $o.log 2>&1 \
      && echo "$r $t $sp $(sha256sum $o/package/r$r/registry.re4nmr | cut -c1-8)" || echo "$r $t $sp FAIL $(tail -1 $o.log | cut -c1-100)"
  done; done
done
