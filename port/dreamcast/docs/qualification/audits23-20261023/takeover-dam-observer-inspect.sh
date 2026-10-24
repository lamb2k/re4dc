#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23-target-on
sed -n '1,180p' "$T/include/cManager.h"
rg -n -C3 'extern.*EmMgr|_EmMgr|cEmMgr::cEmMgr' "$T/include" "$T/src/game/em_mgr.cpp" "$T/src/game"/em*.cpp | head -100
rg -n '^warp: goto|^r10c:|^room lifecycle:|^warp: frame' '/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0/event-dam-on-r1/run-output.txt' | head -25