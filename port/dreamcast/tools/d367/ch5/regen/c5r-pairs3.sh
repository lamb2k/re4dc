set -euo pipefail
# st3 lane q147.sh (pairs-em1f, explicit pairs) and q16.sh-equivalent pairs-r3 (r300 e75f4f42/56b64f34/7222ad5b etc. from
# st3-material-pairs.json, explicit --pair since the round-2 logs on C: were later overwritten)
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/tools/port/dreamcast/tools
ISO='/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm'
export PYTHONDONTWRITEBYTECODE=1
rm -rf "${L:?}/pairs-em1f" "${L:?}/pairs-r3"
cd /tmp
python3 $T/d367/pairs_from_log.py --iso "$ISO" --output $L/pairs-em1f --pair 734b77e1-784d02a1:8fbab74e-245332ce --pair d4ed44ff-8433a435:021bd49a-0e35cf88 --file em/em1f.das --file st3/r30b.das --file em/em1d.das --file em/em1e.das 2>&1 | tail -3
P=$(python3 -c "
import json
d=json.load(open('$L/game-249effe5/port/dreamcast/tools/d367/st3firstpass/st3-material-pairs.json'))
print(' '.join('--pair %s:%s'%(x['color'],x['mask']) for x in d))")
echo "$P"
python3 $T/d367/pairs_from_log.py --iso "$ISO" --output $L/pairs-r3 $P --file st3/r300.das --file st3/r304.das --file st3/r305.das --file ss/cmn/ss_oc301.dat 2>&1 | tail -3
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $L/pairs-em1f $L/pairs-r3
