#!/bin/bash
# hwproject.sh - project a D367 candidate onto real Dreamcast hardware (SH-4 @200 MHz), by area.
#
#   hwproject.sh [options] <evidence-dir | build-dir | hwmodel-dir>
#
# Input (WSL or Windows path):
#   evidence dir   a harness capture dir (re4dc-game.elf, syms.txt, disc-output/disc.bin[, run.pcs])
#   build dir      build.sh output (re4dc-game.elf, syms.txt) with the disc in ./disc, ../disc or --disc
#   hwmodel dir    a dir made by an earlier hwproject run (trace/ present): only re-simulates
# Steps:
#   1. stage a NEW evidence dir $HWM_EVROOT/hwmodel-<name> from the hwtrace binary dir $HWM_BIN
#      (interpreter-mode Flycast with the hwtrace patch; see flycast/README in this dir)
#   2. run it: frames --count (per-PC counts) and --trace A:B:STEP (full traces, ~62 MB/frame);
#      Flycast exits by itself after the last traced frame
#   3. hwsim nominal / low / high / no-DMA over the traces, hwreport per function and area
#   4. print the area table and the delta against the reference (LD) projection in $HWM_REF
# Options:
#   --name N         evidence dir suffix (default: basename of the input)
#   --disc FILE      disc.bin for a build dir
#   --elf FILE       ELF when it is not <input>/re4dc-game.elf (e.g. a D349 room reference.elf)
#   --frameaddr HEX  physical address of a guest word stored once per frame with the frame number;
#                    needed when there is no syms.txt (non-PC_SAMPLER builds)
#   --area-rules F   extra function->area rules for hwreport (TSV: regex<TAB>area; 'file:regex' matches
#                    the source file), checked before the built-in D367 rules
#   --count A:B      counted frames (default 2401:2520)
#   HWM_SECONDS=s    (env) emulator run limit, default 3600 (hwtrace-run.ps1); a late window needs more
#   --trace A:B:S    traced frames (default 2401:2520:8 = 15 frames, ~0.9 GB)
#   --ref DIR        reference hwproject output dir to diff against (default $HWM_REF)
#   --pcs FILE       run.pcs of a normal (dynarec) capture of the same build: adds sampled Flycast ms
#   --keep-disc      keep the staged disc copy (default: delete it after the run)
#   --drop-traces    delete trace-*.bin after simulating (keeps counts, logs and proj/; ~0.8 GB saved)
#   --jobs N         parallel hwsim jobs (default 4)
#   --tail N         keep the log reader running N frames past the window (the emulator does not exit by
#                    itself; the tree's read_log.py stops after a final drain), so the window's last tick's
#                    log records (LOGIC_TRACE behaviour arms) are kept. Counts and traces are unchanged.
# Output: <hwmodel dir>/proj/{nominal,low,high,nodma}.*, proj/rep/{functions,areas}.tsv,
#         proj/projection.txt (the printed tables)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
HWM_BIN=${HWM_BIN:-/mnt/d/Flycast-Evidence/re4-dreamcast/hwmodel-bin}
HWM_EVROOT=${HWM_EVROOT:-/mnt/d/Flycast-Evidence/re4-dreamcast}
# disc images are staged outside evidence dirs (and off the trace drive), deleted after the run
HWM_DISCS=${HWM_DISCS:-/mnt/c/Flycast-Evidence/re4-dreamcast/_hwmodel-discs}
HWM_MINFREE_MB=${HWM_MINFREE_MB:-10000}   # refuse to start if the trace drive would drop below this
HWM_REF=${HWM_REF:-/mnt/d/Flycast-Evidence/re4-dreamcast/hwmodel-ld2/proj}
HWM_TID1=${HWM_TID1:-/root/probe/d367-agents/hwmodel/data/ld-pcs-func-tid1.csv}
HWM_TID12=${HWM_TID12:-/root/probe/d367-agents/hwmodel/data/ld-pcs-func-tid12.csv}
PCS_SYMBOLIZE=${PCS_SYMBOLIZE:-/root/probe/d367-agents/profiler/host/pcs_symbolize.py}
PS=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe

NAME= DISC= COUNT=2401:2520 TRACE=2401:2520:8 REF=$HWM_REF PCS= KEEP=0 DROP=0 JOBS=4 IN= ELFIN= FRAMEADDR= AREARULES= TAIL=0
while [ $# -gt 0 ]; do
  case $1 in
    --name) NAME=$2; shift ;; --disc) DISC=$2; shift ;; --count) COUNT=$2; shift ;;
    --trace) TRACE=$2; shift ;; --ref) REF=$2; shift ;; --pcs) PCS=$2; shift ;;
    --elf) ELFIN=$2; shift ;; --frameaddr) FRAMEADDR=$2; shift ;; --area-rules) AREARULES=$2; shift ;;
    --keep-disc) KEEP=1 ;; --drop-traces) DROP=1 ;; --jobs) JOBS=$2; shift ;; --tail) TAIL=$2; shift ;;
    -h|--help) sed -n '2,42p' "$0"; exit 0 ;;
    *) IN=$1 ;;
  esac; shift
done
[ -n "$IN" ] || { sed -n '2,42p' "$0"; exit 2; }
winp() { case $1 in [A-Za-z]:\\*|[A-Za-z]:/*) wslpath -u "$1" ;; *) echo "$1" ;; esac; }
IN=$(cd "$(winp "$IN")" && pwd)
[ -z "$DISC" ] || DISC=$(winp "$DISC")
[ -z "$PCS" ] || PCS=$(winp "$PCS")
[ -z "$ELFIN" ] || ELFIN=$(winp "$ELFIN")
[ -z "$AREARULES" ] || AREARULES=$(cd "$(dirname "$(winp "$AREARULES")")" && pwd)/$(basename "$AREARULES")

# hwsim binary (built on demand next to a cache of the source hash)
CACHE=${XDG_CACHE_HOME:-$HOME/.cache}/hwmodel; mkdir -p "$CACHE"
SUM=$(md5sum "$HERE/hwsim.c" | cut -c1-12); HWSIM=$CACHE/hwsim-$SUM
[ -x "$HWSIM" ] || gcc -O2 -march=native -o "$HWSIM" "$HERE/hwsim.c" -lm

if ls "$IN"/trace/trace-*.bin >/dev/null 2>&1; then
  E=$IN; echo "[reusing traces in $E/trace]"
else
  SRC=$IN; [ -f "$IN/re4dc-game.elf" ] || [ -n "$ELFIN" ] || SRC=$IN/build
  [ -n "$ELFIN" ] || ELFIN=$SRC/re4dc-game.elf
  [ -f "$ELFIN" ] || { echo "no ELF ($ELFIN); pass --elf" >&2; exit 1; }
  [ -f "$SRC/syms.txt" ] || [ -n "$FRAMEADDR" ] || { echo "no syms.txt in $SRC: pass --frameaddr" >&2; exit 1; }
  if [ -z "$DISC" ]; then
    for d in "$IN/disc-output/disc.bin" "$IN/disc/disc.bin" "$IN/../disc/disc.bin" "$IN/disc.bin"; do
      [ -f "$d" ] && { DISC=$d; break; }
    done
  fi
  [ -f "${DISC:-}" ] || { echo "no disc.bin found; pass --disc" >&2; exit 1; }
  [ -n "$NAME" ] || NAME=$(basename "$IN"); [ "$NAME" != build ] || NAME=$(basename "$(dirname "$IN")")
  E=$HWM_EVROOT/hwmodel-$NAME
  [ ! -e "$E" ] || { echo "$E exists; pick another --name (or pass that dir to re-simulate)" >&2; exit 1; }
  NFR=$(echo "$TRACE" | awk -F: '{s=$3?$3:1; print int(($2-$1)/s)+1}')
  FREE=$(df -BM --output=avail "$HWM_EVROOT" | tail -1 | tr -dc 0-9)
  NEED=$((NFR * 70 + 100 + HWM_MINFREE_MB))
  [ "$FREE" -gt "$NEED" ] || { echo "only ${FREE} MB free on $HWM_EVROOT; need ~$((NFR * 70 + 100)) MB and to keep ${HWM_MINFREE_MB} MB free" >&2; exit 1; }
  mkdir -p "$E/disc-output" "$HWM_DISCS"
  cp -r "$HWM_BIN"/. "$E"/
  if [ "$TAIL" -gt 0 ]; then   # the tail needs this tree's runner and log reader (RE4DC_LOG_STOP)
    cp "$HERE/flycast/hwtrace-run.ps1" "$HERE/../flycast-harness/read_log.py" "$E"/
  fi
  # A real pad must never drive a traced run: this Flycast reads pads while unfocused, and a user's
  # DualSense press sent a fixture into the VMU menu (stdrt g-shw orig arms). Same block as the harness.
  if ! grep -q '^maple_sdl_joystick_0 = -1' "$E/emu.cfg"; then
    printf '\n[input]\n' >> "$E/emu.cfg"
    for i in 0 1 2 3 4 5 6 7; do printf 'maple_sdl_joystick_%d = -1\n' $i >> "$E/emu.cfg"; done
  fi
  for f in syms.txt elf.sha256 head.txt candidate.txt size.txt; do
    [ -f "$SRC/$f" ] && cp "$SRC/$f" "$E/"
  done
  cp "$ELFIN" "$E/re4dc-game.elf"
  FA=(); [ -z "$FRAMEADDR" ] || FA=(-FrameAddr "$FRAMEADDR")
  DB=$HWM_DISCS/hwmodel-$NAME.bin; DC=$HWM_DISCS/hwmodel-$NAME.cue
  cp "$DISC" "$DB"
  sha256sum "$DB" | sed "s#  .*#  disc.bin#" > "$E/disc-output/disc.sha256"
  (cd "$E" && sha256sum re4dc-game.elf > elf.sha256.check)
  printf 'FILE "hwmodel-%s.bin" BINARY\n  TRACK 01 MODE1/2048\n    INDEX 01 00:00:00\n' "$NAME" > "$DC"
  echo "disc staged at $(wslpath -w "$DB") and deleted after the run" > "$E/disc-output/README.txt"
  echo "hwmodel: SH-4 hardware projection trace of $IN" > "$E/PURPOSE.txt"
  echo "$IN" > "$E/source.txt"
  echo "[tracing $NFR frames in $E; ~6 min for 2401:2520:8]"
  T0=$(date +%s)
  "$PS" -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$E/hwtrace-run.ps1")" -Out trace -Cue "$(wslpath -w "$DC")" \
        "${FA[@]}" -Count "$COUNT" -Trace "$TRACE" -Tail "$TAIL" ${HWM_SECONDS:+-Seconds $HWM_SECONDS} </dev/null | tr -d '\r'
  echo "[trace run $(( $(date +%s) - T0 )) s]"
  [ "$KEEP" = 1 ] || rm -f "$DB" "$DC"
  N=$(ls "$E"/trace/trace-*.bin 2>/dev/null | wc -l)
  [ "$N" -gt 0 ] || { echo "no traces written; see $E/trace/run-output.txt and $E/flycast.log" >&2; exit 1; }
  [ "$N" = "$NFR" ] || echo "WARNING: $N of $NFR traced frames written (game did not reach the window?)"
fi

ELF=$E/re4dc-game.elf
P=$E/proj; mkdir -p "$P"
TR=$(ls "$E"/trace/trace-*.bin)
T0=$(date +%s)
cat > "$P/jobs.txt" <<JOBS
nominal
low     --fill-hit 12 --fill-miss 20 --fill-ovh 0 --burst-tail 6 --wb-hit 8 --wb-miss 16 --sq-cost 10
high    --fill-hit 16 --fill-miss 26 --fill-ovh 10 --burst-tail 4 --wb-hit 10 --wb-miss 20 --sq-cost 24
nodma   --no-dma
JOBS
( cd "$P" && awk 'NF' jobs.txt | while read -r n args; do
    echo "$HWSIM --elf $ELF --out $n $args $(echo $TR) > $n.log 2>&1"; done | xargs -P "$JOBS" -I{} bash -c "{}" )
echo "[hwsim $(( $(date +%s) - T0 )) s]"
# guard: every traced frame must be complete (a full disk truncates traces silently)
TRI=$(awk '/^frame .*traced/ {s += $4; n++} END {if (n) printf "%.0f", s / n}' "$E/trace/hwtrace.log")
SIM=$(awk '$1 == "insn_per_frame" {print $2}' "$P/nominal.sum.txt")
if [ -n "$TRI" ] && awk -v a="$SIM" -v b="$TRI" 'BEGIN {d = a / b - 1; exit !(d < -0.01 || d > 0.01)}'; then
  echo "ERROR: traces hold $SIM insns/frame but Flycast traced $TRI: truncated traces (disk full?)" >&2
  echo "INVALID: truncated traces" > "$P/INVALID.txt"; exit 1
fi

PCSA=()
if [ -n "$PCS" ] && [ -f "$PCS" ] && [ -f "$PCS_SYMBOLIZE" ]; then
  F=${COUNT}
  python3 "$PCS_SYMBOLIZE" --elf "$ELF" --pcs "$PCS" --frames "$F" --top 1000000 --csv "$P/pcs-all.csv" >/dev/null
  python3 "$PCS_SYMBOLIZE" --elf "$ELF" --pcs "$PCS" --frames "$F" --tid 1 --top 1000000 --csv "$P/pcs-tid1.csv" >/dev/null
  python3 "$PCS_SYMBOLIZE" --elf "$ELF" --pcs "$PCS" --frames "$F" --tid 12 --top 1000000 --csv "$P/pcs-tid12.csv" >/dev/null
  PCSA=(--pcs-csv "$P/pcs-all.csv" --pcs-tid1 "$P/pcs-tid1.csv" --pcs-tid12 "$P/pcs-tid12.csv")
else
  PCSA=(--pcs-tid1 "$HWM_TID1" --pcs-tid12 "$HWM_TID12")
fi
CNT=(); [ -f "$E/trace/counts.bin" ] && CNT=(--counts "$E/trace/counts.bin" --count-frames \
  "$(echo "$COUNT" | awk -F: '{print $2-$1+1}')")
python3 "$HERE/hwreport.py" --elf "$ELF" --sim "$P/nominal" --whatif low="$P/low" --whatif high="$P/high" \
  --whatif nodma="$P/nodma" "${PCSA[@]}" ${AREARULES:+--area-rules "$AREARULES"} "${CNT[@]}" --out "$P/rep" --top 30 > "$P/report.txt"
python3 "$HERE/hwcompare.py" --cand "$P" --ref "$REF" --trace-log "$E/trace/hwtrace.log" | tee "$P/projection.txt"
echo "[full report: $P/report.txt; tables: $P/rep/]"
if [ "$DROP" = 1 ]; then
  for f in "$E"/trace/trace-*.bin; do printf '%s %s\n' "$(basename "$f")" "$(stat -c %s "$f")"; done > "$E/trace/traces-dropped.txt"
  rm -f "$E"/trace/trace-*.bin; echo "[traces deleted]"
fi
echo "[$(df -BG --output=avail "$HWM_EVROOT" | tail -1 | tr -d ' ') free on the trace drive]"
