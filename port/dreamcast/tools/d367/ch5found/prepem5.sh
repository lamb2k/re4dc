#!/bin/bash
# island enemy archives (GC data, textures-only + static REL stripped against the route overlays), lane ch5found16 round 3
set -e
L=/root/probe/lanes-20261016/ch5found; P=$L/prepem; TT=$L/tree/port/dreamcast/tools
S=/root/probe/lanes-20261014/st3/deps2/source
mkdir -p $P/src/em; cd $P
for E in "$@"; do
  ln -sf $S/em/$E.drs src/em/$E.drs
  echo em/$E.drs > $E-tex.manifest
  [ -d tex-$E ] || python3 $TT/prepare_native_ui.py $P/src $P/$E-tex.manifest $P/tex-$E > tex-$E.log 2>&1; tail -1 tex-$E.log | cut -c1-200
  rm -rf prep-$E
  python3 $TT/prepare_enemy_motions.py --source src/em/$E.drs --output prep-$E --keep-motion-resident --textures tex-$E > prep-$E.log 2>&1 || { tail -5 prep-$E.log; continue; }
  tail -2 prep-$E.log | cut -c1-250
  echo "$E: GC $(stat -L -c %s src/em/$E.drs) -> $(stat -c %s prep-$E/$E.drs 2>/dev/null) B; textures $(ls tex-$E | wc -l) files $(du -sb tex-$E | cut -f1) B"
done
