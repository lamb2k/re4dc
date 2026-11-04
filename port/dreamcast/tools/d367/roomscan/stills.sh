#!/bin/bash
# roomscan stills (WSL, root): base vs plan still pairs at a room's scan views, for the user's tier-3 look check.
#   stills.sh <base label> <plan label> <work dir> <out dir> <plan.json>...
# <label>: an rr-speed-build.sh cost arm (ELF /root/probe/lanes/route/out-<label>rW, <work>/<label>.data / .env).
# Views per room: the census warp view plus the two costliest sampled views of the plan (before_ms). Each still: a warp
# fixture (t11-fix.py --base payload, the arm's own data line) with `freeze`, staged with stage-scenario.py, one
# Flycast run of 40 s (run-emulator.py), the newest framebuffer kept as <out>/<room>/<view>-<arm>.png; disc deleted.
# Takes /root/probe/lane-rr-b.lock per run; one Flycast at a time.
set -euo pipefail
XB=${1:?}; XP=${2:?}; W=${3:?}; OUT=${4:?}; shift 4
TREE=${RR_TREE:-/root/work/lanes/lod27}; D367=$TREE/port/dreamcast/tools/d367
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
PY=/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe
mkdir -p "$OUT" "$W/stills"
for PLAN in "$@"; do
  python3 - "$PLAN" "$D367/castgc/warps" "$W/stills" <<'PY' > "$W/stills/list.txt"
import json, math, sys
plan = json.load(open(sys.argv[1])); room = plan['room']
views = [v for v in plan['views'] if v['kind'] == 'warp'][:1]
views += sorted((v for v in plan['views'] if v['kind'] != 'warp'), key=lambda v: -v['before_ms'])[:2]
src = open('%s/%s.txt' % (sys.argv[2], room)).read().splitlines()
for i, v in enumerate(views):
    name = 'v%d-%s' % (i, v['kind'])
    yaw = v['yaw']
    # the scan eye = Leon position + 1.6 m up - 2 m along the view: put Leon back there, facing the view
    x, y, z = v['eye'][0] + 2000 * math.sin(yaw), v['eye'][1] - 1600, v['eye'][2] + 2000 * math.cos(yaw)
    lines = [l for l in src if l.split()[:1] and l.split()[0] in ('room', 'find', 'inv', 'god')]
    if v['kind'] != 'warp':
        lines.insert(1, 'pos %d %d %d' % (x, y, z))
    else:
        lines.insert(1, [l for l in src if l.startswith('pos ')][0])
    lines.insert(2, 'ang %.4f' % yaw)
    lines += ['name rs-%s-%s' % (room, name), 'freeze 900']
    open('%s/%s-%s.txt' % (sys.argv[3], room, name), 'w').write('\n'.join(lines) + '\n')
    print(room, name)
PY
  while read -r R V <&3; do
    mkdir -p "$OUT/$R"
    [ -s "$OUT/$R/$V-base.png" ] && [ -s "$OUT/$R/$V-plan.png" ] && { echo "$R $V: pair exists, skipped"; continue; }
    for X in "$XB" "$XP"; do
      N=rs-$X-$R-$V; S="$HW/scenarios/rrspeed-$N"; FIX=$W/stills/fix-$N.json
      python3 "$D367/test11/t11-fix.py" "${X}rW" "$FIX" --base payload --data "$(cat "$W/$X.data")" --warp "$W/stills/$R-$V.txt" > /dev/null
      rm -rf "${S:?}"
      ( set -a; [ -s "$W/$X.env" ] && . "$W/$X.env"; set +a
        cd "$HW" && RE4DC_DISCCACHE=/mnt/c/Flycast-Evidence/_disccache bash /root/probe/lanelock.sh python3 stage-scenario.py "rrspeed-$N" --arm "candidate-route${X}rW" \
          --programs "$HW/programs-route.json" --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture "$FIX" ) > "$W/stills/stage-$N.json" 2>&1 || true
      grep -q STAGED_PAYLOAD_IDENTITY_PASS "$W/stills/stage-$N.json" || { echo "$R $V $X: stage failed"; rm -rf "${S:?}"; continue; }
      for TRY in $(seq 60); do  # the shared Flycast queue may be full: wait for a slot (up to ~10 min)
        ( cd "$HW" && timeout 120 "$PY" run-emulator.py "rrspeed-$N" --seconds 40 --period 6 ) > "$W/stills/run-$N.txt" 2>&1 || true
        grep -q "Emulator queue occupied" "$W/stills/run-$N.txt" || break; sleep 10
      done
      LAST=$(ls -d "$S"/capture/shots/t* 2>/dev/null | sort | tail -1 || true)
      if [ -n "$LAST" ] && [ -f "$LAST/frames/fb0.png" ]; then cp "$LAST/frames/fb0.png" "$OUT/$R/$V-$([ $X = "$XB" ] && echo base || echo plan).png"; fi
      echo "$R $V $X frozen=$(grep -ac 'warp: frozen' "$S/capture/run-output.txt" 2>/dev/null) halt=$(grep -ac HALT "$S/capture/run-output.txt" 2>/dev/null) shot=${LAST##*/}"
      rm -f "$S/disc/disc.bin"; rm -rf "${S:?}"
    done
  done 3< "$W/stills/list.txt"
done
