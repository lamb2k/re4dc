#!/bin/bash
# look.sh <name> [KNOB=value ...]   (Git Bash on the Windows host; look gallery, look study 2026-10-10)
#
# One command per look iteration: builds the warp twin of the play recipe (tools/d367/route/route-build.sh with
# play-knobs.txt + the knobs given, label lg<name>, ACT_CAP=0), renders every shot of shots.json in Flycast (warp
# rig, then `freeze` so the last framebuffer shot is a still), keeps the stills in $GALLERY/dc/<name>/<shot>.png,
# deletes each disc, then redraws the sheet and metrics (sheet.py) for every column in $GALLERY/dc.
#
# env: TREE=<WSL checkout> (default: the checkout holding this script), SKIP_BUILD=1 (reuse out-lg<name>), ARM=<label> (render an existing build),
#      LOOK=<n> (LOOK_TOGGLE builds: warp "look <n>" preset),
#      SHOTS="r100start r101F" (subset), GALLERY (default re4-assets-private/look-gallery-20261010),
#      EV (evidence root, default D:/Flycast-Evidence/re4-dreamcast/look-gallery), COLS="cur fogA" (sheet columns,
#      default every dc/ dir), HWMS=<json {column: {view: ms}}> (default $GALLERY/hwms.json), NOSHEET=1.
# Runs one Flycast at a time. Names are reusable: a rerun replaces dc/<name>.
set -u
NAME=$1; shift
KNOBS="$*"
L=${ARM:-lg$NAME}   # ARM=<label>: reuse an existing route build out-<label> (no build)
[ -n "${ARM:-}" ] && SKIP_BUILD=1
HERE=$(cd "$(dirname "$0")" && pwd)
WTREE=${TREE:-$(MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- wslpath -u "$(cygpath -w "$HERE/../../../../..")" 2>/dev/null)}
case "$WTREE" in /root/*|/home/*|/mnt/*) ;; *) echo "set TREE=<WSL path of the checkout> ($WTREE)"; exit 1 ;; esac
GALLERY=${GALLERY:-"/c/Game Dev/Emulators/re4-assets-private/look-gallery-20261010"}
EV=${EV:-/d/Flycast-Evidence/re4-dreamcast/look-gallery}
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
WL=/root/probe/look-gallery/$L
TMP=$(cygpath -u "$TEMP")/look-$L.sh
mkdir -p "$GALLERY/dc/$NAME" "$EV"
run_wsl() { printf '%s\n' "$1" > "$TMP"; MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash "$(cygpath -w "$TMP" | sed 's#\\#/#g; s#^\([A-Za-z]\):#/mnt/\L\1#')" < /dev/null; }
# 1. build
if [ -z "${SKIP_BUILD:-}" ]; then
  echo "== build $L: $(cat "$HERE/play-knobs.txt") $KNOBS"
  run_wsl "cd $WTREE && TREE=$WTREE bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh $L $(cat "$HERE/play-knobs.txt") $KNOBS 2>&1 | tail -3; cat /root/probe/lanes/route/out-$L/missing.txt 2>/dev/null" || exit 1
fi
run_wsl "test -s /root/probe/lanes/route/out-$L/elf.sha256" || { echo "no build out-$L"; exit 1; }
echo "$NAME: $KNOBS" > "$GALLERY/dc/$NAME/knobs.txt"
run_wsl "cat /root/probe/lanes/route/out-$L/elf.sha256" >> "$GALLERY/dc/$NAME/knobs.txt"
# 2. fixtures
LIST=$(run_wsl "rm -rf $WL && LOOK=${LOOK:-} python3 $WTREE/port/dreamcast/tools/d367/look/mkfix.py $L $WL ${SHOTS:-}") || { echo "$LIST"; exit 1; }
echo "$LIST"
# 3. one Flycast run per shot
cd "$H" || exit 1
STAMP=$(date +%H%M%S)
while read -r shot fix secs; do
  [ -z "$shot" ] && continue
  N=lg-$NAME-$shot-$STAMP; S=scenarios/route-$N
  D=$(run_wsl "cd \"$HW\" && python3 stage-scenario.py route-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $fix > $WL/stage-$shot.json 2>&1; python3 -c \"import json;d=json.load(open('$WL/stage-$shot.json'));print(d['status'],d['disc_sha256'])\" || tail -3 $WL/stage-$shot.json")
  case "$D" in STAGED_PAYLOAD_IDENTITY_PASS*) ;; *) echo "$shot: stage failed: $D"; continue ;; esac
  python run-emulator.py route-$N --seconds $secs --period ${PERIOD:-6} > $S-run-stdout.txt 2>&1 < /dev/null
  C=$S/capture
  # the newest still that is not the crash screen (a long `freeze` trips CRASH_SCREEN's 30 s hang watchdog)
  last=$(python -c "import sys,glob,numpy as np;from PIL import Image
for d in sorted(glob.glob(sys.argv[1]+'/shots/t*'))[::-1]:
    m=np.asarray(Image.open(d+'/frames/fb0.png').convert('RGB'),float).reshape(-1,3).mean(0)
    if m[2]<=m[0]+30: print(d); break" "$C" 2>/dev/null)
  frz=$(grep -a -c "warp: frozen" $C/run-output.txt)
  echo "$shot: frozen=$frz halt=$(grep -ac HALT $C/run-output.txt) missing=$(grep -ac 'RE4DC MISSING' $C/run-output.txt) misalign=$(grep -ac MISALIGN $C/run-output.txt) shot=${last##*/}"
  [ -n "$last" ] && cp "$last/frames/fb0.png" "$GALLERY/dc/$NAME/$shot.png"
  echo "$(echo $D | awk '{print $2}')  disc.bin (deleted after run)" > $S/disc.sha256
  rm -f $C/disc.bin $S/disc/disc.bin
  mv $S $S-run-stdout.txt "$EV/" 2>/dev/null
done <<< "$LIST"
# 4. sheet
[ -n "${NOSHEET:-}" ] || python "$HERE/sheet.py" "$GALLERY" ${COLS:-} --hwms "${HWMS:-$GALLERY/hwms.json}"
