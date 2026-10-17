#!/bin/bash
# MEASURE ONLY (no disc use): resident heap-4 body of the island enemies with all motions streamed (a scratch copy of the
# tool with the enemy added to MOTION_SMALL; their FCV consumers are NOT audited). em39 --compact-effects: 3,711,840 ->
# 3,109,792 B (em36 / em32: no eligible effect sequences).
L=/root/probe/lanes-20261016/ch5found; P=$L/prepem
H=/root/probe/lanes-20261015/castle/prepem/empty-hot.json
S=/tmp/pem-scratch; rm -rf $S; mkdir -p $S/port/dreamcast/game/platform $S/config/G4BE08
cp -r $L/tree/port/dreamcast/tools $S/port/dreamcast/
cp $L/tree/port/dreamcast/game/Makefile $S/port/dreamcast/game/
cp $L/tree/port/dreamcast/game/platform/modules.cpp $S/port/dreamcast/game/platform/
ln -s $L/tree/config/G4BE08/modules $S/config/G4BE08/modules
ln -s $L/tree/tools $S/tools
sed -i "s/^MOTION_SMALL=('em21.drs','em23.drs','em2a.drs','em2b.drs')/MOTION_SMALL=('em21.drs','em23.drs','em2a.drs','em2b.drs','em36.drs','em39.drs','em32.drs')/" $S/port/dreamcast/tools/prepare_enemy_motions.py
cd $P
for E in "$@"; do
  rm -rf mst-$E
  python3 $S/port/dreamcast/tools/prepare_enemy_motions.py --source src/em/$E.drs --output mst-$E --hot-audit $H --diagnostic-incomplete-prefetch --textures tex-$E > mst-$E.log 2>&1 && echo "$E streamed: $(grep -a 'resident body' mst-$E.log | tail -1) mot $(ls mst-$E/mot | wc -l) $(du -sb mst-$E/mot | cut -f1) B" || { echo "$E streamed FAIL"; tail -2 mst-$E.log; }
done
