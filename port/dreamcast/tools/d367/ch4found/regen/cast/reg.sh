#!/bin/bash
# ch4regen: model_registry room packages for the ch4 cast (two recorded flag sets: a = c4spec2.sh, b = zq6/k7reg).
set -euo pipefail
C=/root/probe/lanes-20261016/cast16; W=$C/conv4; OUT=/root/probe/lanes-20261018/ch4regen/c16reg
M=$C/c4m/port/dreamcast/tools/d367/model-registry
mkdir -p "$OUT"
for r in ${ROOMS:-201 211 212 213 214 216 217 218 21b 21d 220 222 223 224 225 226 227 228 229 22a}; do
  for v in a b; do
    o=$OUT/$v/reg-$r; rm -rf "${o:?}"; mkdir -p "$OUT/$v"
    if [ $v = a ]; then T=/root/probe/lanes-20261016/ch4found/tree; X="--pack-bones 64 $( [ $r = 227 ] && echo --roles5 || true)"; cd $C/tree
    else T=$C/c4m; X="--pack-bones 96 --roles5"; cd $C/c4m; fi
    python3 port/dreamcast/tools/d367/model_registry.py $M/ps2-ch4-r$r.json $o --tree $T --package-room $r --pool --wide-identity $X > $o.log 2>&1 \
      && echo "$r $v $(sha256sum $o/package/r$r/registry.re4nmr | cut -c1-8)" || echo "$r $v FAIL $(tail -1 $o.log | cut -c1-150)"
  done
done
