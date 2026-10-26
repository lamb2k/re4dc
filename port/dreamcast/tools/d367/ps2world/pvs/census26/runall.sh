#!/bin/bash
# vis-census26 driver (Git Bash): prep (Windows py) -> cells (WSL pvs_cast) -> cams -> ceil -> eval, every room
cd "/c/Flycast-Evidence/re4-dreamcast/vis-census26-20261026"
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/3eafc4fe-ad61-4030-8af6-7352db985ae8/scratchpad
for r in $(ls pkg); do (python tools/pvs/pvs_prep_let.py pkg/$r ${r#r} work/$r > prep-$r.log 2>&1) & done; wait
for r in $(ls pkg); do
  rm -f work/$r/cells.bin work/$r/ceil.bin work/$r/census.json
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash $S/build1.sh $r 14 >/dev/null
  python tools/pvs/census.py cams work/$r > cams-$r.log 2>&1
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash $S/ceil1.sh $r 14 >/dev/null
  python tools/pvs/census.py eval work/$r 2>&1 | tail -1
done
