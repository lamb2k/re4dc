set -e
L=/root/probe/lanes-20261016/final16; TT=$L/tree/port/dreamcast/tools
cd $TT
python3 - <<'PY'
p='prepare_enemy_motions.py'; s=open(p).read()
a="ROUTE_OVL_MODULES=('em2b','em2f','em22','pl11','em1d','em1e','em1f','em36','em39','em3a','em32','em3d')"
if s.count(a)!=1: raise SystemExit(0)
s=s.replace(a,"# em31 (ROUTE_FINAL room overlay, lane final16): its static REL is stripped like the island overlays' (the motion table\n# binding needs the 64-byte retained descriptor: native_motion.cpp re4dc_motion_bind, bytes - rel == 64).\nROUTE_OVL_MODULES=('em2b','em2f','em22','pl11','em1d','em1e','em1f','em36','em39','em3a','em32','em3d','em31')")
open(p,'w').write(s)
PY
cd $L/prepem; rm -rf prepc-em31
python3 $TT/prepare_enemy_motions.py --source src/em/em31.drs --output prepc-em31 --hot-audit empty-hot.json --diagnostic-incomplete-prefetch --textures tex-em31 > prepc-em31.log 2>&1 || { tail -5 prepc-em31.log; exit 1; }
tail -c 300 prepc-em31.log; echo
python3 -c "
import struct;d=open('prepc-em31/em31.drs','rb').read()
print(len(d))
"
python3 - prepc-em31/motion-residency-report.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
print('resident_body',r['resident_body_bytes'],'hot_payload',r['hot_payload_bytes'],'cold_reserve',r['cold_reserve_bytes'],'entries',len(r['entries']))
PY
