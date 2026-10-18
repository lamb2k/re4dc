set -euo pipefail
# c3r-rel.sh COMMIT MIRRORCOMMIT ROOM...: tex (prepare_native_ui) -> compact -> release31 (room_smd release) per room
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
C=${1:?commit}; MC=${2:?mirror commit or -}; shift 2
T=$L/trees/$C
[ -d "$T" ] || git -C "$L/git" worktree add -q --detach "$T" "$C"
MPY=-
if [ "$MC" != "-" ]; then
  [ -d "$L/trees/$MC" ] || git -C "$L/git" worktree add -q --detach "$L/trees/$MC" "$MC"
  MPY=$L/trees/$MC/port/dreamcast/tools/le_mirror.py
fi
TAG=$(echo "$C-$MC" | tr '/' '_')
for R in "$@"; do
  st=st${R:1:1}
  bash "$S/c3r-tex1.sh" "$R" "$C" > /dev/null
  TEX=$L/tex1/$C/$R/tex
  D=$L/compact/$TAG/$R; rm -rf "${D:?}"; mkdir -p "$(dirname "$D")"
  ( cd /tmp && nice python3 "$S/c3r_compact.py" "$T/port/dreamcast/tools" "$MPY" "$L/src/$st/$R.das" "$TEX" "$D" > "$D.log" 2>&1 ) || { tail -3 "$D.log"; continue; }
  P=$L/pkg/$C/pkg-$R
  [ -e "$P/MAINSCENARIO.re4mesh.json" ] || bash "$S/c3r-pkg.sh" "$C" "$R" > /dev/null
  O=$L/rel/$TAG/rel-$R/$st; mkdir -p "$O"
  for x in arc dar; do
    ( cd /tmp && python3 "$T/port/dreamcast/tools/room_smd.py" release "$D/$R.$x" "$P/MAINSCENARIO.re4mesh.json" "$O/$R.$x" > /dev/null )
    echo "$TAG $R compact.$x $(sha256sum "$D/$R.$x" | cut -c1-12) rel.$x $(sha256sum "$O/$R.$x" | cut -c1-12)"
  done
done
