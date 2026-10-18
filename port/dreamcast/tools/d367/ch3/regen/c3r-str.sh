set -euo pipefail
# c3r-str.sh: aica_banks streams (bgm/aica_str.dat) for castle (ch31, castle tree) and ch3found (ch3, ch3found tree)
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
ISO=/root/work/re4-dreamcast/orig/G4BE08/re4_debug_disc1.iso
M=$L/src
for f in bgm/bio4bgm.sbb bgm/bio4evt.sbb bgm/bio4str.hed; do [ -e "$M/$f" ] || python3 "$S/c3r_gcx.py" "$ISO" "$M" "$f"; done
B=$L/srcbgm; rm -rf "${B:?}"; mkdir -p "$B/bgm"; for f in bio4bgm.sbb bio4evt.sbb bio4str.hed; do ln -sf "$M/bgm/$f" "$B/bgm/$f"; done
MM=$L/mirror-bgm; rm -rf "${MM:?}"
( cd /tmp && python3 "$L/trees/origin/lane/castle-1015/port/dreamcast/tools/le_mirror.py" "$B" "$MM" > "$MM.log" 2>&1 ) || tail -3 "$MM.log"
ls -la "$MM/bgm"; M=$MM
run() { C=$1; K=$2; O=$L/extra/str-$K; rm -rf "${O:?}"; mkdir -p "$O"
  ( cd /tmp && nice python3 "$L/trees/$C/port/dreamcast/tools/aica_banks.py" streams --mirror "$M" --streams "$K" --out "$O" > "$O.log" 2>&1 ) || tail -3 "$O.log"
  echo "$K $(sha256sum "$O/bgm/aica_str.dat" | cut -c1-16) $(stat -c %s "$O/bgm/aica_str.dat")"; }
run origin/lane/castle-1015 ch31
run origin/lane/ch3found16 ch3
