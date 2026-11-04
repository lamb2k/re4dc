#!/bin/bash
# em14p (lane castlebudget 11-04): em14 (castle zealots, r20f) with motion streamed cold + PS2 motion, PS2 BINs.
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); D=$(cd "$H/.." && pwd); T=$(cd "$D/.." && pwd)
W=${W:-/root/probe/lanes/castlebudget-w}; mkdir -p $W; cd $W
ISO="/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso"
I=/root/probe/lanes/ps2cast/inputs; REL=/root/re4data/private/cgca26-20261101/em/em14.drs
D1=/root/probe/playreads/d1/tree; CT=/root/re4data/private/castle-d2-j-20261021
HOT=${HOT:-hot-empty.json}
printf '{"source_complete": false, "profile": "castlebudget 11-04: em14 all-cold first pass", "union": {"source_arc_indices": []}}\n' > hot-empty.json
rm -rf "${W:?}/p14"; mkdir -p p14/src/em; cd p14
cp $I/em14.drs src/em/em14.drs; echo em/em14.drs > files.txt
python3 $T/prepare_native_ui.py src files.txt tex-em14 > tex.log 2>&1 || { tail tex.log; exit 1; }
python3 $T/prepare_enemy_motions.py --source src/em/em14.drs --output prep ${NOTEX:+}${NOTEX:---textures tex-em14} --hot-audit ../$HOT --diagnostic-incomplete-prefetch > prep.log 2>&1 || { tail -20 prep.log; exit 1; }
tail -1 prep.log
python3 $D/castlebudget/bankcopy.py "$REL" prep/em14.drs em14-a.drs
mkdir -p cast/dc; cp -al "$D1/dc/native" cast/dc/native; cp -a "$CT/dc/native/." cast/dc/native/
python3 $D/ps2cast/ps2_ganado_bins.py build --release em14-a.drs --gc $I/em14.drs --ps2 $I/em14.dat --cast-tree cast --out em14-b.drs --json bins.json > bins.log 2>&1 || { tail bins.log; exit 1; }
grep TOTAL bins.log
python3 $D/motion/ps2_motion_prepared.py rewrite em14-b.drs "$ISO" em14.dat m --mot-dir "$CT/dc/mot" | tail -2
o=$(ls m/em/*); python3 $D/motion/ps2_motion_prepared.py verify "$o" em14-b.drs "$ISO" em14.dat m/dc/mot "$CT/dc/mot" | tail -1
ls -la $o; ls m/dc/mot | wc -l; ls tex-em14 | wc -l
