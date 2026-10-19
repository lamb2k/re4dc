#!/bin/bash
# stills.sh <tag> <scene-with-freeze...> (Git Bash): e19krW vs e19wrW at a frozen tick; tier-2 pixel diff of the
# framebuffers in the last shot (t0060). One Flycast at a time.
set -euo pipefail
TAG=${1:?}; shift
D=$(cd "$(dirname "$0")" && pwd)
E=/c/Flycast-Evidence/re4-dreamcast/engine19-20261019
export RC19D=/root/re4data/private/rc19o2-20261019
for sc in "$@"; do
  for arm in k w; do
    N=$TAG-$sc-$arm
    PURPOSE="engine19 stills $sc arm e19${arm}${SUF:-}rW" bash "$D/g.sh" $N e19${arm}${SUF:-}rW /root/probe/lanes-20261019/engine19/k/$sc-warp.txt "" 60 | tail -1
  done
  echo "== $sc"
  grep -a "warp: frozen" $E/$TAG-$sc-w/capture/run-output.txt | head -1 || echo "not frozen"
  grep -a "INVISPCO" $E/$TAG-$sc-w/capture/run-output.txt | tail -1
  python "$D/fbdiff.py" $E/$TAG-$sc-k/capture/shots/t0060/frames $E/$TAG-$sc-w/capture/shots/t0060/frames
done
