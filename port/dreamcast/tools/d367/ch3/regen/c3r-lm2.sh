set -euo pipefail
# c3r-lm2.sh ROOM...: compact+release with the ch4regen le_mirror variants (b47c, p45/c3d2), castle tools
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
X=/root/re4data/private/cxfix-replay-20261018/replay
TD=$L/trees/90606dcf/port/dreamcast/tools
for v in b47 p45; do cp "$X/lm-$v.py" "$TD/lem_$v.py"; echo "$v $(sha256sum "$TD/lem_$v.py" | cut -c1-12)"; done
C=origin/lane/castle-1015; T=$L/trees/$C
for R in "$@"; do
  st=st${R:1:1}
  for v in b47 p45; do
    D=$L/compact/lm-$v/$R; rm -rf "${D:?}"; mkdir -p "$(dirname "$D")"
    if ( cd /tmp && python3 "$S/c3r_compact.py" "$T/port/dreamcast/tools" "$TD/lem_$v.py" "$L/src/$st/$R.das" "$L/tex1/$C/$R/tex" "$D" > "$D.log" 2>&1 ); then
      O=$L/rel/lm-$v/rel-$R/$st; mkdir -p "$O"
      for x in arc dar; do
        ( cd /tmp && python3 "$T/port/dreamcast/tools/room_smd.py" release "$D/$R.$x" "$L/pkg/$C/pkg-$R/MAINSCENARIO.re4mesh.json" "$O/$R.$x" > /dev/null )
        echo "$v $R rel.$x $(sha256sum "$O/$R.$x" | cut -c1-12)"
      done
    else echo "$v $R FAIL $(tail -1 "$D.log")"; fi
  done
done
