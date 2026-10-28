#!/bin/bash
# gpu-scene.sh <gdemu dir (Windows)> <syms file> <evidence dir (Git Bash)> <label> <scene>   (Git Bash; lane guards28 10-28)
# One cache-model Flycast measurement of a QA disc (the perf-cache27 method, fix-cachefly27 states), three runs of at
# most 60 s each, one Flycast at a time:
#   fast  dynarec on, gdemu profile, QA teleporter keys (speed/gpu-keys/<scene>.txt), state saved at SPEED_GPU_FAST_S (50)
#   warm  dynarec off (cache model), load fast, state saved at 40 s (a dynarec state carries an empty cache)
#   meas  dynarec off, load warm, 60 s with RE4DC_CACHE_STATS (CSTAT every 60 frames) + RE4DC_TA_STATS (TA list peak)
# Exe: SPEED_GPU_EXE (default the perf-cache27 flycast-console cstat build, emulator patch f06da2d8). States are deleted
# after the run (they belong to this exe + disc only); logs and stats are kept.
set -euo pipefail
G=${1:?gdemu}; SY=${2:?syms}; EV=${3:?evidence}; X=${4:?label}; SC=${5:?scene}
HERE=$(cd "$(dirname "$0")" && pwd)
FP=$(cd "$HERE/../../fullplay" && pwd)/fp_run.py
EXE=${SPEED_GPU_EXE:-C:\\Flycast-Evidence\\re4-dreamcast\\perf-cache27-20261027\\bin\\flycast-console-cstat.exe}
mkdir -p "$EV/runs" "$EV/stats" "$EV/states"
EW=$(cygpath -w "$EV")
KEYS=$(cygpath -w "$HERE/gpu-keys/$SC.txt")
SYMS=$(tr -d '\r\n' < "$SY")
N=$X-$SC
export RE4DC_EMU=console RE4DC_CONSOLE_EXE="$EXE" RE4DC_GD_PROFILE=gdemu RE4DC_GD_SEED=1 PYTHONIOENCODING=utf-8 PYTHONUTF8=1
run() { # <name> <dynarec> [extra env assignments...]
  local n=$1 d=$2; shift 2
  rm -rf "${EV:?}/runs/${n:?}"
  env RE4DC_CONSOLE_DYNAREC="$d" "$@" python "$FP" --disc "$G" --cap "$EW\\runs\\$n" --syms "$SYMS" --seconds 60 --name "$n" \
    ${KEYARG:+--keys "$KEYARG"} > "$EV/runs/$n.out" 2>&1 || true
}
KEYARG=$KEYS run "$N-fast" yes RE4DC_CONSOLE_SAVE_STATE="$EW\\states\\$N-fast.state" RE4DC_CONSOLE_SAVE_AT_S="${SPEED_GPU_FAST_S:-50}"
[ -s "$EV/states/$N-fast.state" ] || { echo "GPU $N: no fast state"; exit 1; }
KEYARG= run "$N-warm" no RE4DC_CONSOLE_LOAD_STATE="$EW\\states\\$N-fast.state" RE4DC_CONSOLE_SAVE_STATE="$EW\\states\\$N-warm.state" RE4DC_CONSOLE_SAVE_AT_S=40
[ -s "$EV/states/$N-warm.state" ] || { echo "GPU $N: no warm state"; exit 1; }
KEYARG= run "$N-meas" no RE4DC_CONSOLE_LOAD_STATE="$EW\\states\\$N-warm.state" \
  RE4DC_CACHE_STATS="$EW\\stats\\$N-cstat.txt" RE4DC_CACHE_STATS_FRAMES=60 RE4DC_TA_STATS="$EW\\stats\\$N-ta.txt"
rm -f "${EV:?}/states/${N:?}-fast.state" "${EV:?}/states/${N:?}-warm.state"
find "$EV/runs" -path "*$N-*" \( -name 'track03*' -o -name 'disc.bin' \) -delete 2>/dev/null || true
echo "GPU $N done: $(grep -c '^CSTAT frame' "$EV/stats/$N-cstat.txt" 2>/dev/null || echo 0) CSTAT rows"
