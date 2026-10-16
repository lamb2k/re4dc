#!/bin/bash
# gdemu_gate.sh <tag> <evidence dir> <fp_master base dir> "<twin syms>" <warp fixture> <seed...>   (Git Bash)
# GDEMU race gate: fp_run.py --base under RE4DC_EMU=console RE4DC_GD_PROFILE=gdemu (flycast-console: BIOS status
# COMPLETED before the G1 DMA data lands), one run per seed, at most MAXP (6) at once, 150 s cap, stop 15 s after r103
# entry (use the door103 fixture: r101 entry + the r103 door load). Pass = every seed reaches r103 with no
# MISSING / HALT / FAULT / Out of memory line. Crash repro only, never timing. Docs: docs/tools/flycast-console.md.
set -u
here=//wsl.localhost/Ubuntu-24.04/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/d367/fullplay
TAG=$1; EV=$2; BASE=$3; SYMS=$4; WARP=$5; shift 5
MAXP=${MAXP:-6}
export RE4DC_EMU=console RE4DC_GD_PROFILE=gdemu RE4DC_GD_JITTER=${RE4DC_GD_JITTER:-20000}
for s in "$@"; do
  while [ $(jobs -rp | wc -l) -ge $MAXP ]; do sleep 5; done
  ( RE4DC_GD_SEED=$s python "$(cygpath -w "$here/fp_run.py")" --base "$(cygpath -w "$BASE")" --cap "$(cygpath -w "$EV/$TAG-s$s")" \
      --syms "$SYMS" --seconds 150 --name $TAG-s$s --warp "$(cygpath -w "$WARP")" --stop 'phase=enter room=103' --grace 15 \
      > "$EV/$TAG-s$s.runner.log" 2>&1 ) &
  sleep 4
done
wait
fail=0
for s in "$@"; do
  o="$EV/$TAG-s$s/run-output.txt"
  bad=$(grep -a -m1 -E 'MISSING|HALT|FAULT|Out of memory' "$o" 2>/dev/null | cut -c1-160)
  r103=$(grep -a -c 'phase=enter room=103' "$o" 2>/dev/null)
  if [ -n "$bad" ] || [ "${r103:-0}" = 0 ]; then fail=$((fail+1)); echo "seed $s FAIL r103=${r103:-0} $bad"; else echo "seed $s ok"; fi
done
echo "GDEMU RACE GATE $([ $fail = 0 ] && echo PASS || echo FAIL) $fail/$# stopped"
[ $fail = 0 ]
