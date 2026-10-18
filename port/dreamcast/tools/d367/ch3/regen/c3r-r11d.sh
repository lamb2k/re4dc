set -euo pipefail
# c3r-r11d.sh: le_mirror --native-rooms of st1/r11d.das with several le_mirror versions, then the AICA search
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
LAY=127936,253856,72544,264576,0,0,0,32736,1004192
B=$L/extra/r11d-src; mkdir -p "$B/st1"; ln -sf "$L/src/st1/r11d.das" "$B/st1/r11d.das"
for C in 90606dcf origin/lane/castle-1015 8b6449b1 origin/lane/ch2code16; do
  T=$L/trees/$C; [ -d "$T" ] || git -C "$L/git" worktree add -q --detach "$T" "$C"
  TAG=$(echo "$C" | tr '/' '_'); O=$L/extra/r11d-mirror-$TAG; rm -rf "${O:?}"
  ( cd /tmp && python3 "$T/port/dreamcast/tools/le_mirror.py" "$B" "$O" --native-rooms > "$O.log" 2>&1 ) || { echo "$C mirror fail"; continue; }
  f=$O/st1/r11d.dar; [ -e "$f" ] || { echo "$C no dar"; continue; }
  echo "$C $(stat -c %s "$f") $(sha256sum "$f" | cut -c1-12)"
  bash "$S/c3r-aica.sh" origin/lane/castle-1015 $LAY "$f" st1/r11d.dar 2>&1 | tail -1
done
for v in b47 p45; do
  O=$L/extra/r11d-mirror-$v; rm -rf "${O:?}"
  ( cd /tmp && python3 "$L/trees/90606dcf/port/dreamcast/tools/lem_$v.py" "$B" "$O" --native-rooms > "$O.log" 2>&1 ) || { echo "$v mirror fail"; continue; }
  f=$O/st1/r11d.dar; echo "$v $(stat -c %s "$f") $(sha256sum "$f" | cut -c1-12)"
  bash "$S/c3r-aica.sh" origin/lane/castle-1015 $LAY "$f" st1/r11d.dar 2>&1 | tail -1
done
