set -euo pipefail
# ch3regen c3r-aica.sh method: aica_search4k (caps search) of the unconverted input to the target sha, test 15 layout.
# usage: c5r-aica.sh DISC_PATH IN_FILE [LAYOUT]
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/game-249effe5/port/dreamcast/tools
DP=${1:?}; IN=${2:?}; LAY=${3:-127936,253856,72544,264576,0,0,0,32736,1004192}
[ -e $L/aica_search4k.py ] || git -C /root/work/re4-dreamcast show origin/wip/ch3regen-20261018:port/dreamcast/tools/d367/ch3/regen/aica_search4k.py > $L/aica_search4k.py
SHA=$(awk -F'\t' -v p="$DP" '$1==p{print $3; exit}' $S/missing-src.tsv)
O=$L/aica/$DP; mkdir -p "$(dirname "$O")" $L/aica-cache
( cd /tmp && nice python3 $L/aica_search4k.py $T "$IN" "$SHA" $L/aica-cache "$O" --layout "$LAY" 2>&1 | tail -2 ) || true
if [ -e "$O" ] && [ "$(sha256sum "$O" | cut -d' ' -f1)" = "$SHA" ]; then echo "MATCH $DP"; else echo "NOMATCH $DP"; fi
