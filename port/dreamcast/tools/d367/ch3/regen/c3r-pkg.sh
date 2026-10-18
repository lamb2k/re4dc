set -euo pipefail
# c3r-pkg.sh COMMIT ROOM...: convert_room_bins prelit MAINSCENARIO (release31.sh step 1) per room at COMMIT
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
C=${1:?commit}; shift
T=$L/trees/$C
[ -d "$T" ] || git -C "$L/git" worktree add -q --detach "$T" "$C"
for R in "$@"; do
  st=st${R:1:1}
  [ -e "$L/src/$st/$R.das" ] || python3 "$S/c3r_gcx.py" "$ISO" "$L/src" "$st/$R.das"
  O=$L/pkg/$C/pkg-$R; mkdir -p "$O"
  ( cd /tmp && nice python3 "$T/port/dreamcast/tools/convert_room_bins.py" "$O/MAINSCENARIO.re4mesh" --owner 0xff --smd "$L/src/$st/$R.das" --lod --lod-min-gain 0.4 \
    --lod-max-levels 4 --lod-eps 24,48,96,192,384 --lod-share --class-auto --color prelit > "$O.log" 2>&1 ) || tail -3 "$O.log"
  echo "$C $R $(sha256sum "$O/MAINSCENARIO.re4mesh" | cut -c1-16)"
done
