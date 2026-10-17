#!/bin/bash
# grun.sh <name> <arm label> <warp.txt> [seconds]  (Git Bash; lane gprof17, 2026-10-17): one profiler run.
# Stages and runs ONE Flycast through benchmark/bench-run.sh (same fixture, data set, disc cleanup and bench-ms row)
# with the given warp file, streams the PC sampler ring with read_pcs.py while it runs, then prints the gprof.py table.
# Evidence: C:\Flycast-Evidence\re4-dreamcast\gprof17-20261017\<name> (user rule: stay on C:); run.pcs lands there.
# The warp file is copied to benchmark/benchmark-gp-<name>-warp.txt for the run and removed afterwards.
set -euo pipefail
N=${1:?name}; L=${2:?arm label}; WARP=${3:?warp file}; SECS=${4:-80}
HERE=$(cd "$(dirname "$0")" && pwd)
B=$HERE/../benchmark
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export BENCH_EV=${BENCH_EV:-/c/Flycast-Evidence/re4-dreamcast/gprof17-20261017}
mkdir -p "${BENCH_EV:?}/_pcs"
SC=gp-$N
SCF=$B/benchmark-$SC-warp.txt
[ ! -e "$SCF" ] || { echo "$SCF exists"; exit 1; }
cp "$WARP" "$SCF"
trap 'rm -f "${SCF:?}"' EXIT
C="$H/scenarios/route-bench-$N/capture"
PCS=$BENCH_EV/_pcs/$N.pcs
(
  for _ in $(seq 1 1800); do [ -f "$C/flycast.pid" ] && [ -f "$C/syms.txt" ] && break; sleep 1; done
  OFF=$(awk '$3=="re4dc_pcs"{printf "0x%x\n", strtonum("0x"$1) - 0x8c000000}' "$C/syms.txt" | head -1)
  [ -n "$OFF" ] || { echo "no re4dc_pcs in syms.txt (not a PC_SAMPLER build?)"; exit 0; }
  python "$(dirname "$HERE")/../flycast-harness/read_pcs.py" "$OFF" "$PCS" "$((SECS + 30))" --dir "$(cygpath -w "$C")" \
    > "$PCS.out" 2>&1
) &
RP=$!
bash "$B/bench-run.sh" "$SC" "$L" "$N" "$SECS"
wait "$RP" || true
E=$BENCH_EV/$N
[ -d "$E" ] && [ -f "$PCS" ] && mv "$PCS" "$PCS.json" "$PCS.out" "$E/" 2>/dev/null || true
[ -f "$E/$N.pcs" ] && python "$HERE/gprof.py" pcs "$E/$N.pcs" "$E/capture/syms.txt" \
  --out-log "$E/capture/run-output.txt" --skip-s 20 | tee "$E/gprof.txt"
