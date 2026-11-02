#!/bin/bash
# lane bakeall: step B over a batch: resolve each room's shipped files from a release fixture (replace map, else the
# payload base tree) and run post_room.sh on its conv_room.sh output.
#   post_set.sh <fixture json> <conv root (WSL path)> <set dir> <room> ...
set -euo pipefail
FIX=${1:?}; CONV=${2:?}; SET=${3:?}; shift 3
SCR=/root/work/lanes/world-n256all-scratch
HERE=$(dirname "$(readlink -f "$0")")
mkdir -p "$SET"
for R in "$@"; do
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
    LIN=/root/probe/lanes/bakeall/rc/rc-$R-64/ps2-world.r4pw; [ -f "$LIN" ] || LIN=$SCR/rc-$R-64/ps2-world.r4pw
    [ "$R" = r10d ] && LIN=/root/re4data/private/ch21l-20261020/dc/native/r10d/ps2-world.r4pw   # rc-r10d-64 is r10dbake23's
    bash "$HERE/post_room.sh" "$R" "$CONV/$R" "$SET" "$LIN" "$SHIP_R4PW" "$PAK" "$HAS_TC" "$SHIP_RC" "$SG"
done
