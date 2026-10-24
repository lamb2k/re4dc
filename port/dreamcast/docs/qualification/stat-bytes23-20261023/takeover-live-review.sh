#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete
git -C "$T" remote get-url origin
git -C "$T" fetch origin t15/int dreamcast-port
git -C "$T" status --short --branch
git -C "$T" log -1 --format='%H %s' origin/t15/int
git -C "$T" log -1 --format='%H %s' origin/dreamcast-port
git -C "$T" show origin/t15/int:port/dreamcast/tools/d367/rr/recipe.conf | tail -35
ps -eo pid,ppid,etimes,stat,args | rg 'flycast.exe|rr.sh|sh-elf-gcc|sh-elf-g\+\+' | head -25 || true
/root/rr/bin/rr.sh status
find /root/work/lanes -maxdepth 1 -type d -name '*stat*' -printf '%f\n'