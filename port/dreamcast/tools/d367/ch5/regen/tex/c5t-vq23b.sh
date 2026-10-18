set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5tex
W=/root/probe/lanes-20261018/ch5tex
G="/mnt/c/Game Dev/Emulators"
export PYTHONDONTWRITEBYTECODE=1
V=$W/vq33; cd /tmp
FX=$(ls $W/fx-e2/cx-r3*-walk-*.armed.json $W/fx-e2/cx-r327-fight1-*.armed.json)
mapfile -t L1 < <(ls "$G"/re4-rfp-20261015-st3e2/scenarios/*-11/capture/run-output.txt)
mapfile -t LA < <(ls "$G"/re4-rfp-20261015-st3e2/scenarios/*/capture/run-output.txt)
rm -rf "${V:?}/b" "${V:?}/c"; mkdir -p $V/b $V/c
python3 $S/c5t_vqroom.py $V/tex-st3vq2.pak $V/b $V/tex-st3vq.pak --fixtures $FX --logs "${L1[@]}" 2>&1 | tail -1 | grep -o "'candidates.*"
python3 $S/c5t_vqroom.py $V/tex-st3vq3.pak $V/c $V/tex-st3vq2.pak --fixtures $FX --logs "${LA[@]}" 2>&1 | tail -1 | grep -o "'candidates.*"
echo want st3vq2 ba6379dc st3vq3 0e0015de
