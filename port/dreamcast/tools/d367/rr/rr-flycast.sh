#!/bin/bash
# rr-flycast.sh <evidence dir (Git Bash path)> [max slots]   (Git Bash on the Windows host; lane rr)
# Runs <evidence>/_jobs/list.txt ("<slots> <name>" per line, <name>.sh beside it) with at most <max slots> (default 12)
# Flycast slots in use by these jobs; each fp_run.py also waits while 12 flycast.exe run machine-wide
# (RE4DC_MAX_FLYCASTS). Writes <name>.log and <name>.rc per job and times.tsv (name, start, end, rc). No global input:
# fp_run.py posts keys to its own Flycast window only.
set -uo pipefail
EV=${1:?evidence}; MAX=${2:-12}
J=$EV/_jobs
export RE4DC_MAX_FLYCASTS=${RE4DC_MAX_FLYCASTS:-12}
: > "$J/times.tsv"
declare -A SL=()
used=0
reap() {
  local p
  for p in "${!SL[@]}"; do
    if ! kill -0 "$p" 2>/dev/null; then wait "$p" 2>/dev/null; used=$((used - SL[$p])); unset "SL[$p]"; fi
  done
}
while read -r slots name; do
  [ -n "${name:-}" ] || continue
  [ "$slots" -le "$MAX" ] || slots=$MAX
  while [ $((used + slots)) -gt "$MAX" ]; do sleep 3; reap; done
  ( t=$(date +%s); bash "$J/$name.sh" < /dev/null > "$J/$name.log" 2>&1; rc=$?; echo $rc > "$J/$name.rc"
    printf '%s\t%s\t%s\t%s\n' "$name" "$t" "$(date +%s)" "$rc" >> "$J/times.tsv" ) &
  SL[$!]=$slots; used=$((used + slots))
  sleep 3
done < <(tr -d '\r' < "$J/list.txt")
wait
echo "rr-flycast done $(wc -l < "$J/times.tsv") jobs"
