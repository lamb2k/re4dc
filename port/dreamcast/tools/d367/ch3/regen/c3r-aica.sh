set -euo pipefail
# c3r-aica.sh TOOLSCOMMIT LAYOUT IN_FILE DISC_PATH: aica_search (ch2regen) the unconverted IN_FILE to the target sha of DISC_PATH
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
C=${1:?}; LAY=${2:?}; IN=${3:?}; DP=${4:?}
T=$L/trees/$C
[ -d "$T" ] || git -C "$L/git" worktree add -q --detach "$T" "$C"
[ -e "$L/aica_search.py" ] || git -C "$L/git" show origin/wip/ch2regen-20261017:port/dreamcast/tools/d367/ch2/regen/aica_search.py > "$L/aica_search.py"
SHA=$(python3 -c "import json,sys;print(json.load(open('$S/srcmap.json'))[sys.argv[1]]['sha256'])" "$DP")
O=$L/aica/$DP; mkdir -p "$(dirname "$O")" "$L/aica-cache"
( cd /tmp && nice python3 "$L/aica_search4k.py" "$T/port/dreamcast/tools" "$IN" "$SHA" "$L/aica-cache" "$O" --layout "$LAY" 2>&1 | tail -3 )
if [ -e "$O" ] && [ "$(sha256sum "$O" | cut -d' ' -f1)" = "$SHA" ]; then echo "MATCH $DP"; else echo "NOMATCH $DP"; fi
