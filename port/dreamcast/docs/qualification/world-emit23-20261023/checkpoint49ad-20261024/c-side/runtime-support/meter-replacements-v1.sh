#!/usr/bin/env bash
set -euo pipefail
E=/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776/runtime-support
H='/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/runtime-support/qualified-run-v1.sh'
for ((N=0;N<300;N++));do
 if [ -s "$E/B-m-s2-q1/bounded-launch.json" ];then
  python3 - "$E/B-m-s2-q1" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);b=json.loads((p/'bounded-launch.json').read_text());r=json.loads((p/'run-result.json').read_text());assert b['guest_exited'] and not b['deadline_fired'] and r['status']=='RUN_COMPLETE' and not r['errors']
PY
  bash "$H" R m b1 R-m-b1-q2
  bash "$H" L m b1 L-m-b1-q2
  exit 0
 fi
 sleep 2
done
printf 'ERROR no completed B-m-s2 within bounded wait\n' >&2
exit 1