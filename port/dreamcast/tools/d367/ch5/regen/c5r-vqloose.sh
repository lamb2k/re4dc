set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/game-249effe5/port/dreamcast/tools
W=$L/vqloose
export PYTHONDONTWRITEBYTECODE=1
rm -rf "${W:?}"; mkdir -p $W
KEYS=$(grep st3-pak-loose $S/missing-src.tsv | cut -f1 | xargs -n1 basename | sed 's/\.re4tex$//')
SRCS=""
for k in $KEYS; do
  f=$(find $L/fixtures $L/pairs-st3 $L/pairs-r3 $L/pairs-em1f $L/emprep-game-249effe5 $L/prepem-game-249effe5 -name "$k.re4tex" 2>/dev/null | head -1 || true)
  [ -n "$f" ] && SRCS="$SRCS $f"
done
echo "sources found: $(echo $SRCS | wc -w)"
cd /tmp
python3 $S/c5r_vqkeys.py $T $W $SRCS | awk '{print $NF=="fail"?"fail":$4}' | sort | uniq -c
python3 $S/c5r_verify.py $S/missing-src.tsv $L/found.tsv $W/out
