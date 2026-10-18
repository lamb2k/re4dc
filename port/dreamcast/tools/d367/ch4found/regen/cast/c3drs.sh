#!/bin/bash
set -euo pipefail
C=/root/probe/lanes-20261016/cast16/conv3
for a in em14 em19 em1a; do [ -e "$C/$a.drs" ] || cp "/root/probe/lanes/ps2cast/inputs/$a.drs" "$C/$a.drs"; done
rm -rf "${C:?}/zealot-em1b-0ap" "$C/zealot-em1b-0ap.native.log"
ls "$C"/*.drs
