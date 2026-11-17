#!/bin/bash
# gen.sh <2|3> <out store dir> [afs.json] [archive names...]   (WSL; lane srcgeo 2026-11-17)
# The srcgeo (Disc 3, D3_SRCGEO=1) / srcgeo2 (Disc 2, D2_SRCGEO=1) data set. Inputs = the disc's FINAL files from srcgeo/chain.py
# (content tree overlaid by the recipe's D?_DATA sets in order): every enemy archive that has a PS2 BIO4DAT dat (or the names given)
# and every room registry / partner package. Regenerate whenever a later D?_DATA set stages one of these files.
# afs.json: {name: [[offset, size], ...]} of PS2 BIO4DAT.AFS (srcgeo/afs_index.py writes it; the first entry of size > 0 is the file).
set -euo pipefail
D=${1:?2 or 3}; O=${2:?out store dir}; AFS=${3:-/root/srcgeo-scratch/afs-fixed.json}; shift 3 || true
H=$(cd "$(dirname "$0")" && pwd); T=$(cd "$H/../../../../.." && pwd)
python3 "$H/chain.py" "$D" ${D1TREE:+--d1tree "$D1TREE"} > "$O.chain" 2> "$O.chain.err" || { cat "$O.chain.err"; exit 1; }
ARCH=(); PKG=()
want=" $* "
while read -r kind name path who; do
  if [ "$kind" = arch ]; then
    if [ -n "$*" ]; then case "$want" in *" $name "*) ;; *) continue;; esac
    else python3 -c "import json,sys;a=json.load(open('$AFS'));sys.exit(0 if [e for e in a.get('$name.dat',[]) if e[1]>0] else 1)" || continue
    fi
    ARCH+=(--arch "$name=$path")
  elif [ "$kind" = pkg ]; then PKG+=(--pkg "$name=$path"); fi
done < "$O.chain"
python3 "$T/port/dreamcast/tools/d367/ps2cast/srcgeo_store.py" --out "$O" --tree "$T" --ps2-afs "$AFS" "${ARCH[@]}" "${PKG[@]}"
cp "$O.chain" "$O/chain.txt"
