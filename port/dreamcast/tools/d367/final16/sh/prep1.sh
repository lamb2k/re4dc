set -e
L=/root/probe/lanes-20261016/final16; TT=$L/tree/port/dreamcast/tools
python3 "/mnt/c/Game Dev/Emulators/final16-20261016/py/ed2.py"
P=$L/prepem; mkdir -p $P/src/em; cd $P
[ -f src/em/em31.drs ] || cp /root/probe/lanes-20261016/stress16b/em31/em-src/em/em31.drs src/em/em31.drs
[ -d tex-em31 ] || cp -r /root/probe/lanes-20261016/stress16b/em31/tex-em31 tex-em31
sha256sum src/em/em31.drs | cut -c1-16; ls tex-em31 | wc -l
echo '{"source_complete": false, "union": {"source_arc_indices": []}}' > empty-hot.json
rm -rf prepc-em31
python3 $TT/prepare_enemy_motions.py --source src/em/em31.drs --output prepc-em31 --hot-audit empty-hot.json --diagnostic-incomplete-prefetch --textures tex-em31 > prepc-em31.log 2>&1 || { tail -5 prepc-em31.log; exit 1; }
tail -c 400 prepc-em31.log; echo
python3 - prepc-em31/motion-residency-report.json <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
print('resident_body',r['resident_body_bytes'],'hot_payload',r['hot_payload_bytes'],'cold_reserve',r['cold_reserve_bytes'],'entries',len(r['entries']),'hot',sum(1 for e in r['entries'] if e['hot']))
PY
ls prepc-em31/mot | wc -l; du -sb prepc-em31/mot | cut -f1
