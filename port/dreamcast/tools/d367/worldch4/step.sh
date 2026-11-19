#!/bin/bash
# step.sh <step> ...   (WSL; lane world-ch4 2026-11-02; castlegca26/step.sh for the chapter 4 rooms, see env.sh)
#   objects <room> <etm|-> <pairs|-> <etm-from|empty:names|-> <outdir> <item lib>
#   itemlib <lib> <rooms,...>
#   snd <scratch> <work>          ps2_audio.py banks on the motion-final room archives + the converted enemy archives
#   final <c4gca store> <pmc4gca store> <work>
#   clean <store>... / seal <store>...
set -euo pipefail
H=$(cd "$(dirname "$0")" && pwd); TW=$(cd "$H/../.." && pwd)
source "$H/env.sh"
REASON="no-GameCube-assets rule (user 10-23; chapter 4 Disc 2 build 11-02): the PS2 object replaces the GC one"
ISO=${PS2_ISO:-/mnt/c/Game Dev/Emulators/re4_helpers/Resident Evil 4 (USA)/Resident Evil 4 (USA).iso}
case "$1" in
  objects)
    r=$2; etm=$3; pairs=$4; from=$5; O=${6:?}; L=${7:?}
    rm -rf "${O:?}"; mkdir -p "$O/i" "$O/x/tex" "$O/../gcroom"
    cd "$TW"
    [ -s "$O/../gcroom/$r.arc" ] || python3 "$TW/d367/castlegca26/gcroom.py" "$O/../gcroom" "$r"
    a=(room --dar "$(w4_base "$r" dar)" --room "$r" --uv-fold --keep-larger --keep-larger-reason "$REASON" --out "$O/$r.dar" --json "$O/$r.json")
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
    SW=$2; WKD=$3; CAT=${4:?base catalog.json}
    rm -rf "${SW:?}"; mkdir -p "$SW/tree/st2" "$SW/tree/em" "$SW/ps2"
    fl=()
    for r in $W4_ROOMS; do cp "$WKD/m/$r/em/$r.dar" "$SW/tree/st2/$r.dar"; fl+=("st2/$r.dar"); done
    CEMOK=$(cat "$WKD/em-ok.txt")   # enemies gen-em.sh converted (env W4_CEM minus those without PS2 inputs)
    for e in $CEMOK; do cp "$WKD/m/$e/em/$e.drs" "$SW/tree/em/"; fl+=("em/$e.drs"); done
    cd "$TW"
    pats=(); for r in $W4_ROOMS; do pats+=("$r.snd"); done; for e in $CEMOK; do pats+=("$e.snd"); done
    python3 ps2_audio.py afs --iso "$ISO" --out "$SW/ps2" "${pats[@]}" | tail -1
    python3 ps2_audio.py banks --tree "$SW/tree" --ps2 "$SW/ps2" --out "$SW/ov" \
      --files "$(IFS=,; echo "${fl[*]}")" --json "$SW/banks-map.json" --jobs 4 > "$SW/banks.txt"
    tail -1 "$SW/banks.txt"
    python3 d367/snd28_store.py "$SW/tree" "$SW/ov" "$SW/banks-map.json" "$CAT" "$SW/store" "$SW/ps2" | tail -1
    mkdir -p "$SW/store/_map"; cp "$SW/banks.txt" "$SW/store/_map/" ;;
  final)
    python3 "$H/mkfinal.py" "$2" "$3" "$4" ;;
  clean)
    shift
    for s in "$@"; do
      case "$s" in /root/re4data/private/*c4gca-2*) rm -rf "${s:?}";; *) echo "refusing to clean $s"; exit 1;; esac
    done ;;
  seal)
    shift
    for s in "$@"; do
      (cd "$s" && find . -type f ! -name SHA256SUMS.txt -printf '%P\n' | sort | xargs -d '\n' sha256sum > SHA256SUMS.txt)
      echo "sealed $s: $(wc -l < "$s/SHA256SUMS.txt") files"
    done ;;
  *) echo "step.sh: unknown step $1"; exit 2 ;;
esac
