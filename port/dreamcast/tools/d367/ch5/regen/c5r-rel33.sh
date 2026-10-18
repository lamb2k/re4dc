set -euo pipefail
# st3 lane rel33.sh (compact-room + castle release31 method) and relout (le_mirror --compact-static-rel), replayed with
# the game tree tools at ${GREF:-origin/lane/ch5found16}.
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
GREF=${GREF:-origin/lane/ch5found16}
G=$L/game-$(git -C /root/work/re4-dreamcast rev-parse --short=8 $GREF)
[ -d $G ] || git -C $L/tools worktree add -q --detach $G $(git -C /root/work/re4-dreamcast rev-parse $GREF)
T=$G/port/dreamcast/tools
O=$L/rel33-$(basename $G)
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $O
if [ "${1:-}" = relout ]; then
  mkdir -p $O/relsrc/rel $O/relout
  ( cd $T && python3 - "$O" <<'P'
import sys; sys.path.insert(0,'.')
from assetpipe.rooms import GcIso
g=GcIso('/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm')
for n in ('st3_0','st3_1','st3_2','st3_3'):
    k=[f for f in g.files if f.lower()=='rel/%s.rel'%n][0]
    open(sys.argv[1]+'/relsrc/rel/%s.rel'%n,'wb').write(g.read(k))
P
  )
  python3 $T/le_mirror.py $O/relsrc $O/relout --compact-static-rel=st3_0,st3_1,st3_2,st3_3 2>&1 | tail -1
  shift
fi
one() {
  R=$1
  A=$L/fixtures/$R/ancillary-b47c37112cf4
  SRC=$A/source/st3/$R.das
  rm -rf "${O:?}/compact-$R"
  if ! python3 $T/prepare_native_ui.py --compact-room $SRC --compact-room-mips --textures $A/tex --output $O/compact-$R > $O/compact-$R.log 2>&1; then
    echo "$R COMPACT FAILED: $(tail -1 $O/compact-$R.log)"; return 0; fi
  mkdir -p $O/pkg-$R $O/rel-$R/st3
  python3 $T/convert_room_bins.py $O/pkg-$R/MAINSCENARIO.re4mesh --owner 0xff --smd $SRC --lod --lod-min-gain 0.4 \
    --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > $O/pkg-$R.log
  for e in arc dar; do
    python3 $T/room_smd.py release $O/compact-$R/$R.$e $O/pkg-$R/MAINSCENARIO.re4mesh.json $O/rel-$R/st3/$R.$e > $O/rel-$R/st3/$R.$e.log
  done
  echo "$R ok"
}
export -f one; export L O T
printf '%s\n' "$@" | grep . | xargs -P4 -I{} bash -c 'one {}' || true
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $O
