set -euo pipefail
# st3 lane r51.sh: cx_room_dependencies.py (prepared enemy lists, enemy archives, event transports) on review disc 2
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
ISO='/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm'
python3 -c "
import json,glob,os
rooms=sorted(os.path.basename(d) for d in glob.glob('$L/fixtures/r3*'))
json.dump({r:{} for r in rooms},open('$L/fixtures-index.json','w'))
print(len(rooms))"
rm -rf "${L:?}/deps"
cd $L/tools/port/dreamcast/tools/d367
PYTHONDONTWRITEBYTECODE=1 python3 cx_room_dependencies.py --iso "$ISO" --fixture-index $L/fixtures-index.json --out $L/deps > $L/deps.log 2>&1 || tail -5 $L/deps.log
tail -3 $L/deps.log
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/deps
