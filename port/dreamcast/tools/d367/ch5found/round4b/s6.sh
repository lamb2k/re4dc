#!/bin/bash
# STRICT pair data: prepa = every em36 clip hot (the whole motion set resident in the motion cache: the reference,
# no cold reads) vs preph = the r307 hot list (9 hot, 63 cold). Fixtures: trace arm cx5srT, warp m6 (release + kill).
set -e
L=/root/probe/lanes-20261016/ch5found
python3 - <<'PY'
import json
r=json.load(open('/root/probe/lanes-20261016/ch5found/prepem/prepc-em36/motion-residency-report.json'))
a=sorted({x for e in r['entries'] for x in e['source_arc_indices']})
json.dump({'source_complete':False,'profile':'reference: every streamed clip hot (STRICT off arm)','union':{'source_arc_indices':a}},open('/root/probe/lanes-20261016/ch5found/prepem/em36-allhot.json','w'))
print('allhot',len(a))
PY
bash /mnt/c/tmp/ch5b/prepc.sh prepa $L/prepem/em36-allhot.json em36
bash /mnt/c/tmp/ch5b/h.sh cx5srT
bash /mnt/c/tmp/ch5b/mk.sh cx5srT s6a $L/fixtures/wp2/cx-r307-m6.txt prepa
bash /mnt/c/tmp/ch5b/mk.sh cx5srT s6h $L/fixtures/wp2/cx-r307-m6.txt preph
bash /mnt/c/tmp/ch5b/mk.sh cx5mmW m6h $L/fixtures/wp2/cx-r307-m6.txt preph
bash /root/probe/lanes-20261016/ch5found/tree/port/dreamcast/tools/d367/trace_lock.sh --status 2>&1 | tail -3
