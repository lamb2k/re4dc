set -euo pipefail
# c3r-warps.sh: castle mk32g.sh warp/pad texts + ch3found c449.sh k4-r203-kw, verbatim
W=/root/probe/lanes-20261018/ch3regen/extra/warps; mkdir -p "$W"
C=/root/re4data/private/cxfix-replay-20261018/output
cat > $W/cx-r20d-s20.txt <<X
name cx-r20d-s20
# castle lane: r20d, then a jump through door 0x10 into r206 (room_id_prev 0x20D, rsf[206] 0 = snipe done) -> s20
room 0x20d
pos -22062 7999 17122
ang 0.0
inv default
rsf 0x206 0 5
jump 200 0x20d 0x206 10007 7999 -4221 -1.75
dump
X
cat > $W/pad-r206-s20.txt <<X
0 0000 1 movie=1/1568 200000
+90 1000 4
X
mk(){ r=$1; tag=$2; shift 2; { grep -v "^act\|^dump\|^name" $C/r$r/cx-r$r-walk.txt; echo "name k4-r$r-$tag"; printf '%s\n' "$@"; echo dump; } > $W/k4-r$r-$tag.txt; }
mk 203 kw god "alivelog 150" "atfunc 300 0x8a" "kill 0 900 0x203" "killrep 20 90" || true
# god "alivelog 150" "atfunc 300 0x8a" "kill 0 900 0x203" "killrep 20 90"
sha256sum $W/*.txt | cut -c1-16
