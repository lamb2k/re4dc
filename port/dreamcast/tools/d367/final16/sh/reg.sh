set -e
L=/root/probe/lanes-20261016/final16; T=$L/tree/port/dreamcast/tools/d367
python3 - <<'PY'
import json
p='/root/probe/lanes-20261016/final16/tree/port/dreamcast/tools/d367/model-registry/'
d=json.load(open(p+'stress-r119-saddler.json'))
d['registry']='final-r332-saddler'
d['about']=("lane final16 (2026-10-16): Saddler's final form (em31) in his own room r332 (ROUTE_FINAL): PS2 body + head "
 "(ps2_cast.py saddler-em31-00) and tentacle (saddler-em31-01) from lane stress16b's casts, full meshes only (stress16b: "
 "the gameplay levels save ~2.8 of 9.9 Flycast ms, so no level pick). Package: model_registry.py --stress-saddler (the "
 "1 MiB / 256 part fact ceilings; ROUTE_FINAL's RE4DC_SADDLER_NMR). source_drops bump / mask = SADDLER_MASK_OPAQUE "
 "(visible approximation, default off).")
d['descriptors']=[x for x in d['descriptors'] if 'lod_of' not in x]
d['room_packages']={'332':{'descriptors':['saddler-em31-00','saddler-em31-01'],'evidence':'final16: r332, the final boss room (list 0xA8 body / 0xA9 tentacle)'}}
json.dump(d,open(p+'final-r332-saddler.json','w'),indent=1)
PY
W=$L/reg; mkdir -p $W; rm -rf $W/reg-r332
python3 $T/model_registry.py $T/model-registry/final-r332-saddler.json $W/reg-r332 --package-room 332 --pack-bones 96 --wide-identity --pool --stress-saddler > $W/reg-r332.log 2>&1 || { tail -8 $W/reg-r332.log; exit 1; }
python3 - $W/reg-r332.log <<'PY'
import json,sys
t=open(sys.argv[1]).read(); r=json.loads(t[t.index('{'):])
for x in r['runtime']: print(x)
print(r['package'])
PY
find $W/reg-r332 -name "*.re4nmr" -exec ls -la {} \; ; ls $W/reg-r332/tex | wc -l; du -sb $W/reg-r332/tex | cut -f1
