#!/bin/bash
# ch5regen: keep the wrong-warp first attempts of r300/r301/r304 under a renamed scenario dir before the rerun.
set -euo pipefail
H=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018/hroot/h/scenarios
for r in r300 r301 r304; do
  [ -d "$H/c5r-$r" ] && mv "$H/c5r-$r" "$H/attempt1-basewarp-c5r-$r"
done
ls "$H" | grep attempt1
