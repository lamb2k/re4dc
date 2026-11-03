#!/bin/bash
# lane lod27: step B for the lod27 set: bakeall/post_room.sh (rekey R4PW, ids, r4tc, room.r4rc GRID + OCCL + SCDD,
# certificate row) for each room converted by conv_lod.py, with each room's own lineage R4PW (the recipe's converter
# output the shipped R4PW was rekeyed from), then geninc_bake.py -> provenance_certificates_lod27.inc.
#   post_lod.sh <fixture json> <conv root (WSL path)> <set dir>
set -euo pipefail
FIX=${1:?}; CONV=${2:?}; SET=${3:?}
HERE=$(dirname "$(readlink -f "$0")")
TOOLS=$(cd "$HERE/../.." && pwd)
declare -A LIN=(
  [r119]=/root/probe/lanes/bakeall/rc/rc-r119-64/ps2-world.r4pw
  [r10e]=/root/work/lanes/world-n256all-scratch/rc-r10e-64/ps2-world.r4pw
  [r103]=/root/work/lanes/w2ms-scratch/sweep13/r103room64/ps2-world.r4pw
)
mkdir -p "$SET"; : > "$SET/cert-rows.txt"; : > "$SET/sizes.tsv"
for R in r119 r10e r103; do
    eval "$(python3 - "$FIX" "$R" <<'PY'
import json, sys, os, shlex
fx = json.load(open(sys.argv[1])); room = sys.argv[2]; rep = fx['replace']
base = fx['provenance']['t11']['base'].split(':', 1)[1] + '/tree'
def ship(name):
    k = 'dc/native/%s/%s' % (room, name)
    if k in rep: return rep[k]
    p = os.path.join(base, k)
    return p if os.path.exists(p) else ''
out = dict(SHIP_R4PW=ship('ps2-world.r4pw'), SHIP_RC=ship('room.r4rc'), HAS_TC=ship('ps2-world.r4tc'),
           SG='1' if ship('ps2-world.r4sg') else '0', PAK=rep.get('dc/tex.pak') or os.path.join(base, 'dc/tex.pak'))
print(' '.join('%s=%s' % (k, shlex.quote(v)) for k, v in out.items()))
PY
)"
    BAKE_TOOLS=$TOOLS bash "$TOOLS/d367/bakeall/post_room.sh" "$R" "$CONV/$R" "$SET" "${LIN[$R]}" "$SHIP_R4PW" "$PAK" "$HAS_TC" "$SHIP_RC" "$SG"
done
python3 "$TOOLS/d367/bakeall/geninc_bake.py" "$SET/cert-rows.txt" "$TOOLS/d367/texture_rect21/provenance_certificates.inc" \
    "$TOOLS/d367/texture_rect21/provenance_certificates_lod27.inc" "$TOOLS/d367/texture_rect21/provenance_lod27_rooms.inc"
cat "$SET/sizes.tsv"
