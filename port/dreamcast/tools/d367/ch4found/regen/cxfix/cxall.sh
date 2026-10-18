set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
O=/root/probe/lanes-20261018/ch4regen/cxrun
while IFS=: read v rooms; do
  echo $rooms | tr ' ' '\n' | grep . | xargs -P 4 -I{} python3 $S/c4r-cxrun.py $v $O {}
done < $S/cx-jobs.txt
rm -f $O/verify.tsv
python3 $S/c4r-cxverify.py $S/cx-targets.tsv $O | tail -70
