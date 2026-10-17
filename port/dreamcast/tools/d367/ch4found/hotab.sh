set -e
L=/root/probe/lanes-20261016/ch4found; T=$L/tree/port/dreamcast/tools; W=/root/probe/lanes-20261010/r117/rooms
cd $L/hot11
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
for t in a b; do rm -rf prep-em11$t; python3 $T/prepare_enemy_motions.py --source $W/em-src/em/em11.drs --output prep-em11$t --hot-audit em11-ch4$t.json --diagnostic-incomplete-prefetch --textures $W/tex-em > prep-em11$t.log 2>&1 || { tail prep-em11$t.log; exit 1; }; tail -1 prep-em11$t.log; done
cd $L/snd
for t in a b; do sed "s#hot11/prep-em11h/em11.drs#hot11/prep-em11$t/em11.drs#; s/c4h/c4$t/g" /mnt/c/tmp/ch4/snd4h.sh > /tmp/snd4$t.sh; bash /tmp/snd4$t.sh > snd4$t.out 2>&1; tail -4 snd4$t.out; done
