#!/usr/bin/env bash
set -euo pipefail
printf 'STAT LOCKS\n'
lslocks -o PID,COMMAND,PATH | grep -E 'stat-bytes|trace-' | head -15 || true
printf 'LIVE STAT JOBS\n'
ps -eo pid,ppid,etime,args | grep -E 'takeover-census|takeover-h2-v4|stat-guest-slot|census-bound-run|takeover-kos' | grep -v grep | cut -c1-240 | head -25
printf 'H2 CAP STATE\n'
find '/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d' -maxdepth 2 -name run-result.json -o -name bounded-launch.json | head -10
