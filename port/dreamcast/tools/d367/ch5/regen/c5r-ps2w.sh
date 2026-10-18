set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
cp $S/c5r_run_rooms_st3.py $L/run_rooms_st3.py
cd $L
PYTHONDONTWRITEBYTECODE=1 nice $L/venv/bin/python run_rooms_st3.py "$@" > $L/ps2w-$1.log 2>&1 || true
grep -E 'ROOM_READY|ROOM_BLOCKED|PREFLIGHT|Error' $L/ps2w-$1.log | cut -c1-300 | tail -20
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/tools/.assets
