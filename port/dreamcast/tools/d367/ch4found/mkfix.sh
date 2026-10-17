#!/bin/bash
# mkfix.sh <room> <tag> [view=walk]: ch4found16 room fixture = ${FIXB:-ch3f-c} (ch3found's latest chapter 3 data set)
# + the room's keys from Codex's cx fixture (world package, textures, events, room archives) + its warp/pad files
# + ch4 additions (${ADD:-$L/fix/ch4-add.json}: prepared archives, compacted rooms, AICA banks) + the arm's overlays,
# armed for ${ARM}, pack-winner audited. Boss rooms r221/r228 get ch3found's boss files (as c3boss.sh).
set -euo pipefail
export ARM=${ARM:-cxc4amW}
R=$1; TAG=$2; VIEW=${3:-walk}
L=/root/probe/lanes-20261016/ch4found
C3=/root/probe/lanes-20261016/ch3found
TOOLS=/root/probe/codex-ps2-assets-20261013/tree
P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export CAND="$P/programs/candidate-route${ARM}"
D=$L/fixtures/$R; mkdir -p $D
SRC=/root/probe/codex-cx-fixtures-20261013/output/$R/cx-$R-$VIEW.armed.json
[ -n "${WARPSRC:-}" ] && SRC=$WARPSRC
OUT=$D/cx-$R-$TAG.armed.json
[ -e "$OUT" ] && { echo "exists $OUT"; exit 1; }
BASE=${FIXBASE:-$C3/fix/${FIXB:-ch3f-c}.json}
ADDF=${ADD:-$L/fix/ch4-add.json}
python3 - "$BASE" "$SRC" $R $C3 $D/tmp-$TAG.json "$ADDF" "${WARPTXT:-}" <<'PY'
import json, sys, os, glob
b = json.load(open(sys.argv[1])); c = json.load(open(sys.argv[2])); R = sys.argv[3]; C3 = sys.argv[4]
addf = sys.argv[6]; warptxt = sys.argv[7]
br, cr = b['replace'], c['replace']
n = 0
for k, v in cr.items():
    if k not in br and (R in k or k.startswith('dc/tex/') or k.startswith('evd/') or k.startswith('event/')):
        br[k] = v; n += 1
for k in ('dc/warp.txt', 'dc/padscript.txt', 'dc/codec_ready.txt'):
    if k in cr: br[k] = cr[k]
    else: br.pop(k, None)
if warptxt:
    br['dc/warp.txt'] = warptxt
if R in ('r221', 'r228'):
    br['st2/%s.arc' % R] = '%s/rel31/rel-%s/st2/%s.arc' % (C3, R, R)
    br['st2/%s.dar' % R] = '%s/rel31/rel-%s/st2/%s.dar' % (C3, R, R)
    br['dc/native/%s/MAINSCENARIO.re4mesh' % R] = '%s/rel31/pkg-%s/MAINSCENARIO.re4mesh' % (C3, R)
br['em/em2c.drs'] = C3 + '/prepem/prep-em2c/em2c.drs'
br['em/em38.drs'] = C3 + '/prepem/prep-em38/em38.drs'
for e in ('em2c', 'em38'):
    for t in json.load(open('%s/prepem/prep-%s/motion-residency-report.json' % (C3, e)))['textures']['selected']:
        br['dc/tex/%s/%s.re4tex' % (t['key'][0], t['key'])] = '%s/prepem/tex-%s/%s.re4tex' % (C3, e, t['key'])
br['em/em2d.drs'] = C3 + '/prepem/prep-em2d/em2d.drs'
added = 0
if os.path.exists(addf):
    a = json.load(open(addf))
    for k, v in a.get('all', {}).items():
        br[k] = v; added += 1
    for k, v in a.get('rooms', {}).get(R, {}).items():
        br[k] = v; added += 1
    for k, v in a.get('fallback', {}).items():   # GC-converted enemy / event textures: only keys the base lacks
        if k not in br:
            br[k] = v; added += 1
for f in glob.glob(os.environ['CAND'] + '/*.ovl'):
    br['dc/' + os.path.basename(f)] = f
b['remove'] = sorted(set(b['remove']) - set(br))
b['provenance']['ch4found16_room'] = {'room': R, 'codex_fixture': sys.argv[2], 'codex_added': n, 'ch4_added': added}
json.dump(b, open(sys.argv[5], 'w'), indent=1, sort_keys=True)
print(R, 'codex keys added', n, 'ch4 keys', added)
PY
python3 $TOOLS/port/dreamcast/tools/d367/texchk/fixture_arm.py $D/tmp-$TAG.json $OUT ${ARM} --candidate-dir "$CAND" | tail -1
rm -f $D/tmp-$TAG.json
PAK=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['replace']['dc/tex.pak'])" $OUT)
python3 $TOOLS/port/dreamcast/tools/audit_ps2_texture_winners.py --pack "$PAK" --room /root/probe/codex-cx-textures-20261013/output/rooms/$R.json \
  --fixture "$R=$OUT" --output $D/cx-$R-$TAG.pack-audit.json > /dev/null || true
python3 -c "import json,sys;a=json.load(open(sys.argv[1]));r=a['rooms'][sys.argv[2]];print('PACK_AUDIT',sys.argv[2],r.get('fixture_selection',r.get('selection')))" $D/cx-$R-$TAG.pack-audit.json $R
