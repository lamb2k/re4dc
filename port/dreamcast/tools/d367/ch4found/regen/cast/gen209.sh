#!/bin/bash
# ch4regen copy of scratchpad/gen209.sh (ch4found agent, 10-17 16:5xZ).
set -euo pipefail
T=/root/probe/lanes-20261016/ch4found/tree; M=$T/port/dreamcast/tools/d367/model-registry; W=/root/probe/lanes-20261016/ch4found/cast
cd $T
for x in 209:ch3-em1ap 20d:ch3-em19p; do r=${x%%:*}; s=${x#*:}; o=$W/reg-$r; rm -rf "${o:?}"
  python3 port/dreamcast/tools/d367/model_registry.py $M/ps2-$s.json $o --tree $T --package-room $r --pool --wide-identity --pack-bones 64 --roles5 > $o.log 2>&1 \
    && sha256sum $o/package/r$r/registry.re4nmr $o/tex/* | cut -c1-120 || echo "$r FAIL $(tail -2 $o.log | cut -c1-300)"
done
