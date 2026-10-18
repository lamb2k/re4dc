set -euo pipefail
# c3r-res.sh: resident_keys.py pack of each candidate tree's committed vram/resident/r*.tsv; print sha
L=/root/probe/lanes-20261018/ch3regen
O=$L/extra/resident; mkdir -p "$O"
for C in origin/lane/castle-1015 origin/lane/castlecap4-16 origin/lane/ch3found16 origin/wip/ch3found16-20261017 origin/wip/ch3found16-base-20261017 origin/t15/int origin/lane/castlecap4-rigs; do
  T=$L/trees/$C
  [ -d "$T" ] || git -C "$L/git" worktree add -q --detach "$T" "$C"
  D=$T/port/dreamcast/tools/d367/vram/resident
  [ -d "$D" ] || { echo "$C no resident dir"; continue; }
  TAG=$(echo "$C" | tr '/' '_')
  ( cd "$D" && python3 ../resident_keys.py pack "$O/$TAG.bin" r*.tsv > /dev/null 2>&1 ) || { echo "$C pack failed"; continue; }
  echo "$C $(ls "$D" | wc -l) tsv $(stat -c %s "$O/$TAG.bin") $(sha256sum "$O/$TAG.bin" | cut -c1-16)"
done
