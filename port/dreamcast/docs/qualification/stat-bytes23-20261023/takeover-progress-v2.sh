#!/usr/bin/env bash
set -euo pipefail
for A in off on;do
 echo "ARM=$A"
 B=/root/work/lanes/stat-bytes23-complete-scratch/$A
 tail -n 2 "$B/build.log" | cut -c1-240
 [ ! -s "$B/k/logs-build.txt" ] || tail -n 1 "$B/k/logs-build.txt" | cut -c1-200
done
printf 'RESOURCE COUNTS\n'
ps -eo comm | grep -c '^sh-elf' || true
df -h /mnt/c | tail -1
