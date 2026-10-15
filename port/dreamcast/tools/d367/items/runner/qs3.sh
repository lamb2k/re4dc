#!/bin/bash
# qs3.sh <jobfile> [workers] (Git Bash): lane items job queue. Job lines: "run|trc|hw args..." (same functions as qa.sh).
# Every launch waits for a host Flycast slot (8 machine-wide) and C: > 17 GB (slot lock, 150 s per launch).
G=/c/Flycast-Evidence/re4-dreamcast/items-20261014/_tools
export G
J=$1; P=${2:-5}
grep -v '^#' $J | grep -v '^$' | while read -r line; do printf '%s\0' "$line"; done | xargs -0 -P $P -I{} bash $G/qjob3.sh {}
echo "queue $J done $(date +%T)"
