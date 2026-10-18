set -euo pipefail
# st3 lane q44.sh (pairs-all = pairs_from_log.py over allpairs.py pairs) + pairs-em1f; tools = st3 tool tree (tools/)
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=${PT:-$L/tools}/port/dreamcast/tools
ISO='/mnt/c/Game Dev/Emulators/Resident Evil 4 - 2004.11.25 Disc 2 (Resident Evil 4 Review Rom (GC) No Reviews Until March 05 Issues).gcm'
O=$L/pairs-${PTAG:-st3}
export PYTHONDONTWRITEBYTECODE=1
P=$(python3 $S/c5r_allpairs.py $L)
echo "$P" | wc -w
F=""; for r in r300 r301 r303 r304 r305 r306 r307 r308 r309 r30a r30b r30c r30d r30e r30f r310 r311 r312 r315 r316 r317 r318 r31a r31b r31c r31d r320 r321 r325 r326 r327 r329 r330 r331 r332 r322 r323 r324 r328 r333; do F="$F --file st3/$r.das"; done
rm -rf "${O:?}"
cd /tmp
python3 $T/d367/pairs_from_log.py --iso "$ISO" --output $O/all $P $F --file ss/cmn/ss_oc301.dat 2>&1 | tail -2
ls $O/all | wc -l
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $O
