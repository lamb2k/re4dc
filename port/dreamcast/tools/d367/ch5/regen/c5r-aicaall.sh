set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
R=$L/rel33-game-249effe5
P=$L/prepem-game-249effe5
for r in r307 r30a r310 r311 r315 r329 r31b r31c r320 r327; do
  bash $S/c5r-aica.sh st3/$r.dar $R/rel-$r/st3/$r.dar | tail -1
done
bash $S/c5r-aica.sh em/em39.drs $P/preph-em39/em39.drs | tail -1
bash $S/c5r-aica.sh em/em3a.drs $P/prep-em3a/em3a.drs | tail -1
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/aica
