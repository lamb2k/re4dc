#!/usr/bin/env bash
set -euo pipefail
printf 'TARGET OFF IDENTITY\n'
TOOL=/opt/toolchains/dc/sh-elf/bin
W=/dev/shm/stat-takeover-identity
mkdir -p "$W"
for A in base off on;do
 case "$A" in base)O=/root/probe/lanes/route/out-rr933936erP;;off)O=/root/probe/lanes/route/out-sb23off66f0rP;;on)O=/root/probe/lanes/route/out-sb23on66f0rP;;esac
 "$TOOL/sh-elf-objcopy" -R .stack -O binary "$O/re4dc-game.elf" "$W/$A.bin"
 sha256sum "$W/$A.bin"
done
cmp "$W/base.bin" "$W/off.bin"
for P in /root/probe/lanes/route/out-rr933936erP/*.ovl;do
 N=$(basename "$P");cmp "$P" "/root/probe/lanes/route/out-sb23off66f0rP/$N"
done
printf 'MAIN_AND_ALL_OFF_OVERLAYS_IDENTICAL\n'
printf 'STAGE PROGRESS\n'
ps -eo pid,ppid,etime,comm | grep -E 'sha256sum|fp_iso|python3' | head -16 || true
find /root/work/lanes/stat-bytes23-takeover-scratch/release -maxdepth 1 -type f -printf '%f %s\n'
printf 'VMU TEST DISCOVERY\n'
find /root/work/lanes/stat-bytes23-complete -maxdepth 6 -iname '*vmu*test*' -o -iname '*vmu*context*'
