#!/bin/bash
# ch5regen: vqroom VQ step for the r331 / r332 PS2-world keys of st3-pak-loose (sources = run_rooms_st3 rooms-r331/r332 tex).
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/game-249effe5/port/dreamcast/tools
W=$L/vq3132
export PYTHONDONTWRITEBYTECODE=1
rm -rf "${W:?}"; mkdir -p "$W"
SRCS=()
for k in 0ebd9e7f-4a369e6b 06d4e055-cedbdba4 2bebcc5f-82af02e5 35f713b5-b80b2b65 5b460184-cade3a5e 58782e85-a6f3e627 6d75fff4-206e2095 6c2ff08e-4600535c 839d80d8-c1485ac9 bfdabdc0-0aa3b7a4 c453bc82-393c073d; do
  f=$(ls "$L"/tools/.assets/rooms-r33[12]/rooms/r33[12]/tex/$k.re4tex 2>/dev/null | head -1 || true)
  if [ -n "$f" ]; then SRCS+=("$f"); else echo "nosrc $k"; fi
done
cd /tmp
python3 "$S/c5r_vqkeys.py" "$T" "$W" "${SRCS[@]}"
python3 "$S/c5r_verify.py" "$S/missing-src.tsv" "$L/found.tsv" "$W/out"
