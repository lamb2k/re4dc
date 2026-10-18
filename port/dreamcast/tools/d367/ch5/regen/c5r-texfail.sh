#!/bin/bash
# ch5regen: classify gate TEX_CHECK failures: key loose in the fixture / in the staged tex.pak / in neither; and
# whether the recorded run loaded the key (from the recorded tex-ch5e pak). Also confirm no disc images remain.
set -uo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
H=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018/hroot/h/scenarios
for r in r307 r310 r31c r31b; do
  K=$(grep -a "texchk: FAIL missing" "$H/c5r-$r/capture/run-output.txt" | awk '{print $4}' | sort -u)
  echo "$r keys $(echo $K | wc -w): $(python3 "$S/c5r_pakhas.py" /root/probe/lanes-20261018/ch5regen/gate/fix/$r.json $K | grep -c ' False ')"" not in pak, not loose"
  for k in $K; do grep -q "$k" "$S/missing-src.tsv" && echo "  TARGET $k"; done
done
find /mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018 -name 'disc.bin' | head
