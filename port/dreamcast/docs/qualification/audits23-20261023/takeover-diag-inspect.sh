#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/audits23
git -C "$T" status --short --branch
git -C "$T" show --stat 6a3f6b60edfd4dc65e23f25ca9ee9a8edf32f6fe
sed -n '1,240p' "$T/port/dreamcast/docs/KOS_CACHE_P2_DIAG_20261023.md"
sed -n '1,180p' "$T/port/dreamcast/game/kos_cache_p2.mk"
/root/rr/bin/rr.sh status