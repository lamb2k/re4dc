set -euo pipefail
# KOS twins for arms a9krP / a9prP (+ later bench arms), mastered on the Test 17 tree (identity proven separately).
export K=/root/work/lanes/actorplan19/k
T=/root/work/lanes/actorplan19/tree
D=$T/port/dreamcast/tools/d367/fullplay
S=/root/work/lanes/actorplan19
R=$S/rel17
mkdir -p $S/fptrees
if [ ! -f $R/manifest.json ]; then
  mkdir -p $R
  python3 $D/fp_iso.py extract "/mnt/c/Game Dev/Emulators/RE4DC-Test17-Candidate/gdemu/track03.bin" $R/tree --manifest $R/manifest.json --ipbin $R/IP.BIN
fi
for a in ${ARMS:-k p}; do
  FP_TREES=$S/fptrees FP_SKIP_IDENTITY=1 bash $D/fp_twin.sh /root/probe/lanes/route/out-a9${a}rP ap19sq$a KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 | tail -2
  bash $D/fp_master.sh $R/tree $R/manifest.json $R/IP.BIN /mnt/c/Flycast-Evidence/re4-dreamcast/actorplan19-20261019/_base-sq$a /root/probe/lanes/route/out-fpap19sq${a}W | tail -2
done
echo KOS TWINS DONE
