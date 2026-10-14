#!/bin/bash
# arm.sh <label> <room> <view> [variant]: add the stage-3 disc keys to the unarmed fixture, arm it for <label>,
# run the pack-winner audit against this lane's texture selection.
set -euo pipefail
LANE=/root/probe/lanes-20261014/st3; L=$1; ROOM=$2; VIEW=$3; VAR=${4:-st3}
TOOLS=/root/probe/codex-ps2-assets-20261013/tree
CAND=$LANE/build/programs/candidate-route$L
D=$LANE/fixtures/$ROOM
SRC=$D/cx-$ROOM-$VIEW.unarmed.json
TMP=$D/cx-$ROOM-$VIEW-$VAR.unarmed.json
OUT=$D/cx-$ROOM-$VIEW-$VAR.armed.json
[ ! -e "$OUT" ] || { echo "$OUT exists"; exit 2; }
export PYTHONDONTWRITEBYTECODE=1
python3 - "$SRC" "$TMP" "$CAND" <<'PY'
import json, sys
src, out, cand = sys.argv[1:4]
d = json.load(open(src)); r = d['replace']
for n in ('st3_0', 'st3_1', 'st3_2', 'st3_3'):
    r['rel/%s.rel' % n] = '/root/probe/lanes-20261014/st3/relout/rel/%s.rel' % n
for m in ('em1d', 'em1e', 'em3b', 'em25'):
    r['dc/%s.ovl' % m] = cand + '/%s.ovl' % m
d.setdefault('provenance', {})['st3_lane'] = {'added': ['rel/st3_*.rel (le_mirror --compact-static-rel)', 'dc/em1d.ovl', 'dc/em1e.ovl', 'dc/em3b.ovl', 'dc/em25.ovl']}
json.dump(d, open(out, 'w'), indent=1, sort_keys=True)
PY
python3 "$TOOLS/port/dreamcast/tools/d367/texchk/fixture_arm.py" "$TMP" "$OUT" "$L" --candidate-dir "$CAND"
PAKFILE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['replace']['dc/tex.pak'])" "$OUT")
python3 "$TOOLS/port/dreamcast/tools/audit_ps2_texture_winners.py" --pack "$PAKFILE" \
  --room "$LANE/texture-fit/rooms/$ROOM.json" --fixture "$ROOM=$OUT" --output "$D/cx-$ROOM-$VIEW-$VAR.pack-audit.json" > /dev/null
python3 - "$D/cx-$ROOM-$VIEW-$VAR.pack-audit.json" "$ROOM" "$OUT" <<'PY'
import hashlib, json, sys
a = json.load(open(sys.argv[1])); row = a['rooms'][sys.argv[2]]
sel = row.get('fixture_selection', row.get('selection', 'UNKNOWN'))
print('fixture %s sha256 %s' % (sys.argv[3], hashlib.sha256(open(sys.argv[3], 'rb').read()).hexdigest()))
print('PACK_AUDIT %s %s' % (sys.argv[2], sel))
PY
