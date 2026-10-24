#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23
printf 'STAT SOURCE\n'
git -C "$T" status --short --branch
git -C "$T" rev-parse HEAD origin/t15/int
git -C "$T" remote -v
printf 'WORKTREES\n'
git -C "$T" worktree list
printf 'LIVE RE4 JOBS\n'
ps -eo pid,ppid,etime,args | grep -E 'ch2-build|fp_twin|trace_lock|Flycast|flycast|sh-elf|make -j|rr.sh|stat-bytes|dedup-offline' | grep -v grep | head -65 || true
printf 'FIXTURE TOOLS\n'
find '/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/fixtures' -maxdepth 1 -type f -printf '%f %s\n'
printf 'UNIT SUMMARY\n'
git -C "$T" diff --stat 7b6ad154..c11a7eea
