#!/bin/bash
# rr-jobs.sh quick|full <work> <tree> <sha7> <evidence (WSL)> <evidence (Windows)>   (WSL; lane rr)
# Writes the Flycast job list of a tier into <evidence>/_jobs: list.txt ("<slots> <name>" per line) and one Git Bash
# script per job (<name>.sh), run by rr-flycast.sh on the Windows host. Bases: <evidence>/_discs/{rel,g,k,c}
# (fp_master.sh): rel = the release binary, g = the full-play twin, k = KOS squeeze twin, c = census twin.
set -euo pipefail
TIER=${1:?}; W=${2:?}; T=${3:?}; S7=${4:?}; EVU=${5:?}; EVW=${6:?}
BIN=$(cd "$(dirname "$0")" && pwd)
if [ -s "$W/recipe.conf" ]; then . "$W/recipe.conf"; else . "$BIN/recipe.conf"; fi   # the built commit's recipe (rr-cycle.sh)
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
if [ "$TIER" = qa ]; then
  # QA disc jobs (standing rule 8; rr-qa.sh masters _discs/qa): boot keys (down,a,a,a), a QA-menu warp to r103 and
  # the GDEMU-profile door103 seed 1
  QO=$ROUTE/out-rr${S7}qrW
  [ -d "$EVU/_discs/qa" ] && [ -s "$QO/syms.txt" ] || { echo "rr-jobs qa: no QA base"; exit 1; }
  cp "$QO/syms.txt" "$J/syms-qa.txt"
  printf '%s\n' 'presets in | 2 | down' '- | 1 | a' '- | 1 | a' '- | 1 | a' > "$EVU/fixtures/qa-boot-keys.txt"
  printf '%s\n' '# QA preset r101, then the QA menu warp to r103' 'name r101' 'room 0x101' 'pos -7914 0 -254' 'ang 2.9600' \
    'find 0x00002000' 'inv default' 'qa_menu 300 r103.txt 800' > "$EVU/fixtures/qa-warp.txt"
  job 1 qa-boot "$(run qa-boot qa qa 60 --keys "\"\$EVW\fixtures\qa-boot-keys.txt\"" --stop "'room enter|phase=enter'" --grace 15)"
  job 1 qa-warp "$(run qa-warp qa qa 60 --warp "\"\$EVW\fixtures\qa-warp.txt\"" --stop "'phase=enter room=103'" --grace 10)"
  job 1 qa-gdemu "MAXP=1 bash \"\$FPD/gdemu_gate.sh\" rrqa \"\$EVW\gdemu-qa\" \"\$EVW\_discs\qa\" \"\$(cat \$J/syms-qa.txt)\" \"\$FPD/segments/door103-warp.txt\" 1"
  wc -l < "$J/list.txt"; exit 0
fi
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
# siege (lane cast-ps2-25 10-26): the r100 house siege (bench-r100-house: rsf 0x100 13, scenario 0x10, the village
# alerted, Ganados close in) on every tier. It halted Test 25 candidates on a dc/mot key a stale enemy archive streamed;
# rr-judge.py fails on HALT / FAULT / RE4DC MISSING in its log.
tr -d '\r' < "$T/port/dreamcast/tools/d367/rr/siege-r100-warp.txt" > "$EVU/fixtures/siege-r100.txt"
job 1 siege-r100 "$(run siege-r100 c c 60 --warp "\"\$EVW\\fixtures\\siege-r100.txt\"")"
# GC-ASSET gate (cast-ps2-25 10-26): h2 + the gate rooms on the gate-ON twin's base a (rr-gca.sh), judged by rr-judge.py
if [ "$TIER" = quick ] && [ -d "$EVU/_discs/a" ] && [ -s "$ROUTE/out-fprr${S7}aW/syms.txt" ]; then
  cp "$ROUTE/out-fprr${S7}aW/syms.txt" "$J/syms-a.txt"
  job 1 gca-h2 "$(run gca-h2 a a 300 --warp "'$SEG\\h2-warp.txt'" --pad "'$SEG\\h2-pad.txt'" --stop "'route movie terminal=. id=10030'" --grace 10)"
  # gca-title (castle-ps2-26 10-26): the other gca jobs warp in at frame ~171 and never draw the title or the save screen,
  # so @startup was judged empty. Power-on through the title, its menus and the load / card screens (castle31's gca-load
  # pad), stock boot; the VMU (RR_GCA_TITLE_VMU, default castle31's ch2-3 end save) lists save slots for the save pictures.
  V=${RR_GCA_TITLE_VMU:-/mnt/c/Flycast-Evidence/re4-dreamcast/castle31/vmu/handoff-ch23end-A1.bin}
  VA=; if [ -s "$V" ]; then VW="C:/${V#/mnt/c/}"; VW=${VW//\//\\}; VA="--vmu '$VW'"; fi
  tr -d '\r' < "$T/port/dreamcast/tools/d367/rr/gca-title-warp.txt" > "$EVU/fixtures/gca-title-warp.txt"
  tr -d '\r' < "$T/port/dreamcast/tools/d367/rr/gca-title-pad.txt" > "$EVU/fixtures/gca-title-pad.txt"
  job 1 gca-title "$(run gca-title a a 60 --warp "\"\$EVW\\fixtures\\gca-title-warp.txt\"" --pad "\"\$EVW\\fixtures\\gca-title-pad.txt\"" $VA)"
  for r in r100 r101 r103 r11e r11f; do
    tr -d '\r' < "$T/port/dreamcast/tools/d367/castgc/warps/$r.txt" > "$EVU/fixtures/gca-$r.txt"
    job 1 gca-$r "$(run gca-$r a a 60 --warp "\"\$EVW\\fixtures\\gca-$r.txt\"")"
  done
  # gca-grenade (lane wep19-26 10-26): no other gca job equips a thrown weapon, so the grenade models (em/pl00.drs 0x6A
  # + its three pictures), the wep19 module and its motion were never judged. r101: equip, aim and throw the hand,
  # incendiary and flash grenades (warp `arm` + `act`), then the rocket launcher.
  tr -d '\r' < "$T/port/dreamcast/tools/d367/rr/gca-grenade-warp.txt" > "$EVU/fixtures/gca-grenade.txt"
  # Two runs of <= 60 s each in one job (user rule: every Flycast check <= 60 s): the gate twin boots slowly (room frame
  # 40 at ~53 s wall, ~250 room frames a minute), so gca-grenade-boot runs to the r101 room entry and saves a state
  # bundle (fp_run.py --state-out, castle31 m3), and gca-grenade resumes it (--state-in) for the whole equip / throw
  # schedule. The bundle is keyed to this image (track03 sha256 + syms): a state of another build is refused. Only
  # gca-grenade is judged (the boot run is gca-r101's path).
  job 1 gca-grenade "$(run gca-grenade-boot a a 60 --warp "\"\$EVW\\fixtures\\gca-grenade.txt\"" --stop "'phase=enter room=101'" --grace 2 --state-out "\"\$EVW\\gca-grenade-state\"") && $(run gca-grenade a a 60 --warp "\"\$EVW\\fixtures\\gca-grenade.txt\"" --state-in "\"\$EVW\\gca-grenade-state\"")"
fi
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
    job 2 kit "MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash -c 'set -euo pipefail; export RC19D=${RC19D:?recipe.conf RC19D}; rm -rf ${KW:?}; cd $T/port/dreamcast && WORK=$KW JOBS=4 bash tools/d367/kit-check.sh ${KF#$T/port/dreamcast/} $ROUTE/out-rr${S7}rP \"$CAND\"' && bash '$WT/kit-boot.sh' $KW"
  else
    echo "kit: SKIP (no committed knob file for image $(cut -c1-16 "$W/image.sha256") or no packaged zips)" > "$W/kit-skip.txt"
  fi
  # the release checks (fp_gate.py on the packaged disc, its own prep and twins); 12 slots: it runs --jobs 10
  job 10 relchecks "export FP_BUILD=$ROUTE/out-rr${S7}rP FP_TREE=$T MSYS2_ENV_CONV_EXCL='FP_BUILD;FP_TREE'
bash \"\$FPD/fullplay.sh\" \"$CW\\gdemu\" --label rr${S7}fp --jobs 10 --evidence \"\$EVW\\relchecks\" --conf '$(wpath "$BIN/$REL_CONF")'"
fi
wc -l < "$J/list.txt"
