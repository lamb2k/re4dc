#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on
sed -n '300,355p' "$T/include/em.h"
sed -n '55,145p' "$T/src/game/em.cpp"
rg -n 're4dc_em.*(slot|work|pool)|cManager<cEm>::(workAt|prepareWork)|cEmMgr::(workAt|prepareWork)|EM.*(POOL|SLOT|SPARSE|BACK)' "$T/include" "$T/port/dreamcast/game/platform" "$T/src/game/em.cpp" | head -95