#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23
printf 'LATEST REMOTE\n'
git -C "$T" fetch origin
printf 'STAT DIFF\n'
git -C "$T" diff 7b6ad154..c11a7eea -- port/dreamcast/platform/include/re4dc_prelude.h port/dreamcast/game/Makefile | head -180
printf 'UNIT FILES\n'
git -C "$T" diff --stat 7b6ad154..c11a7eea
printf 'RR STATUS\n'
bash "$T/port/dreamcast/tools/d367/rr/rr.sh" status || true
printf 'BUILD TOOLS\n'
sed -n '1,170p' "$T/port/dreamcast/tools/d367/fullplay/fp_twin.sh"
printf 'RR RUNNER\n'
sed -n '1,160p' "$T/port/dreamcast/tools/d367/rr/rr.sh"
