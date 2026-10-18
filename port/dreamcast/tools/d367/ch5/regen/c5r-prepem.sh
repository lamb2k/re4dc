set -euo pipefail
# ch5found16 prepem5.sh (prep-*: --keep-motion-resident) and hot39.sh (preph-*: --hot-audit d367/motion/hot/<em>-<room>.json
# --diagnostic-incomplete-prefetch), tools at ${GREF:-origin/lane/ch5found16}; GC source = review disc 2 em/<em>.drs.
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
GREF=${GREF:-origin/lane/ch5found16}
G=$L/game-$(git -C /root/work/re4-dreamcast rev-parse --short=8 $GREF)
[ -d $G ] || git -C $L/tools worktree add -q --detach $G $(git -C /root/work/re4-dreamcast rev-parse $GREF)
TT=$G/port/dreamcast/tools
P=$L/prepem-$(basename $G)
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $P/src/em; cd $P
for E in em32 em36 em39 em3a em3d; do
  [ -e src/em/$E.drs ] || ( cd $TT && python3 - "$P/src/em/$E.drs" "$E" <<'PY'
import sys; sys.path.insert(0,'.')
from assetpipe.rooms import GcIso
g=GcIso('/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm')
k=[f for f in g.files if f.lower()=='em/%s.drs'%sys.argv[2]][0]
open(sys.argv[1],'wb').write(g.read(k))
PY
  )
  echo em/$E.drs > $E-tex.manifest
  [ -d tex-$E ] || python3 $TT/prepare_native_ui.py $P/src $P/$E-tex.manifest $P/tex-$E > tex-$E.log 2>&1 || tail -2 tex-$E.log
  rm -rf "${P:?}/prep-$E"
  python3 $TT/prepare_enemy_motions.py --source src/em/$E.drs --output prep-$E --keep-motion-resident --textures tex-$E > prep-$E.log 2>&1 || tail -2 prep-$E.log
done
for h in em36:r307 em39:r31c; do
  E=${h%%:*}; R=${h#*:}
  rm -rf "${P:?}/preph-$E"
  python3 $TT/prepare_enemy_motions.py --source src/em/$E.drs --output preph-$E --hot-audit $TT/d367/motion/hot/$E-$R.json --diagnostic-incomplete-prefetch --textures tex-$E > preph-$E.log 2>&1 || tail -2 preph-$E.log
done
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $P
