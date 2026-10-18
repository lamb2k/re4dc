set -euo pipefail
# c3r-tex1.sh ROOM COMMIT...: prepare_native_ui room textures at each tool commit; outputs under $L/tex1/<commit>/<room>
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
ISO="/mnt/c/Game Dev/Emulators/Resident Evil 4 Debug (Disc 1)/Resident Evil 4 Debug (Disc 1).iso"
R=${1:?room}; shift
st=st${R:1:1}
mkdir -p "$L/src"
[ -e "$L/src/$st/$R.das" ] || python3 "$S/c3r_gcx.py" "$ISO" "$L/src" "$st/$R.das"
for C in "$@"; do
  T=$L/trees/$C
  if [ ! -d "$T" ]; then git -C "$L/git" worktree add -q --detach "$T" "$C"; fi
  O=$L/tex1/$C/$R; mkdir -p "$O"
  echo "$st/$R.arc" > "$O/manifest"
  D=$(mktemp -d "$L/tmp.XXXXXX"); mkdir -p "$D/$st"; ln -s "$L/src/$st/$R.das" "$D/$st/$R.das"
  ( cd /tmp && nice python3 "$T/port/dreamcast/tools/prepare_native_ui.py" "$D" "$O/manifest" "$O/tex" > "$O/tex.log" 2>&1 ) || { tail -5 "$O/tex.log"; }
  rm -rf "${D:?}"
  echo "$C $R $(ls "$O/tex" 2>/dev/null | wc -l) files"
done
