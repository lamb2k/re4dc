#!/bin/bash
set -euo pipefail
T=/root/probe/lanes-20261016/ch4found/tree; M=$T/port/dreamcast/tools/d367/model-registry; o=/root/probe/lanes-20261016/ch4found/cast/reg-216
rm -rf "${o:?}"; cd "$T"
python3 port/dreamcast/tools/d367/model_registry.py $M/ps2-ch4f-r216.json $o --tree $T --package-room 216 --pool --wide-identity --pack-bones 64 --roles5 > $o.log 2>&1 && sha256sum $o/package/r216/registry.re4nmr $o/tex/* || tail -2 $o.log
