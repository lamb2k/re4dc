#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-takeover
git -C "$T" diff --check
git -C "$T" add port/dreamcast/game/platform/include/re4dc_prelude.h
git -C "$T" commit -m 'Define stat byte-order helper once in the forced prelude'
git -C "$T" push origin HEAD:refs/heads/wip/stat-bytes23-takeover-20261023
printf 'SOURCE\n';git -C "$T" rev-parse HEAD
printf 'RR GATE DRIVER\n'
sed -n '1,260p' "$T/port/dreamcast/tools/d367/rr/rr-jobs.sh"
printf 'RR GATE PLAN\n'
grep -nE 'jobs|twin|stage|judge|census|h2|kos|gdemu|decisions' "$T/port/dreamcast/tools/d367/rr/rr-cycle.sh" | head -85
