set -e
L=/root/probe/lanes-20261016/ch4found; T=$L/tree/port/dreamcast/tools; W=/root/probe/lanes-20261010/r117/rooms
cd $L/hot11; rm -rf prep-em11h
python3 $T/prepare_enemy_motions.py --source $W/em-src/em/em11.drs --output prep-em11h --hot-audit em11-ch4.json --diagnostic-incomplete-prefetch --textures $W/tex-em > prep-em11h.log 2>&1 || { tail -20 prep-em11h.log; exit 1; }
tail -3 prep-em11h.log
python3 -c "
import json;r=json.load(open('prep-em11h/motion-residency-report.json'));print('resident',r['resident_body_bytes'],'hot',r['hot_payload_bytes'],'cold_reserve',r['cold_reserve_bytes'],'hot entries',sum(1 for e in r['entries'] if e['hot']),'entries',len(r['entries']))"
ls prep-em11h/mot | wc -l; ls -la prep-em11h/em11.drs
