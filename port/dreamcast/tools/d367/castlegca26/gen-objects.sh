#!/bin/bash
# gen-objects.sh <store (WSL path)> <pak (WSL path)> <room spec>...   (Git Bash on the Windows host; lane castle-gca-26 11-01)
# Castle room objects (Disc 2, data set cgca26) to PS2: per room spec "rNNN:ETM:PAIRS" (ETM = all | name,... | -;
# PAIRS = GC:PS2 room BIN pairs, comma separated, or -):
#   1. (WSL, step.sh objects) ps2_objects.py room on the castle content's st2/rNNN.dar (recipe D2_CASTLE_TREE): PS2
#      geometry, --uv-fold, --keep-larger (no-GameCube-assets rule: the PS2 model replaces the GC one even where larger);
#   2. (Windows python: numpy + PIL) ps2_objects_tex.py: PS2 pictures for every converted model (loose keys); <pak> is
#      the Disc 2 dc/tex.pak (pair packages are built only where the GC pair is in it);
#   3. (WSL, step.sh store) mkstore.py: STORE/st2/rNNN.dar + graft.json (changed members only) + provenance.tsv,
#      loose keys -> STORE/tex, reports -> STORE/reports.
set -euo pipefail
ST=${1:?store}; PAK=${2:?pak}; shift 2
CT=${D2_CASTLE_TREE:-/root/re4data/private/castle-d2-j-20261021}
SCR=${SCR:-/root/work/lanes/castle-gca-26-scratch/gen}
TW=${TW:-/root/work/lanes/castle-gca-26/port/dreamcast/tools}
WS=//wsl.localhost/Ubuntu-24.04
GI="C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso"
PI="C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso"
W() { MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root -- bash "$TW/d367/castlegca26/step.sh" "$@"; }
for spec in "$@"; do
  IFS=: read -r r etm pairs <<< "$spec"
  O=$SCR/$r
  W objects "$r" "$etm" "$pairs" "$O" "$CT"
  (cd "$WS$TW" && MSYS_NO_PATHCONV=1 py ps2_objects_tex.py --room "$r" --dar "$WS$O/$r.dar" --report "$WS$O/$r.json" \
    --out "$WS$O/x/$r.dar" --texdir "$WS$O/x/tex" --json "$WS$O/x/tex.json" --pak "$WS$PAK" --gc-room "$WS$SCR/gcroom/$r.arc" \
    --gc-iso "$GI" --ps2-iso "$PI" > "$WS$O/x/tex.log" 2>&1) || { echo "$r: tex step failed"; tail -5 "$WS$O/x/tex.log"; exit 1; }
  tail -1 "$WS$O/x/tex.log"
  W store "$ST" "$r" "$O" "$CT"
done
