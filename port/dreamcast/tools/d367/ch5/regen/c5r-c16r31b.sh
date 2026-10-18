#!/bin/bash
# ch5regen: r31b U-3 package with --pack-bones 128 (df054fec: the U-3 has 97 bones; BONES 64/96/128 accepted).
set -euo pipefail
C=/root/probe/lanes-20261018/ch5regen/c16
o=$C/reg/D/reg-31b; rm -rf "${o:?}"
cd "$C/t6"
python3 port/dreamcast/tools/d367/model_registry.py "$C/specs/D-ps2-ch5-boss.json" "$o" --tree "$C/c5m" --package-room 31b --pool --wide-identity --pack-bones 128 --roles5 > "$o.log" 2>&1 \
  && echo "31b $(sha256sum "$o/package/r31b/registry.re4nmr" | cut -c1-8) tex=$(ls "$o/tex" | wc -l)" || echo "31b FAIL $(tail -1 "$o.log" | cut -c1-200)"
