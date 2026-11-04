#!/bin/bash
# lane lod27 / roomscan: step B for a rebuilt-world set: bakeall/post_room.sh (rekey R4PW, ids, r4tc, room.r4rc GRID +
# OCCL + SCDD, certificate row) for each room, with each room's own lineage R4PW (the recorded recipe's converter output
# the shipped R4PW was rekeyed from), then geninc_bake.py -> texture_rect21/provenance_certificates_<tag>.inc and
# provenance_<tag>_rooms.inc.
#   post_lod.sh <fixture json> <conv root (WSL path)> <set dir> [<tag> <room>...]   (default: lod27 r119 r10e r103)
set -euo pipefail
FIX=${1:?}; CONV=${2:?}; SET=${3:?}; TAG=${4:-lod27}; shift 3; if [ $# -gt 0 ]; then shift; fi
ROOMS=("$@"); [ ${#ROOMS[@]} -gt 0 ] || ROOMS=(r119 r10e r103)
HERE=$(dirname "$(readlink -f "$0")")
TOOLS=$(cd "$HERE/../.." && pwd)
N=/root/work/lanes/world-n256all-scratch; B=/root/work/lanes/world-blender25-scratch
declare -A LIN=(
  [r119]=/root/probe/lanes/bakeall/rc/rc-r119-64/ps2-world.r4pw
  [r103]=/root/work/lanes/w2ms-scratch/sweep13/r103room64/ps2-world.r4pw
  [r10e]=$N/rc-r10e-64/ps2-world.r4pw [r107]=$N/rc-r107-64/ps2-world.r4pw [r11d]=$N/rc-r11d-64/ps2-world.r4pw
  [r108]=$N/rc-r108-64/ps2-world.r4pw [r11e]=$N/rc-r11e-64/ps2-world.r4pw [r100]=$N/rc-r100-64/ps2-world.r4pw
  [r111]=$B/rc-r111-64/ps2-world.r4pw [r117]=$B/rc-r117-64/ps2-world.r4pw [r109]=$B/rc-r109-64/ps2-world.r4pw
)
mkdir -p "$SET"; : > "$SET/cert-rows.txt"; : > "$SET/sizes.tsv"
for R in "${ROOMS[@]}"; do
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
    L=${LIN[$R]:-}   # rooms not listed: the recipe dir rc-<room>-64 of the n256all / blender25 / bakeall lanes
    if [ -z "$L" ]; then for d in $N/rc-$R-64 $B/rc-$R-64 /root/probe/lanes/bakeall/rc/rc-$R-64; do [ -f $d/ps2-world.r4pw ] && { L=$d/ps2-world.r4pw; break; }; done; fi
    [ -n "$L" ] || { echo "$R: no lineage R4PW" >&2; exit 1; }
    BAKE_TOOLS=$TOOLS bash "$TOOLS/d367/bakeall/post_room.sh" "$R" "$CONV/$R" "$SET" "$L" "$SHIP_R4PW" "$PAK" "$HAS_TC" "$SHIP_RC" "$SG"
done
python3 "$TOOLS/d367/bakeall/geninc_bake.py" "$SET/cert-rows.txt" "$TOOLS/d367/texture_rect21/provenance_certificates.inc" \
    "$TOOLS/d367/texture_rect21/provenance_certificates_$TAG.inc" "$TOOLS/d367/texture_rect21/provenance_${TAG}_rooms.inc"
cat "$SET/sizes.tsv"
