#!/bin/bash
# gdemu_gate.sh <tag> <evidence dir> <disc> "<twin syms>" <warp fixture> <seed...>   (Git Bash)
# GDEMU race gate: fp_run.py under RE4DC_EMU=console (flycast-console), one run per seed, at most MAXP (6) at once,
# SECS (default 60, the lean <= 1 min rule) cap, stop 15 s after r103 entry (use the door103 fixture: r101 entry + the
# r103 door load). Crash repro only, never timing.
#   <disc>  an fp_master.sh base dir (has base.json: the fixture goes into each run's track01) or a plain disc dir
#           (disc.gdi + tracks, e.g. a mkdcdisc twin whose dc/warp.txt already holds the fixture; pass - as fixture).
#   RE4DC_GD_PROFILE  gdemu (default; BIOS status COMPLETED before the G1 DMA data lands, jitter 20000) or
#                     weak (a weak/clone GDEMU: ~600 KiB/s like GDEMU.ini read_limit=600, 5 ms + 0..2 ms per command,
#                     KOS stream DMA slowed too; flycast-console 2026-10-16 or later). Other RE4DC_GD_* pass through.
# Pass = every seed reaches r103 with no stop (HALT / FAULT / Out of memory / not reaching r103) and no bad read
# (MISSING / DISC READ FAILED / short read / open failed / read failed / BAD-READ / DISCNOTE). Per seed it prints the
# guest-time (vbl-based wall_ms, emulator model, NOT console timing) of the r101 placement and of the door: from the
# fixture's last act (the door press) to "room enter 103", and the r103 load (host seconds to the lifecycle enter line,
# approximate). SUMMARY_ONLY=1 re-prints the table from an existing evidence dir without running anything.
# Docs: docs/tools/flycast-console.md.
set -u
here=$(cd "$(dirname "$0")" && pwd)
TAG=$1; EV=$2; BASE=$3; SYMS=$4; WARP=$5; shift 5
MAXP=${MAXP:-6}
SECS=${SECS:-60}
export RE4DC_EMU=console RE4DC_GD_PROFILE=${RE4DC_GD_PROFILE:-gdemu}
if [ "$RE4DC_GD_PROFILE" = gdemu ]; then export RE4DC_GD_JITTER=${RE4DC_GD_JITTER:-20000}; fi
if [ -e "$BASE/base.json" ]; then SRC=(--base "$(cygpath -w "$BASE")"); else SRC=(--disc "$(cygpath -w "$BASE")"); fi
FIX=(); [ "$WARP" = - ] || FIX=(--warp "$(cygpath -w "$WARP")")
mkdir -p "$EV"
[ "${SUMMARY_ONLY:-0}" = 1 ] || for s in "$@"; do
  while [ $(jobs -rp | wc -l) -ge $MAXP ]; do sleep 5; done
  ( RE4DC_GD_SEED=$s python "$(cygpath -w "$here/fp_run.py")" "${SRC[@]}" --cap "$(cygpath -w "$EV/$TAG-s$s")" \
      --syms "$SYMS" --seconds $SECS --name $TAG-s$s "${FIX[@]}" --stop 'phase=enter room=103' --grace 15 \
      > "$EV/$TAG-s$s.runner.log" 2>&1 ) &
  sleep 4
done
wait
# Bad reads. DISCNOTE lines alone are not failures: DISC_READ_FALLBACK=2 builds (test 15 plain sector reads) log every
# boot-log note, including the info rows (drive init ok, first read ok). Only the trouble rows count: a busy drive, a
# timeout / abort / reset, a late or missing transfer, a failed method, a re-init or PIO fallback, a bad stream table.
BADRE='MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))'
fail=0
echo "seed | result | r103 | bad reads | stop | r101 placed ms | door ms | r103 load s | GDCONSOLE profile"
for s in "$@"; do
  d="$EV/$TAG-s$s"; o="$d/run-output.txt"
  stop=$(grep -a -m1 -E 'HALT|FAULT|Out of memory' "$o" 2>/dev/null | cut -c1-100)
  nbad=$(grep -a -c -E "$BADRE" "$o" 2>/dev/null)
  bad1=$(grep -a -m1 -E "$BADRE" "$o" 2>/dev/null | cut -c1-100)
  r103=$(grep -a -c 'phase=enter room=103' "$o" 2>/dev/null)
  placed=$(grep -a -m1 -o 'warp: placed room=101.*wall_ms=[0-9]*' "$o" 2>/dev/null | grep -o '[0-9]*$')
  lastact=$(grep -a -B200 'warp: room enter 103' "$o" 2>/dev/null | grep -a -o 'warp: act [0-9]* .*wall_ms=[0-9]*' | tail -1 | grep -o '[0-9]*$')
  enter=$(grep -a -m1 -o 'warp: room enter 103.*wall_ms=[0-9]*' "$o" 2>/dev/null | grep -o '[0-9]*$')
  door=-; [ -n "$lastact" ] && [ -n "$enter" ] && door=$((enter - lastact))
  # r103 load: host seconds at which 'phase=enter room=103' appeared (fp_run stop_matched_s) minus the guest time of
  # 'room enter 103'; approximate (host clock vs guest clock, Flycast start-up included)
  load=-; [ -n "$enter" ] && load=$(python -c "import json,sys;r=json.load(open(sys.argv[1]));m=r.get('stop_matched_s');print('%.1f'%(m-int(sys.argv[2])/1000) if m else '-')" "$(cygpath -w "$d/run-result.json")" "$enter" 2>/dev/null)
  prof=$(cat "$d"/serial*.txt "$d"/flycast.log 2>/dev/null | grep -a -m1 -o 'GDCONSOLE profile=[a-z]*')
  if [ -n "$stop" ] || [ "${nbad:-0}" != 0 ] || [ "${r103:-0}" = 0 ]; then
    fail=$((fail+1)); res=FAIL
  else res=ok; fi
  echo "$s | $res | ${r103:-0} | ${nbad:-0} ${bad1} | ${stop:--} | ${placed:--} | $door | ${load:--} | ${prof:-?}"
done
echo "GDEMU RACE GATE ($RE4DC_GD_PROFILE) $([ $fail = 0 ] && echo PASS || echo FAIL) $fail/$# failed"
[ $fail = 0 ]
