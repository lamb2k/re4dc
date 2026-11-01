set -euo pipefail
TREE_EF09=/root/work/lanes/engine-ef09-20261029
OUT_EF09=/root/probe/engine-ef09-20261029/release1
cd "$TREE_EF09"
test ! -e "$OUT_EF09"
mkdir -p "$OUT_EF09/programs"
printf '%s\n' "$$" > "$OUT_EF09/runner.pid"
export ROUTE_PROGRAMS_DIR="$OUT_EF09/programs" ROUTE_PROGRAMS_JSON=''
source <(tr -d '\r' < "$TREE_EF09/port/dreamcast/tools/d367/rr/recipe.conf")
CH2_EF09=$CH2
for arm in absent zero plan portal; do
  extras=''
  case "$arm" in
    zero) extras='WORLD_PREPARED09=0';;
    plan|portal) extras=$(python3 -c 'import json,sys; print(" ".join(json.load(open("port/dreamcast/tools/cloud/build31/world_prepared09_profiles.json"))["profiles"][sys.argv[1]]))' "$arm");;
  esac
  label="ef09oct29v1${arm}"
  expected="/root/probe/lanes/route/out-${label}rP"
  test ! -e "$expected"
  test ! -e "$ROUTE_PROGRAMS_DIR/candidate-route${label}rP"
  printf '%s\n' "START $arm tree=$TREE_EF09 label=$label pid=$$ $(date -Is)" | tee -a "$OUT_EF09/runner.log"
  K="$OUT_EF09/$arm-logs" T="$TREE_EF09" LP="$label" CH2="$CH2_EF09 $extras" bash "$TREE_EF09/port/dreamcast/tools/d367/ch2/ch2-build.sh" rP 2>&1 | tee "$OUT_EF09/$arm-console.log"
  test -s "$expected/re4dc-game.elf"
  test -f "$expected/missing.txt"
  test ! -s "$expected/missing.txt"
  test -s "$expected/resolved-knobs.txt"
  grep -q "built route${label}rP" "$OUT_EF09/$arm-logs/logs-build.txt"
  grep -q "rc=0 ${label}rP" "$OUT_EF09/$arm-logs/logs-build.txt"
  printf '%s\n' "PASS $arm $(date -Is)" | tee -a "$OUT_EF09/runner.log"
done
printf '%s\n' 'COMPLETE' | tee -a "$OUT_EF09/runner.log"