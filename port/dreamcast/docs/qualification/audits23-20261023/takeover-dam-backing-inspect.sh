#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on
sed -n '238,278p' "$T/include/cManager.h"
rg -n -C4 'cManager<cEm>::workAt|cManager<cEm>::prepareWork|em_back|struct.*Backing|re4dc.*(slot|backing)' "$T/src/game/em.cpp" "$T/src/game"/*.cpp | head -110