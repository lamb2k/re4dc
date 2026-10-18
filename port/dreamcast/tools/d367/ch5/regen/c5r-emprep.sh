set -euo pipefail
# st3 lane q35.sh: tex-em (prepare_native_ui of em1d/em1e/em1f) + outT-em* (empty hot audit, streamed motions, --textures tex-em)
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
GREF=${GREF:-origin/lane/ch5found16}
G=$L/game-$(git -C /root/work/re4-dreamcast rev-parse --short=8 $GREF)
[ -d $G ] || git -C $L/tools worktree add -q --detach $G $(git -C /root/work/re4-dreamcast rev-parse $GREF)
TT=$G/port/dreamcast/tools
W=$L/emprep-$(basename $G)
P=$L/prepem-game-249effe5
export PYTHONDONTWRITEBYTECODE=1
mkdir -p $W/src/em
for E in em1d em1e em1f; do
  [ -e $W/src/em/$E.drs ] || ( cd $TT && python3 - "$W/src/em/$E.drs" "$E" <<'PY'
import sys; sys.path.insert(0,'.')
from assetpipe.rooms import GcIso
g=GcIso('/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm')
k=[f for f in g.files if f.lower()=='em/%s.drs'%sys.argv[2]][0]
open(sys.argv[1],'wb').write(g.read(k))
PY
  )
done
printf 'em/em1d.drs\nem/em1e.drs\nem/em1f.drs\n' > $W/tex-em.manifest
[ -d $W/tex-em ] || python3 $TT/prepare_native_ui.py $W/src $W/tex-em.manifest $W/tex-em > $W/tex-em.log 2>&1 || tail -2 $W/tex-em.log
echo '{"union":{"source_arc_indices":[]},"source_complete":false}' > $W/empty-hot.json
cd $TT
for n in em1d em1e em1f; do
  rm -rf "${W:?}/outT-$n"
  python3 -B prepare_enemy_motions.py --source $W/src/em/$n.drs --output $W/outT-$n --hot-audit $W/empty-hot.json --diagnostic-incomplete-prefetch --textures $W/tex-em 2>&1 | tail -1
done
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $W
