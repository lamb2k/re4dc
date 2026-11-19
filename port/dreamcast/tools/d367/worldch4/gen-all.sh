#!/bin/bash
# gen-all.sh <Disc 2 tex.pak (WSL)> <Disc 1 release tree (WSL)> <base snd catalog.json (WSL)> [tag] [from-step]
#   (Git Bash on the Windows host; lane world-ch4 2026-11-02; castlegca26/gen-all.sh for chapter 4, inputs in env.sh)
# Steps: itemlib, objects (per room, WSL) + tex (per room, Windows python), itemtex, em (gen-em.sh), snd, final.
# from-step skips earlier steps (their work output is reused).
set -euo pipefail
PAK=${1:?Disc 2 tex.pak}; D1=${2:?Disc 1 tree}; CAT=${3:?base catalog}; TAG=${4:-20261102}; FROM=${5:-itemlib}
TW=/root/work/lanes/world-ch4/port/dreamcast/tools
H=$TW/d367/worldch4
WS=//wsl.localhost/Ubuntu-24.04
GI="C:/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso"
PI="C:/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso"
W() { MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root -- bash "$@"; }
eval "$(sed -n '/^W4_ROOMS=/p;/^W4_SPECS=/p;/^W4_CEM=/p;/^WK=/p' "$WS$H/env.sh")"
export W4_ROOMS W4_SPECS W4_CEM
S1=/root/re4data/private/c4gca-$TAG; S2=/root/re4data/private/pmc4gca-$TAG
on=0; at() { [ "$on" = 1 ] || [ "$FROM" = "$1" ] && on=1; [ "$on" = 1 ]; }
if at itemlib; then W "$H/step.sh" itemlib "$WK/itemlib" "$(echo $W4_ROOMS | tr ' ' ,)"; fi
if at objects; then
  for spec in $W4_SPECS; do
    IFS='|' read -r r etm pairs from <<< "$spec"
    W "$H/step.sh" objects "$r" "$etm" "$pairs" "$from" "$WK/obj/$r" "$WK/itemlib"
  done
fi
if at tex; then
  for spec in $W4_SPECS; do
    r=${spec%%|*}; O=$WK/obj/$r
    (cd "$WS$TW" && MSYS_NO_PATHCONV=1 py ps2_objects_tex.py --room "$r" --dar "$WS$O/i/$r.dar" --report "$WS$O/$r.json" \
      --out "$WS$O/x/$r.dar" --texdir "$WS$O/x/tex" --json "$WS$O/x/tex.json" --pak "$WS$PAK" --gc-room "$WS$WK/obj/gcroom/$r.arc" \
      --gc-iso "$GI" --ps2-iso "$PI" > "$WS$O/x/tex.log" 2>&1) || { echo "$r: tex step failed"; tail -5 "$WS$O/x/tex.log"; exit 1; }
    echo "$r $(tail -1 "$WS$O/x/tex.log")"
  done
fi
if at itemtex; then
  (cd "$WS$TW" && MSYS_NO_PATHCONV=1 py ps2_items_tex.py "$WS$WK/itemlib" > "$WS$WK/itemlib/tex.log" 2>&1) || { tail -5 "$WS$WK/itemlib/tex.log"; exit 1; }
  echo "items tex: $(tail -1 "$WS$WK/itemlib/tex.log")"
fi
if at em; then W "$H/gen-em.sh" "$WK" "$D1"; fi
if at snd; then W "$H/step.sh" snd "$WK/snd" "$WK" "$CAT"; fi
if at final; then
  W "$H/step.sh" clean "$S1" "$S2" || true
  MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root -- env W4_ROOMS="$W4_ROOMS" bash "$H/step.sh" final "$S1" "$S2" "$WK"
  W "$H/step.sh" seal "$S1" "$S2"
fi
