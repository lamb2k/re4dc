#!/bin/bash
# rr-jobs.sh quick|full <work> <tree> <sha7> <evidence (WSL)> <evidence (Windows)>   (WSL; lane rr)
# Writes the Flycast job list of a tier into <evidence>/_jobs: list.txt ("<slots> <name>" per line) and one Git Bash
# script per job (<name>.sh), run by rr-flycast.sh on the Windows host. Bases: <evidence>/_discs/{rel,g,k,c}
# (fp_master.sh): rel = the release binary, g = the full-play twin, k = KOS squeeze twin, c = census twin.
set -euo pipefail
TIER=${1:?}; W=${2:?}; T=${3:?}; S7=${4:?}; EVU=${5:?}; EVW=${6:?}
BIN=$(cd "$(dirname "$0")" && pwd)
. "$BIN/recipe.conf"
J=$EVU/_jobs; mkdir -p "$J" "$EVU/fixtures"; : > "$J/list.txt"
ROUTE=/root/probe/lanes/route
WT=//wsl.localhost/Ubuntu-24.04$T/port/dreamcast/tools/d367
FPD=$WT/fullplay
wpath() { echo "\\\\wsl.localhost\\Ubuntu-24.04$(echo "$1" | tr / '\\')"; }
for x in g c; do cp "$ROUTE/out-fprr${S7}${x}W/syms.txt" "$J/syms-$x.txt"; done
cp "$ROUTE/out-rr${S7}rP/syms.txt" "$J/syms-rel.txt"
ALL_ROOMS="r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r10f r111 r112 r113 r117 r118 r119 r11a r11b r11c r11d r11e r11f r200"
job() { # job <slots> <name> <script body>
  printf '%s %s\n' "$1" "$2" >> "$J/list.txt"
  { echo 'set -uo pipefail'; echo "J=/c/${J#/mnt/c/}"; echo "FPD='$FPD'"; echo "EVW='$EVW'"; echo "$3"; } > "$J/$2.sh"; }
run() { # fp_run line: <name> <base> <syms> <seconds> [extra fp_run args]
  local n=$1 b=$2 s=$3 sec=$4; shift 4
  echo "python \"\$FPD/fp_run.py\" --base \"\$EVW\\_discs\\$b\" --cap \"\$EVW\\$n\" --syms \"\$(cat \$J/syms-$s.txt)\" --seconds $sec --name rr-$n $*"; }
census_rooms() {
  if [ "$TIER" = full ] || [ ! -s "$W/diff-files.txt" ]; then echo "$ALL_ROOMS"; return; fi
  # game code / data tools outside per-room files -> all rooms; else only the rooms named in changed paths
  if grep -q -v -E '^port/dreamcast/(docs/|tools/d367/(rr|fullplay|castgc|texchk|mcheck)/)|\.md$|^docs/' "$W/diff-files.txt"; then
    local named; named=$(grep -o -E '(^|[^0-9a-z])r(1[0-1][0-9a-f]|200)([^0-9a-f]|$)' "$W/diff-files.txt" | grep -o -E 'r(1[0-1][0-9a-f]|200)' | sort -u | tr '\n' ' ')
    if grep -q -v -E '(^|[^0-9a-z])r(1[0-1][0-9a-f]|200)([^0-9a-f]|$)' "$W/diff-files.txt"; then echo "$ALL_ROOMS"; else echo "$named"; fi
  else echo "r101"; fi
}
SEG=$(wpath "$T/port/dreamcast/tools/d367/fullplay/segments")
# boot: the release binary from power-on to the title (no fixture)
CAND=$(cat "$W/cand.txt"); CW="C:/${CAND#/mnt/c/}"; CW=${CW//\//\\}
job 1 boot "python \"\$FPD/fp_run.py\" --disc '$CW\gdemu' --cap \"\$EVW\boot\" --syms \"\$(cat \$J/syms-rel.txt)\" --seconds 45 --name rr-boot --stop 'state title=' --grace 5"
# h2: r100 house to the s30 cliff movie (340/340 pictures, heap 4 before s30), the full-play gate's segment
job 1 h2 "$(run h2 g g 300 --warp "'$SEG\\h2-warp.txt'" --pad "'$SEG\\h2-pad.txt'" --stop "'route movie terminal=. id=10030'" --grace 10)"
# census
for r in $(census_rooms); do
  w=$T/port/dreamcast/tools/d367/castgc/warps/$r.txt; [ -f "$w" ] || continue
  if [ $r = r11b ]; then { tr -d '\r' < "$w"; echo "rsf 0x11b 0"; } > "$EVU/fixtures/cg-$r.txt"; else tr -d '\r' < "$w" > "$EVU/fixtures/cg-$r.txt"; fi
  job 1 cg-$r "$(run cg-$r c c 60 --warp "\"\$EVW\\fixtures\\cg-$r.txt\"")"
done
echo "$(census_rooms)" > "$W/census-rooms.txt"
if [ "$TIER" = quick ]; then
  job 2 kos "bash \"\$FPD/kos_squeeze.sh\" \"\$EVW\\_discs\\c\" fprr${S7}cW \"\$EVW\\kos\" '49152:0 49152:1' fight"
  job 1 gdemu "MAXP=1 bash \"\$FPD/gdemu_gate.sh\" rr \"\$EVW\\gdemu\" \"\$EVW\\_discs\\g\" \"\$(cat \$J/syms-g.txt)\" \"\$FPD/segments/door103-warp.txt\" 1"
else
  for sc in fight call door leave100 leave103; do
    job 2 kos-$sc "bash \"\$FPD/kos_squeeze.sh\" \"\$EVW\\_discs\\c\" fprr${S7}cW \"\$EVW\\kos\" '49152:0 49152:1' $sc"
  done
  for half in "1 2 3 4 5" "6 7 8 9 10"; do
    job 5 "gdemu-${half%% *}" "MAXP=5 bash \"\$FPD/gdemu_gate.sh\" rr \"\$EVW\\gdemu\" \"\$EVW\\_discs\\g\" \"\$(cat \$J/syms-g.txt)\" \"\$FPD/segments/door103-warp.txt\" $half"
  done
  # cap rooms (chapter 2 cap rigs + r10a), on the census twin
  for w in "$T/port/dreamcast/tools/d367/ch2/warps/k-r11d.txt" "$T/port/dreamcast/tools/d367/ch2/warps/k-r200.txt" "$T/port/dreamcast/tools/d367/fullplay/segments/r10a-warp.txt"; do
    n=cap-$(basename "$w" .txt); tr -d '\r' < "$w" > "$EVU/fixtures/$n.txt"
    job 1 "$n" "$(run "$n" c c 60 --warp "\"\$EVW\\fixtures\\$n.txt\"")"
  done
  # decisions comparison (encounter quality): logic-trace pairs, the recipe's trace arm (base tT) vs the reference
  # recipe's (base tR, recipe.conf CH2_REF), same fixture and stop tick; each run under a host trace slot (trace_lock.sh)
  if [ -d "$EVU/_discs/tR" ]; then
    cp "$ROUTE/out-rr${S7}rT/syms.txt" "$J/syms-tT.txt"; cp "$ROUTE/out-rr${S7}refrT/syms.txt" "$J/syms-tR.txt"
    S=$T/port/dreamcast/tools/d367/fullplay/segments
    cp "$S/h2-warp.txt" "$EVU/fixtures/st-h2-warp.txt"; cp "$S/h2-pad.txt" "$EVU/fixtures/st-h2-pad.txt"
    cp "$S/bell-trg-warp.txt" "$EVU/fixtures/st-bell-warp.txt"; cp "$S/door103-warp.txt" "$EVU/fixtures/st-door103-warp.txt"
    cp "$BIN/st-r11b-warp.txt" "$EVU/fixtures/st-r11b-warp.txt"
    TL=$T/port/dreamcast/tools/d367/trace_lock.sh
    for win in "h2 180" "bell 60" "door103 60" "r11b 60"; do
      set -- $win; w=$1; sec=$2
      pad=""; [ "$w" = h2 ] && pad="--pad \"\$EVW\\fixtures\\st-h2-pad.txt\""
      for side in tR tT; do
        n=st-$w-$side
        { echo 'set -uo pipefail'; echo "J=/c/${J#/mnt/c/}"; echo "FPD='$FPD'"; echo "EVW='$EVW'"; echo "export RE4DC_LOG_STOP_TICK=2000"
          echo "$(run "$n" "$side" "$side" "$sec" --warp "\"\$EVW\\fixtures\\st-$w-warp.txt\"" $pad)"; } > "$J/$n-inner.sh"
        job 1 "$n" "MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- env TRACE_LOCK_OWNER=rr-$n bash $TL '/mnt/c/Program Files/Git/bin/bash.exe' \$J/$n-inner.sh"
      done
    done
  fi
  # contributor kit: kit-check.sh (WSL build from a clean checkout) + kit-boot.sh, only when a committed knob file
  # describes this exact image and the candidate has been packaged (rr.sh package <tag>); else reported as SKIP
  KF=$(grep -l "^# image-sha256: $(cat "$W/image.sha256")" "$T"/port/dreamcast/tools/d367/test*/release-knobs.txt 2>/dev/null | head -1 || true)
  CAND=$(cat "$W/cand.txt")
  if [ -n "$KF" ] && ls "$CAND"/*-GDEMU.zip > /dev/null 2>&1; then
    KW=/root/rr/work/kit-$S7
    job 2 kit "MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash -c 'set -euo pipefail; rm -rf ${KW:?}; cd $T/port/dreamcast && WORK=$KW JOBS=4 bash tools/d367/kit-check.sh ${KF#$T/port/dreamcast/} $ROUTE/out-rr${S7}rP \"$CAND\"' && bash '$WT/kit-boot.sh' $KW"
  else
    echo "kit: SKIP (no committed knob file for image $(cut -c1-16 "$W/image.sha256") or no packaged zips)" > "$W/kit-skip.txt"
  fi
  # the release checks (fp_gate.py on the packaged disc, its own prep and twins); 12 slots: it runs --jobs 10
  job 10 relchecks "export FP_BUILD=$ROUTE/out-rr${S7}rP FP_TREE=$T MSYS2_ENV_CONV_EXCL='FP_BUILD;FP_TREE'
bash \"\$FPD/fullplay.sh\" \"$CW\\gdemu\" --label rr${S7}fp --jobs 10 --evidence \"\$EVW\\relchecks\" --conf '$(wpath "$BIN/$REL_CONF")'"
fi
wc -l < "$J/list.txt"
