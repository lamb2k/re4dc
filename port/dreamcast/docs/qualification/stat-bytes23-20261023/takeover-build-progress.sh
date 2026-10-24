#!/usr/bin/env bash
set -euo pipefail
printf 'STAT BUILD LOG TAILS\n'
for A in off on;do
 B=/root/work/lanes/stat-bytes23-takeover-scratch/$A
 tail -n 4 "$B/build.log"
 [ ! -s "$B/k/logs-build.txt" ] || tail -n 1 "$B/k/logs-build.txt" | cut -c1-220
done
printf 'BUILD RESOURCE OWNERS\n'
ps -eo pid,ppid,etime,args | grep -E 'stat-bytes23/takeover-build|make -j|sh-elf-g\+\+' | grep -v grep | head -10 || true
printf 'REPRO FILES\n'
cat '/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/fixtures/boat-warp.txt'
cat '/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/fixtures/mendez-warp.txt'
printf 'KILL RIG HELPER\n'
find /root/work/lanes/fix-mendez-freeze23-scratch -maxdepth 2 -type f -printf '%f\n' | head -40
