#!/bin/bash
# step.sh <step> ...   (WSL; lane world-ch32 (copy of castlegca26/step.sh, room/enemy lists from ROOMS / SNDEM); called by gen-all.sh, see there)
#   objects <room> <etm|-> <pairs|-> <etm-from|empty:names|-> <outdir> <castle tree> <item lib>
#           ps2_objects.py room (PS2 geometry, --uv-fold --keep-larger) then ps2_items.py pack (PS2 item models + debris
#           models + their pictures in place) -> <outdir>/i/<room>.dar; the tex step (Windows) reads it
#   itemlib <lib> <rooms,...>   ps2_items.py convert for the castle rooms (items + breakables)
#   snd <scratch> <work> <base catalog.json>   ps2_audio.py banks on the motion-final room archives + em19 / em1a
#   final <cgca26 store> <pmcgca26 store> <work>   mkfinal.py
#   clean <store>...   seal <store>...
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); TW=$(cd "$H/../.." && pwd)
REASON="no-GameCube-assets rule (user 10-23; Test 26 castle convert 11-01): the PS2 object replaces the GC one"
ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
case "$1" in
  objects)
    r=$2; etm=$3; pairs=$4; from=$5; O=${6:?}; CT=${7:?}; L=${8:?}
    rm -rf "${O:?}"; mkdir -p "$O/i" "$O/x/tex" "$O/../gcroom"
    cd "$TW"
    [ -s "$O/../gcroom/$r.arc" ] || python3 "$H/gcroom.py" "$O/../gcroom" "$r"
    a=(room --dar "$CT/st2/$r.dar" --room "$r" --uv-fold --keep-larger --keep-larger-reason "$REASON" --out "$O/$r.dar" --json "$O/$r.json")
    [ "$etm" = - ] || a+=(--etm "$etm")
    [ "$pairs" = - ] || a+=(--pairs "$pairs")
    case "$from" in -) ;; empty:*) a+=(--etm-empty "${from#empty:}");; *) a+=(--etm-from "$from");; esac
    python3 ps2_objects.py "${a[@]}" > "$O/objects.log" 2>&1 || { tail -5 "$O/objects.log"; exit 1; }
    tail -1 "$O/objects.log"
    python3 ps2_items.py pack --dar "$O/$r.dar" --room "$r" --lib "$L" --out "$O/i/$r.dar" --json "$O/i/items.json" > "$O/i/items.log" 2>&1 \
      || { tail -3 "$O/i/items.log"; exit 1; }
    tail -1 "$O/i/items.log" ;;
  itemlib)
    L=$2; rm -rf "${L:?}"; mkdir -p "$L"; cd "$TW"
    python3 ps2_items.py convert --lib "$L" --rooms "$3" --classes items,breakables --no-common > "$L/convert.log" 2>&1
    echo "itemlib: $(grep -c . "$L/INDEX.tsv") rows, NONE $(grep -c NONE "$L/INDEX.tsv")" ;;
  snd)
    SW=$2; WK=$3; CAT=${4:?}
    rm -rf "${SW:?}"; mkdir -p "$SW/tree/st2" "$SW/tree/em" "$SW/ps2"
    for r in ${ROOMS:?}; do cp "$WK/m/$r/em/$r.dar" "$SW/tree/st2/$r.dar"; done
    for e in ${SNDEM:?}; do cp "$WK/m/$e/em/$e.drs" "$SW/tree/em/"; done
    cd "$TW"
    python3 ps2_audio.py afs --iso "$ISO" --out "$SW/ps2" $(for r in $ROOMS; do echo $r.snd; done) $(for e in $SNDEM; do echo $e.snd; done) | tail -1
    python3 ps2_audio.py banks --tree "$SW/tree" --ps2 "$SW/ps2" --out "$SW/ov" \
      --files "$(for r in $ROOMS; do printf st2/%s.dar, $r; done)$(for e in $SNDEM; do printf em/%s.drs, $e; done | sed s/,$//)" --json "$SW/banks-map.json" --jobs 4 > "$SW/banks.txt"
    tail -1 "$SW/banks.txt"
    python3 d367/snd28_store.py "$SW/tree" "$SW/ov" "$SW/banks-map.json" "$CAT" "$SW/store" "$SW/ps2" | tail -1
    cp "$SW/banks.txt" "$SW/store/_map/" ;;
  final)
    python3 "$H/mkfinal.py" "$2" "$3" "$4" ;;
  clean)
    shift
    for s in "$@"; do
      case "$s" in /root/re4data/private/*cw32-2*) rm -rf "${s:?}";; *) echo "refusing to clean $s"; exit 1;; esac
    done ;;
  seal)
    shift
    for s in "$@"; do
      (cd "$s" && find . -type f ! -name SHA256SUMS.txt -printf '%P\n' | sort | xargs -d '\n' sha256sum > SHA256SUMS.txt)
      echo "sealed $s: $(wc -l < "$s/SHA256SUMS.txt") files"
    done ;;
  *) echo "step.sh: unknown step $1"; exit 2 ;;
esac
