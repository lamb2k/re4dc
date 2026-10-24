#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23
D=$T/port/dreamcast/tools/d367
printf 'ORIGINAL HOST RESULT FILES\n'
find '/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/host-original-fixes-r1' -type f -printf '%P %s\n'
printf 'DIAGNOSTIC SOURCE\n'
sed -n '1,160p' "$T/port/dreamcast/game/platform/kos_cache_p2_diag.cpp"
printf 'BUILD LOG STATUS\n'
tail -10 /root/rr/logs/1023-2028-a5e972e4.log 2>/dev/null || true
ps -eo pid,ppid,etimes,args | rg 'audits23-original|test_failures|check_missing_actor' | head -12 || true