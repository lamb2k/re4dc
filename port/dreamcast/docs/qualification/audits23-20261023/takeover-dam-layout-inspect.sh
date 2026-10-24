#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on
sed -n '360,430p' "$T/include/model.h"
sed -n '1,115p' "$T/include/em.h"
rg -n '^class cModel|^class cEm|^class cEmMgr|vptr|virtual' "$T/include/model.h" "$T/include/em.h" "$T/port/dreamcast/game/platform/include/re4dc_prelude.h" | head -45
head -75 "$T/port/dreamcast/game/platform/include/re4dc_prelude.h"