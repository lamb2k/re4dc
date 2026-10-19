#!/bin/bash
set -euo pipefail
Q=//wsl.localhost/Ubuntu-24.04/root/work/lanes/actorplan19/tree/port/dreamcast/tools/d367/fullplay/kos_squeeze.sh
for a in ${ARMS:-p k}; do
  bash $Q 'C:\Flycast-Evidence\re4-dreamcast\actorplan19-20261019\_base-sq'$a fpap19sq${a}W 'C:\Flycast-Evidence\re4-dreamcast\actorplan19-20261019\kos-'$a > /c/Flycast-Evidence/re4-dreamcast/actorplan19-20261019/_tools/kos-$a.log 2>&1 || true
  tail -3 /c/Flycast-Evidence/re4-dreamcast/actorplan19-20261019/_tools/kos-$a.log
done
echo KOSRUN DONE
