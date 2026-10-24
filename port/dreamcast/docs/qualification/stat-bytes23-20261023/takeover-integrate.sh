#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23
BASE=$(git -C "$T" rev-parse origin/t15/int)
NEW=/root/work/lanes/stat-bytes23-takeover
[ "$BASE" = 933936ea7f45ba81c09277a780ed00111407aa23 ]
[ -z "$(git -C "$T" status --porcelain)" ]
[ ! -e "$NEW" ]
git -C "$T" worktree add -b wip/stat-bytes23-takeover-20261023 "$NEW" "$BASE"
git -C "$NEW" merge --no-ff c11a7eeaa1f2149b4176ec45aabbbb95206b5e85 -m 'Merge complete stat byte-order audit onto current integration for qualification'
git -C "$NEW" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
git -C "$NEW" push -u origin HEAD:refs/heads/wip/stat-bytes23-takeover-20261023
printf 'MERGED SOURCE\n'
git -C "$NEW" status --short --branch
git -C "$NEW" rev-parse HEAD
printf 'MACRO\n'
git -C "$NEW" diff "$BASE" -- port/dreamcast/game/platform/include/re4dc_prelude.h
printf 'PLAYER CHANGE\n'
git -C "$NEW" diff "$BASE" -- src/game/player.cpp
printf 'CURRENT RECIPE\n'
cat "$NEW/port/dreamcast/tools/d367/rr/recipe.conf"
printf 'CURRENT RR LIVE\n'
ps -eo pid,ppid,etime,args | grep -E 'rr-cycle|ch2-build|sh-elf|route-build|fp_twin' | grep -v grep | head -18 || true
