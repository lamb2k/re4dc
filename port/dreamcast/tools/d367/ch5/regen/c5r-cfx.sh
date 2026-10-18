set -euo pipefail
# ch5found16 cf8.sh (em1d/em1e/em1f --compact-effects, emprep5/cfx-*) then the aica-c5b AICA search on them
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
TT=$L/game-249effe5/port/dreamcast/tools
W=$L/emprep-game-249effe5
export PYTHONDONTWRITEBYTECODE=1
cd $W
for e in em1d em1e em1f; do
  rm -rf "${W:?}/cfx-$e"
  python3 $TT/prepare_enemy_motions.py --source $W/src/em/$e.drs --output cfx-$e --hot-audit $W/empty-hot.json --diagnostic-incomplete-prefetch --textures $W/tex-em --compact-effects > cfx-$e.log 2>&1 || tail -2 cfx-$e.log
  bash $S/c5r-aica.sh em/$e.drs $W/cfx-$e/$e.drs | tail -1
done
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/aica
